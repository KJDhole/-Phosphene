"""Evidence-first collection engine.

Every adapter returns normalized items with a title and a traceable URL. Raw
HTML, opaque ID lists, and failed responses are never passed directly to the
language model.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from rich.table import Table

from core.base_category import SourceConfig
from core.console import FailureSafeConsole
from core.diagnostics import (
    diagnostic_event,
    diagnostic_exception,
    redact_sensitive_text,
    safe_console_print,
    set_diagnostic_context,
)
from core.models import EvidenceItem, SourceResult

CONSOLE = FailureSafeConsole()
_MAX_ITEMS = 12
_MAX_SUMMARY_CHARS = 600


class CollectionSetupError(RuntimeError):
    """Raised when the shared HTTP collection client cannot be initialized."""


def _network_settings() -> dict[str, Any]:
    try:
        from core.config import load_config

        settings = load_config().get("network", {})
        return settings if isinstance(settings, dict) else {}
    except Exception as exc:
        diagnostic_exception("collector.network_config_failed", exc)
        return {}


def _url_descriptor(url: str) -> dict[str, Any]:
    try:
        parsed = urlsplit(url)
        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "path": parsed.path,
            "has_query": bool(parsed.query),
        }
    except ValueError as exc:
        return {"parse_error": f"{type(exc).__name__}: {exc}"}


def _build_http_client(settings: dict[str, Any], *, trust_env: bool) -> httpx.AsyncClient:
    timeout = max(1.0, min(float(settings.get("timeout_seconds", 20)), 120.0))
    max_connections = max(1, min(int(settings.get("max_connections", 8)), 50))
    max_keepalive = max(0, min(int(settings.get("max_keepalive_connections", 4)), max_connections))
    diagnostic_event(
        "collector.http_client_initializing",
        "DEBUG",
        trust_env=trust_env,
        timeout_seconds=timeout,
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive,
    )
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive,
    )
    client = httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": "Phosphene/2.2 (+local content research tool)"},
        trust_env=trust_env,
    )
    diagnostic_event("collector.http_client_initialized", "DEBUG", trust_env=trust_env)
    return client


async def _safe_close_client(client: httpx.AsyncClient, *, trust_env: bool) -> None:
    try:
        await client.aclose()
        diagnostic_event("collector.http_client_closed", "DEBUG", trust_env=trust_env)
    except Exception as exc:
        # A close error must never discard evidence that was already collected.
        diagnostic_exception("collector.http_client_close_failed", exc, trust_env=trust_env)


def _unexpected_source_failure(src: SourceConfig, exc: BaseException) -> SourceResult:
    diagnostic_exception(
        "collector.source_task_escaped",
        exc,
        source=src.name,
        source_type=src.type,
        url=_url_descriptor(src.url),
    )
    return SourceResult(
        source_name=src.name,
        display_name=src.display_name,
        source_url=src.url,
        status="error",
        error=redact_sensitive_text(f"{type(exc).__name__}: {exc}"),
    )


async def _collect_with_client(
    client: httpx.AsyncClient,
    sources: list[SourceConfig],
    debug: bool,
    use_scrapling: bool,
) -> list[SourceResult]:
    raw_results = await asyncio.gather(
        *(_fetch_source(client, source, debug, use_scrapling) for source in sources),
        return_exceptions=True,
    )
    results: list[SourceResult] = []
    for source, raw in zip(sources, raw_results):
        if isinstance(raw, asyncio.CancelledError):
            raise raw
        if isinstance(raw, BaseException):
            results.append(_unexpected_source_failure(source, raw))
        else:
            results.append(raw)
    return results


def _looks_like_environment_failure(result: SourceResult) -> bool:
    error = result.error.lower()
    markers = (
        "[errno 22]",
        "invalid argument",
        "invalidurl",
        "unknown scheme",
        "proxyerror",
        "ssl_cert_file",
        "ssl_cert_dir",
    )
    return result.status == "error" and any(marker in error for marker in markers)


async def collect_sources(
    sources: list[SourceConfig],
    debug: bool = False,
    use_scrapling: bool = True,
) -> dict[str, dict[str, Any]]:
    """Collect all sources concurrently and return normalized evidence."""
    set_diagnostic_context(stage="collect.initialize")
    diagnostic_event(
        "collector.started",
        source_count=len(sources),
        source_names=[source.name for source in sources],
        source_types={source.name: source.type for source in sources},
        debug=debug,
        use_scrapling=use_scrapling,
    )
    safe_console_print(CONSOLE, "\n[bold cyan]📡 采集并标准化数据...[/]")
    table = Table(box=None, padding=(0, 2))
    table.add_column("信源", style="cyan")
    table.add_column("类型", style="yellow")
    table.add_column("状态")
    table.add_column("有效条目")

    settings = _network_settings()
    trust_env = bool(settings.get("trust_env", True))
    fallback_without_env = bool(settings.get("fallback_without_env", True))
    set_diagnostic_context(stage="collect.client")
    client: httpx.AsyncClient | None = None
    try:
        client = _build_http_client(settings, trust_env=trust_env)
    except Exception as first_error:
        diagnostic_exception(
            "collector.http_client_init_failed",
            first_error,
            trust_env=trust_env,
            fallback_without_env=fallback_without_env,
        )
        if not trust_env or not fallback_without_env:
            raise CollectionSetupError(
                "HTTP 采集器初始化失败（COLLECT-CLIENT-INIT），请下载诊断日志"
            ) from first_error
        diagnostic_event("collector.http_client_fallback", reason="initialization_failed")
        try:
            trust_env = False
            client = _build_http_client(settings, trust_env=False)
        except Exception as fallback_error:
            diagnostic_exception(
                "collector.http_client_fallback_failed",
                fallback_error,
                trust_env=False,
            )
            raise CollectionSetupError(
                "HTTP 采集器初始化失败（COLLECT-CLIENT-FALLBACK），请下载诊断日志"
            ) from fallback_error

    set_diagnostic_context(stage="collect.sources")
    try:
        source_results = await _collect_with_client(client, sources, debug, use_scrapling)
    finally:
        await _safe_close_client(client, trust_env=trust_env)

    retry_indices = [
        index
        for index, (source, result) in enumerate(zip(sources, source_results))
        if not (source.type == "scrapling" and use_scrapling)
        and _looks_like_environment_failure(result)
    ]
    if trust_env and fallback_without_env and retry_indices:
        diagnostic_event(
            "collector.environment_fallback_started",
            source_names=[sources[index].name for index in retry_indices],
            reason="environment_or_proxy_error",
        )
        direct_client: httpx.AsyncClient | None = None
        try:
            direct_client = _build_http_client(settings, trust_env=False)
            retry_sources = [sources[index] for index in retry_indices]
            replacements = await _collect_with_client(
                direct_client,
                retry_sources,
                debug,
                use_scrapling,
            )
            for index, replacement in zip(retry_indices, replacements):
                source_results[index] = replacement
            diagnostic_event(
                "collector.environment_fallback_finished",
                recovered_sources=[
                    source.name
                    for source, result in zip(retry_sources, replacements)
                    if result.status == "ok"
                ],
            )
        except Exception as fallback_error:
            diagnostic_exception("collector.environment_fallback_failed", fallback_error)
        finally:
            if direct_client is not None:
                await _safe_close_client(direct_client, trust_env=False)

    results: dict[str, dict[str, Any]] = {}
    for source, result in zip(sources, source_results):
        results[source.name] = result.to_dict()
        if result.status == "ok":
            table.add_row(source.display_name, source.type, "✅", str(len(result.items)))
        else:
            table.add_row(
                source.display_name,
                source.type,
                "❌",
                (result.error or "无有效条目")[:60],
            )

    safe_console_print(CONSOLE, table)
    item_count = sum(len(result.items) for result in source_results)
    success_count = sum(result.status == "ok" for result in source_results)
    safe_console_print(
        CONSOLE,
        f"  [green]✅ {success_count}/{len(sources)} 个信源有效，"
        f"共 {item_count} 条可追溯证据[/]"
    )
    set_diagnostic_context(stage="collect.finished")
    diagnostic_event(
        "collector.finished",
        success_count=success_count,
        failure_count=len(sources) - success_count,
        evidence_count=item_count,
        sources={
            source.name: {
                "status": result.status,
                "item_count": len(result.items),
                "error": result.error,
            }
            for source, result in zip(sources, source_results)
        },
    )
    return results


async def _fetch_source(
    client: httpx.AsyncClient,
    src: SourceConfig,
    debug: bool,
    use_scrapling: bool,
) -> SourceResult:
    started = time.monotonic()
    set_diagnostic_context(stage="collect.source")
    diagnostic_event(
        "collector.source_started",
        "DEBUG",
        source=src.name,
        display_name=src.display_name,
        source_type=src.type,
        adapter="scrapling" if src.type == "scrapling" and use_scrapling else "httpx",
        url=_url_descriptor(src.url),
    )
    try:
        if src.type == "scrapling" and use_scrapling:
            items = await _fetch_scrapling(src, debug)
        else:
            items = await _fetch_http(client, src)
        if not items:
            raise ValueError("响应中没有可验证的标题与链接")
        result = SourceResult(
            source_name=src.name,
            display_name=src.display_name,
            source_url=src.url,
            status="ok",
            items=items[:_MAX_ITEMS],
        )
        diagnostic_event(
            "collector.source_succeeded",
            source=src.name,
            source_type=src.type,
            item_count=len(result.items),
            elapsed_ms=round((time.monotonic() - started) * 1000, 2),
        )
        return result
    except Exception as exc:
        diagnostic_exception(
            "collector.source_failed",
            exc,
            source=src.name,
            display_name=src.display_name,
            source_type=src.type,
            adapter="scrapling" if src.type == "scrapling" and use_scrapling else "httpx",
            url=_url_descriptor(src.url),
            elapsed_ms=round((time.monotonic() - started) * 1000, 2),
        )
        return SourceResult(
            source_name=src.name,
            display_name=src.display_name,
            source_url=src.url,
            status="error",
            error=redact_sensitive_text(f"{type(exc).__name__}: {exc}"),
        )


async def _fetch_http(
    client: httpx.AsyncClient,
    src: SourceConfig,
) -> list[EvidenceItem]:
    request_started = time.monotonic()
    response = await client.get(src.url, headers=src.headers or None)
    diagnostic_event(
        "collector.http_response",
        "DEBUG",
        source=src.name,
        status_code=response.status_code,
        content_type=response.headers.get("content-type", "").split(";", 1)[0],
        content_length=len(response.content),
        elapsed_ms=round((time.monotonic() - request_started) * 1000, 2),
        final_url=_url_descriptor(str(response.url)),
        redirect_count=len(response.history),
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if src.type == "rss" or "xml" in content_type:
        return _parse_feed(response.text, src)

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError(
            "该信源未返回 JSON/RSS；请为网页配置 Scrapling 选择器"
        ) from exc

    if src.name == "hackernews":
        return await _fetch_hackernews_items(client, payload, src)
    return _parse_json_payload(payload, src)


async def _fetch_hackernews_items(
    client: httpx.AsyncClient,
    payload: Any,
    src: SourceConfig,
) -> list[EvidenceItem]:
    if not isinstance(payload, list):
        raise ValueError("Hacker News topstories 返回格式异常")
    ids = [item_id for item_id in payload[:_MAX_ITEMS] if isinstance(item_id, int)]
    responses = await asyncio.gather(
        *[
            client.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
            for item_id in ids
        ],
        return_exceptions=True,
    )
    items: list[EvidenceItem] = []
    for index, response in enumerate(responses):
        if isinstance(response, Exception) or response.status_code != 200:
            continue
        data = response.json()
        title = str(data.get("title", "")).strip()
        if not title:
            continue
        item_id = data.get("id", ids[index])
        url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        items.append(
            _item(
                src,
                index,
                title=title,
                url=url,
                published_at=_unix_time(data.get("time")),
                summary=f"score={data.get('score', 0)}, comments={data.get('descendants', 0)}",
                author=str(data.get("by", "")),
            )
        )
    return items


def _parse_feed(text: str, src: SourceConfig) -> list[EvidenceItem]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError("信源标记为 RSS，但返回内容不是有效 XML") from exc

    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    items: list[EvidenceItem] = []
    for index, entry in enumerate(entries[:_MAX_ITEMS]):
        title = _xml_text(entry, "title")
        link = _xml_text(entry, "link")
        if not link:
            link_node = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.attrib.get("href", "") if link_node is not None else ""
        if not title or not link:
            continue
        summary = (
            _xml_text(entry, "description")
            or _xml_text(entry, "summary")
            or _xml_text(entry, "content")
        )
        published = (
            _xml_text(entry, "pubDate")
            or _xml_text(entry, "published")
            or _xml_text(entry, "updated")
        )
        items.append(
            _item(
                src,
                index,
                title=title,
                url=link,
                published_at=published,
                summary=_clean_text(summary),
            )
        )
    return items


def _parse_json_payload(payload: Any, src: SourceConfig) -> list[EvidenceItem]:
    records: list[dict[str, Any]] = []

    if src.name == "github" and isinstance(payload, dict):
        records = payload.get("items", [])
    elif src.name == "reddit" and isinstance(payload, dict):
        records = [child.get("data", {}) for child in payload.get("data", {}).get("children", [])]
    elif src.name == "bilibili" and isinstance(payload, dict):
        records = payload.get("data", {}).get("list", [])
    elif src.name == "sina_finance" and isinstance(payload, dict):
        records = payload.get("result", {}).get("data", [])
    elif src.name == "163_music" and isinstance(payload, dict):
        records = payload.get("result", {}).get("hots", [])
    elif src.name == "weibo_hot" and isinstance(payload, dict):
        records = payload.get("data", {}).get("realtime", [])
    elif isinstance(payload, dict) and isinstance(payload.get("subjects"), list):
        records = payload["subjects"]
    elif isinstance(payload, dict) and isinstance(payload.get("articles"), list):
        records = payload["articles"]
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        records = payload["data"]
    elif isinstance(payload, list):
        records = [record for record in payload if isinstance(record, dict)]
    elif isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                records = value
                break

    items: list[EvidenceItem] = []
    for index, record in enumerate(records[:_MAX_ITEMS]):
        title = _first(record, "title", "full_name", "name", "first", "subject", "desc", "note", "word_scheme")
        if not title:
            continue
        url = _first(record, "html_url", "url", "link", "short_link_v2")
        if src.name == "reddit" and url.startswith("/"):
            url = urljoin("https://www.reddit.com", url)
        if src.name == "bilibili" and not url and record.get("bvid"):
            url = f"https://www.bilibili.com/video/{record['bvid']}"
        if not url:
            url = src.url
        summary = _first(record, "description", "summary", "content", "abstract")
        metadata = {
            key: record[key]
            for key in ("score", "stargazers_count", "forks_count", "replies", "rate")
            if key in record and isinstance(record[key], (str, int, float))
        }
        items.append(
            _item(
                src,
                index,
                title=title,
                url=url,
                published_at=_first(record, "publishedAt", "updated_at", "created_at", "pubdate", "ctime"),
                summary=_clean_text(summary),
                author=_author(record),
                metadata=metadata,
            )
        )
    return items


async def _fetch_scrapling(src: SourceConfig, debug: bool) -> list[EvidenceItem]:
    diagnostic_event(
        "collector.scrapling_initializing",
        "DEBUG",
        source=src.name,
        mode=src.scrapling_mode,
        selector_names=sorted(src.selectors),
        debug=debug,
    )
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError as exc:
        raise RuntimeError("Scrapling 未安装") from exc

    if not src.selectors.get("item") or not src.selectors.get("title"):
        raise ValueError("Scrapling 信源必须配置 item 与 title 选择器")

    def _blocking_fetch():
        StealthyFetcher.adaptive = True
        return StealthyFetcher.fetch(
            url=src.url,
            headless=True,
            network_idle=True,
            timeout=30000,
        )

    page = await asyncio.to_thread(_blocking_fetch)
    items: list[EvidenceItem] = []
    for index, node in enumerate(page.css(src.selectors["item"])[:_MAX_ITEMS]):
        title = str(node.css(src.selectors["title"]).get() or "").strip()
        link_selector = src.selectors.get("link", "")
        link = str(node.css(link_selector).get() or "").strip() if link_selector else ""
        if title and link:
            items.append(
                _item(src, index, title=_clean_text(title), url=urljoin(src.url, link))
            )
    return items


def _item(
    src: SourceConfig,
    index: int,
    *,
    title: str,
    url: str,
    published_at: str = "",
    summary: str = "",
    author: str = "",
    metadata: dict[str, Any] | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        source_id=f"{src.name}:{index + 1}",
        source_name=src.display_name,
        title=_clean_text(str(title))[:300],
        url=str(url).strip(),
        published_at=str(published_at or ""),
        summary=_clean_text(str(summary))[:_MAX_SUMMARY_CHARS],
        author=str(author or "")[:120],
        metadata=metadata or {},
    )


def _xml_text(node: ET.Element, local_name: str) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1] == local_name:
            return "".join(child.itertext()).strip()
    return ""


def _clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _first(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and not isinstance(value, (dict, list)):
            return str(value).strip()
    return ""


def _author(record: dict[str, Any]) -> str:
    value = record.get("author") or record.get("owner") or record.get("by") or ""
    if isinstance(value, dict):
        return str(value.get("login") or value.get("name") or "")
    return str(value)


def _unix_time(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""
