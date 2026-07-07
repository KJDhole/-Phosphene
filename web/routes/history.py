"""历史文章 CRUD API"""

import re
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query, HTTPException
from web.routes import router
from web.models import ArticleSummary, ArticleDetail
from main import ROOT

BJT = timezone(timedelta(hours=8))


def _extract_title(blog_text: str) -> str:
    for line in blog_text.split("\n"):
        m = re.match(r'^#\s+(.+)$', line.strip())
        if m and not line.startswith("##"):
            return m.group(1).strip()
    return "未命名文章"


def _parse_slug_date(slug: str) -> str:
    """从 slug 20260707_2052 解析为 2026-07-07 20:52"""
    try:
        dt = datetime.strptime(slug, "%Y%m%d_%H%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return slug


def _scan_articles() -> list[dict]:
    """扫描 docs/posts/ 下的所有文章"""
    posts_dir = ROOT / "docs" / "posts"
    if not posts_dir.exists():
        return []
    articles = []
    for cat_dir in sorted(posts_dir.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("__"):
            continue
        category = cat_dir.name
        for slug_dir in sorted(cat_dir.iterdir(), reverse=True):
            if not slug_dir.is_dir():
                continue
            blog_path = slug_dir / "blog.md"
            if not blog_path.exists():
                continue
            blog_text = blog_path.read_text(encoding="utf-8")
            title = _extract_title(blog_text)
            formats = []
            for f in sorted(slug_dir.iterdir()):
                if f.suffix == ".md":
                    formats.append(f.stem)
            articles.append({
                "slug": slug_dir.name,
                "category": category,
                "title": title,
                "date": _parse_slug_date(slug_dir.name),
                "formats": sorted(formats),
            })
    # 全局按 slug（时间戳）倒序，最新的排最前
    articles.sort(key=lambda a: a["slug"], reverse=True)
    return articles


@router.get("/history", response_model=list[ArticleSummary])
def get_history(category: str | None = Query(None)):
    articles = _scan_articles()
    if category:
        articles = [a for a in articles if a["category"] == category]
    return [ArticleSummary(**a) for a in articles]


@router.get("/history/{slug}", response_model=ArticleDetail)
def get_article_detail(slug: str, category: str | None = Query(None)):
    articles = _scan_articles()
    matched = [a for a in articles if a["slug"] == slug]
    if category:
        matched = [a for a in matched if a["category"] == category]
    if not matched:
        raise HTTPException(status_code=404, detail="文章不存在")
    article = matched[0]
    posts_dir = ROOT / "docs" / "posts" / article["category"] / slug
    formats = {}
    for fmt in article["formats"]:
        path = posts_dir / f"{fmt}.md"
        if path.exists():
            formats[fmt] = path.read_text(encoding="utf-8")
    return ArticleDetail(
        slug=article["slug"],
        category=article["category"],
        title=article["title"],
        date=article["date"],
        formats=formats,
    )


@router.delete("/history/{slug}")
def delete_article(slug: str, category: str | None = Query(None)):
    articles = _scan_articles()
    matched = [a for a in articles if a["slug"] == slug]
    if category:
        matched = [a for a in matched if a["category"] == category]
    if not matched:
        raise HTTPException(status_code=404, detail="文章不存在")

    import shutil
    posts_dir = ROOT / "docs" / "posts" / matched[0]["category"] / slug
    if posts_dir.exists():
        shutil.rmtree(posts_dir)
    return {"status": "deleted"}


@router.post("/history/{slug}/rerun")
async def rerun_article(slug: str, category: str | None = Query(None)):
    """重新生成 — 委托给 run 路由"""
    from web.routes.run import run_category
    if not category:
        articles = _scan_articles()
        matched = [a for a in articles if a["slug"] == slug]
        if not matched:
            raise HTTPException(status_code=404, detail="文章不存在")
        category = matched[0]["category"]
    return await run_category(category)
