"""视频生成 API — 触发/状态/下载/预留配置"""

import asyncio
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from web.routes import router
from web.models import VideoStatus, VideoConfig, VideoReviewUpdate
from core.config import ROOT, load_config

# 运行状态（进程内简单存储）
_generating: dict[str, VideoStatus] = {}


@router.get("/video/status/{slug}", response_model=VideoStatus)
def get_video_status(slug: str, category: Optional[str] = None):
    """查询视频生成状态"""
    _validate_slug(slug)
    if category:
        _validate_identifiers(slug, category)
    posts_dir = ROOT / "docs" / "posts"

    key = _video_key(slug, category)
    if key in _generating:
        return _generating[key]

    video_path = _find_video(slug, category, posts_dir)
    if video_path:
        review_status = "awaiting_review"
        manifest = video_path.parent / "video_manifest.json"
        if manifest.exists():
            import json
            review_status = json.loads(manifest.read_text(encoding="utf-8")).get("review_status", review_status)
        return VideoStatus(
            slug=slug,
            status="done",
            progress=1.0,
            video_url=f"/api/video/{slug}?category={category}" if category else f"/api/video/{slug}",
            review_status=review_status,
        )

    return VideoStatus(slug=slug, status="pending")


@router.get("/video/{slug}")
def get_video(slug: str, category: Optional[str] = None):
    """提供已生成的视频文件"""
    _validate_slug(slug)
    if category:
        _validate_identifiers(slug, category)
    posts_dir = ROOT / "docs" / "posts"
    video_path = _find_video(slug, category, posts_dir)

    if not video_path or not video_path.exists():
        raise HTTPException(404, "视频尚未生成")

    size = video_path.stat().st_size
    if size == 0:
        raise HTTPException(500, "视频文件为空，生成可能失败")

    from fastapi.responses import FileResponse
    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"{slug}.mp4",
        headers={
            "Content-Length": str(size),
            "Accept-Ranges": "bytes",
        },
    )


@router.post("/video/generate/{slug}")
async def trigger_generate_video(slug: str, category: str):
    """触发视频生成（异步后台任务）"""
    _validate_identifiers(slug, category)
    key = _video_key(slug, category)
    if key in _generating and _generating[key].status == "generating":
        raise HTTPException(400, "视频正在生成中")

    script_path = ROOT / "docs" / "posts" / category / slug / "video_script.md"
    if not script_path.exists():
        raise HTTPException(404, "视频脚本不存在")

    status = VideoStatus(slug=slug, status="generating", progress=0.0)
    _generating[key] = status

    asyncio.create_task(_run_generate(slug, category))
    return status


@router.put("/video/{slug}/review")
def review_video(slug: str, review: VideoReviewUpdate, category: str):
    """Approve or return a rendered preview for revision."""
    _validate_identifiers(slug, category)
    manifest = ROOT / "docs" / "posts" / category / slug / "video_manifest.json"
    if not manifest.exists():
        raise HTTPException(404, "视频审核清单不存在，请先生成视频")
    from core.video_generator import update_video_review_status
    update_video_review_status(manifest, review.status, review.note)
    return {"slug": slug, "status": review.status, "note": review.note}


async def _run_generate(slug: str, category: str):
    """后台执行视频生成，逐步更新进度"""
    from core.video_generator import generate_video as _gen_video

    key = _video_key(slug, category)

    def update_progress(pct: float, msg: str):
        if key in _generating:
            _generating[key].progress = round(pct, 2)
            _generating[key].message = msg

    try:
        update_progress(0.05, "开始生成...")
        posts_dir = ROOT / "docs" / "posts"

        # 在线程池中执行同步的 _gen_video，传 progress_callback
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _gen_video(category, slug, posts_dir, update_progress),
        )

        if key in _generating:
            _generating[key].status = "done"
            _generating[key].progress = 1.0
            _generating[key].video_url = f"/api/video/{slug}?category={category}"
            _generating[key].error = None
            _generating[key].message = "视频生成完成"

    except Exception as e:
        if key in _generating:
            _generating[key].status = "failed"
            _generating[key].error = str(e)
            _generating[key].message = "视频生成失败"


# ✅ 预留 — 下版本实现
@router.put("/video/{slug}/config")
def update_video_config(slug: str, config: VideoConfig):
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.put("/video/config")
def update_global_video_config(config: VideoConfig):
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.get("/video/config")
def get_global_video_config():
    cfg = load_config()
    video_cfg = cfg.get("video", {})
    return VideoConfig(
        prompt_template=video_cfg.get("prompt_template", ""),
        voice=video_cfg.get("audio_voice", "zh-CN-XiaoxiaoNeural"),
    )


def _find_video(slug: str, category: Optional[str], posts_dir: Path) -> Optional[Path]:
    if category:
        vp = posts_dir / category / slug / "video.mp4"
        return vp if vp.exists() else None

    if not posts_dir.exists():
        return None
    for cat_dir in posts_dir.iterdir():
        if cat_dir.is_dir():
            vp = cat_dir / slug / "video.mp4"
            if vp.exists():
                return vp
    return None


def _video_key(slug: str, category: Optional[str]) -> str:
    return f"{category or '*'}:{slug}"


def _validate_identifiers(slug: str, category: str) -> None:
    from core.registry import get_category

    _validate_slug(slug)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", category) or get_category(category) is None:
        raise HTTPException(400, "非法分类")


def _validate_slug(slug: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
        raise HTTPException(400, "非法 slug")
