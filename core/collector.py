"""
通用采集引擎 — 支持 API / RSS / Scrapling 三种信源类型
"""

from __future__ import annotations
import httpx
from typing import Optional
from rich.console import Console
from rich.table import Table

from core.base_category import SourceConfig

CONSOLE = Console()


async def collect_sources(sources: list[SourceConfig], debug: bool = False) -> dict:
    """并行采集所有信源"""
    import asyncio
    from copy import deepcopy

    CONSOLE.print("\n[bold cyan]📡 采集数据...[/]")
    table = Table(box=None, padding=(0, 2))
    table.add_column("信源", style="cyan")
    table.add_column("类型", style="yellow")
    table.add_column("状态", style="green")
    table.add_column("摘要")

    results = {}
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_source(client, src, debug) for src in sources]
        for coro in asyncio.as_completed(tasks):
            name, data, err = await coro
            if err:
                results[name] = f"[采集失败] {err}"
                table.add_row(name, "", "❌", err[:50])
            elif data:
                results[name] = data
                snippet = data.strip().replace("\n", " ")[:60]
                src_type = next((s.type for s in sources if s.name == name), "")
                table.add_row(name, src_type, "✅", snippet)
            else:
                results[name] = "[采集失败] 无数据"
                src_type = next((s.type for s in sources if s.name == name), "")
                table.add_row(name, src_type, "⚠️", "空响应")

    CONSOLE.print(table)
    success = sum(1 for v in results.values() if v and not v.startswith("[采集失败]"))
    CONSOLE.print(f"  [green]✅ {success}/{len(sources)} 个信源采集成功[/]")
    return results


async def _fetch_source(client: httpx.AsyncClient, src: SourceConfig, debug: bool) -> tuple:
    """采集单个信源"""
    if src.type == "scrapling":
        return await _fetch_scrapling(src, debug)
    else:
        # API / RSS 都走 httpx
        return await _fetch_http(client, src, debug)


async def _fetch_http(client: httpx.AsyncClient, src: SourceConfig, debug: bool) -> tuple:
    """HTTP 请求采集（API / RSS）"""
    headers = src.headers or {}
    try:
        resp = await client.get(src.url, headers=headers, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        raw = resp.text[:5000]
        return src.name, raw, None
    except Exception as e:
        return src.name, None, f"{type(e).__name__}: {e}"


async def _fetch_scrapling(src: SourceConfig, debug: bool) -> tuple:
    """Scrapling 智能抓取"""
    from scrapling.fetchers import StealthyFetcher

    try:
        # 配置 Scrapling
        StealthyFetcher.adaptive = True

        kwargs = dict(
            url=src.url,
            headless=True,
            network_idle=True,
            timeout=30000,
        )

        if debug:
            # CONSOLE.print(f"  [dim]🕷️  Scrapling 抓取: {src.url}[/]")
            pass

        page = StealthyFetcher.fetch(**kwargs)

        # 如果有选择器，提取结构化数据
        if src.selectors and src.selectors.get("item"):
            items = page.css(src.selectors["item"])
            results = []
            for item in items[:15]:  # 最多 15 条
                title_sel = src.selectors.get("title", "")
                link_sel = src.selectors.get("link", "")
                if title_sel:
                    title = item.css(title_sel).get()
                    if link_sel:
                        link = item.css(link_sel).get()
                        results.append(f"- {title} ({link})")
                    else:
                        results.append(f"- {title}")
            data = "\n".join(results) if results else page.text[:5000]
        else:
            data = page.text[:5000]

        return src.name, data, None
    except ImportError:
        return src.name, None, "Scrapling 未安装 (pip install ./tools/Scrapling-main)"
    except Exception as e:
        return src.name, None, f"ScraplingError: {e}"
