"""History, evidence inspection and human-review APIs."""

from __future__ import annotations

import json
import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Query

from core.config import ROOT
from core.quality import (
    ContentQualityError,
    normalize_citation_syntax,
    validate_generated_content,
)
from web.models import ArticleDetail, ArticleSummary, ReviewUpdate
from web.routes import router

BJT = timezone(timedelta(hours=8))
_cache_result: list[dict[str, Any]] | None = None
_cache_mtime: float = 0


def _extract_title(blog_text: str) -> str:
    for line in blog_text.split("\n"):
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match and not line.startswith("##"):
            return match.group(1).strip()
    return "未命名文章"


def _parse_slug_date(slug: str) -> str:
    base = "_".join(slug.split("_")[:2])
    for fmt in ("%Y%m%d_%H%M%S", "%Y%m%d_%H%M"):
        try:
            return datetime.strptime(base, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return slug


def _read_metadata(slug_dir: Path) -> dict[str, Any]:
    path = slug_dir / "metadata.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _flatten_evidence(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    results = metadata.get("evidence")
    if not isinstance(results, dict):
        return []
    flattened: list[dict[str, Any]] = []
    for result in results.values():
        if not isinstance(result, dict) or result.get("status") != "ok":
            continue
        source_display = str(result.get("display_name") or result.get("source_name") or "")
        for item in result.get("items", []):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            normalized["source_display_name"] = source_display
            flattened.append(normalized)
    return flattened


def _article_record(category: str, slug_dir: Path, blog_text: str) -> dict[str, Any]:
    metadata = _read_metadata(slug_dir)
    quality = metadata.get("quality") if isinstance(metadata.get("quality"), dict) else {}
    evidence = _flatten_evidence(metadata)
    errors = quality.get("errors") if isinstance(quality.get("errors"), list) else []
    warnings = quality.get("warnings") if isinstance(quality.get("warnings"), list) else []
    formats = sorted(file.stem for file in slug_dir.iterdir() if file.suffix == ".md")
    review_status = str(metadata.get("review_status") or "legacy_unverified")
    approved_hash = metadata.get("approved_content_sha256")
    current_hash = hashlib.sha256(blog_text.encode("utf-8")).hexdigest()
    deployment_ready = review_status == "approved" and approved_hash == current_hash
    return {
        "slug": slug_dir.name,
        "category": category,
        "title": _extract_title(blog_text),
        "date": _parse_slug_date(slug_dir.name),
        "formats": formats,
        "review_status": review_status,
        "quality_passed": bool(quality.get("passed", False)),
        "evidence_count": int(quality.get("evidence_count") or len(evidence)),
        "issue_count": len(errors) + len(warnings) + int(review_status == "approved" and not deployment_ready),
        "deployment_ready": deployment_ready,
    }


def _scan_articles(force: bool = False) -> list[dict[str, Any]]:
    global _cache_result, _cache_mtime
    posts_dir = ROOT / "docs" / "posts"
    if not posts_dir.exists():
        return []

    current_mtime = 0.0
    try:
        current_mtime = max(
            (path.stat().st_mtime for path in posts_dir.rglob("*") if path.is_file()),
            default=0.0,
        )
    except OSError:
        current_mtime = time.time()

    if not force and _cache_result is not None and current_mtime == _cache_mtime:
        return _cache_result

    articles: list[dict[str, Any]] = []
    for category_dir in sorted(posts_dir.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("__"):
            continue
        for slug_dir in sorted(category_dir.iterdir(), reverse=True):
            blog_path = slug_dir / "blog.md"
            if not slug_dir.is_dir() or not blog_path.exists():
                continue
            articles.append(
                _article_record(
                    category_dir.name,
                    slug_dir,
                    blog_path.read_text(encoding="utf-8"),
                )
            )
    articles.sort(key=lambda article: article["slug"], reverse=True)
    _cache_result = articles
    _cache_mtime = current_mtime
    return articles


def _resolve_article(slug: str, category: str | None) -> dict[str, Any]:
    matched = [article for article in _scan_articles() if article["slug"] == slug]
    if category:
        matched = [article for article in matched if article["category"] == category]
    elif len(matched) > 1:
        raise HTTPException(status_code=409, detail="slug 跨分类重复，请提供 category")
    if not matched:
        raise HTTPException(status_code=404, detail="文章不存在")
    return matched[0]


def _article_directory(article: dict[str, Any]) -> Path:
    return ROOT / "docs" / "posts" / article["category"] / article["slug"]


def _detail(article: dict[str, Any]) -> ArticleDetail:
    slug_dir = _article_directory(article)
    formats: dict[str, str] = {}
    for fmt in article["formats"]:
        path = slug_dir / f"{fmt}.md"
        if path.exists():
            formats[fmt] = path.read_text(encoding="utf-8")
    metadata = _read_metadata(slug_dir)
    quality = metadata.get("quality") if isinstance(metadata.get("quality"), dict) else {}
    detail = dict(article)
    detail["formats"] = formats
    return ArticleDetail(
        **detail,
        review_note=str(metadata.get("review_note") or ""),
        quality=quality,
        evidence=_flatten_evidence(metadata),
    )


@router.get("/history", response_model=list[ArticleSummary])
def get_history(category: str | None = Query(None)):
    articles = _scan_articles()
    if category:
        articles = [article for article in articles if article["category"] == category]
    return [ArticleSummary(**article) for article in articles]


@router.get("/history/{slug}", response_model=ArticleDetail)
def get_article_detail(slug: str, category: str | None = Query(None)):
    return _detail(_resolve_article(slug, category))


@router.put("/history/{slug}/review", response_model=ArticleDetail)
def update_article_review(
    slug: str,
    request: ReviewUpdate,
    category: str | None = Query(None),
):
    """Persist a review decision; approval re-runs the strict quality gate."""
    article = _resolve_article(slug, category)
    slug_dir = _article_directory(article)
    metadata = _read_metadata(slug_dir)
    if not metadata:
        raise HTTPException(status_code=409, detail="历史文章缺少证据元数据，请重新生成后审核")

    if request.status == "approved":
        blog_path = slug_dir / "blog.md"
        original_blog = blog_path.read_text(encoding="utf-8")
        blog = normalize_citation_syntax(original_blog)
        evidence = metadata.get("evidence")
        if not isinstance(evidence, dict):
            raise HTTPException(status_code=409, detail="文章缺少可追溯证据，不能通过审核")
        try:
            report = validate_generated_content(blog, evidence, article["category"])
        except ContentQualityError as exc:
            raise HTTPException(status_code=409, detail=f"质量校验未通过：{exc}") from exc
        metadata["quality"] = report.to_dict()
        metadata["approved_content_sha256"] = hashlib.sha256(blog.encode("utf-8")).hexdigest()
        if blog != original_blog:
            temporary_blog = blog_path.with_suffix(".md.tmp")
            temporary_blog.write_text(blog, encoding="utf-8")
            temporary_blog.replace(blog_path)

    metadata["review_status"] = request.status
    if request.status != "approved":
        metadata.pop("approved_content_sha256", None)
    metadata["review_note"] = request.note.strip()
    metadata["reviewed_at"] = datetime.now(BJT).isoformat()
    metadata_path = slug_dir / "metadata.json"
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(metadata_path)
    _scan_articles(force=True)
    return _detail(_resolve_article(slug, article["category"]))


@router.delete("/history/{slug}")
def delete_article(slug: str, category: str | None = Query(None)):
    import shutil

    article = _resolve_article(slug, category)
    posts_dir = _article_directory(article)
    if posts_dir.exists():
        shutil.rmtree(posts_dir)
    _scan_articles(force=True)

    from core.config import load_config
    from core.output import OutputManager

    OutputManager(load_config(), article["category"]).update_index()
    return {"status": "deleted"}


@router.post("/history/{slug}/rerun")
async def rerun_article(slug: str, category: str | None = Query(None)):
    from web.routes.run import run_category

    article = _resolve_article(slug, category)
    return await run_category(article["category"])
