"""视频生成 API — 触发/状态/下载/预留配置"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from web.routes import router
from web.models import VideoStatus, VideoConfig
from main import ROOT, load_config

# 运行状态（进程内简单存储）
_generating: dict[str, VideoStatus] = {}


@router.get("/video/status/{slug}", response_model=VideoStatus)
def get_video_status(slug: str, category: Optional[str] = None):
    """查询视频生成状态"""
    posts_dir = ROOT / "docs" / "posts"

    if slug in _generating:
        return _generating[slug]

    video_path = _find_video(slug, category, posts_dir)
    if video_path:
        return VideoStatus(
            slug=slug,
            status="done",
            progress=1.0,
            video_url=f"/api/video/{slug}",
        )

    return VideoStatus(slug=slug, status="pending")


@router.get("/video/{slug}")
def get_video(slug: str, category: Optional[str] = None):
    """提供已生成的视频文件"""
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
    if slug in _generating and _generating[slug].status == "generating":
        raise HTTPException(400, "视频正在生成中")

    status = VideoStatus(slug=slug, status="generating", progress=0.0)
    _generating[slug] = status

    asyncio.create_task(_run_generate(slug, category))
    return status


async def _run_generate(slug: str, category: str):
    """后台执行视频生成，逐步更新进度"""
    from core.video_generator import generate_video as _gen_video

    def update_progress(pct: float, msg: str):
        if slug in _generating:
            _generating[slug].progress = round(pct, 2)
            _generating[slug].error = msg

    try:
        update_progress(0.05, "开始生成...")
        posts_dir = ROOT / "docs" / "posts"

        # 在线程池中执行同步的 _gen_video，传 progress_callback
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _gen_video(category, slug, posts_dir, update_progress),
        )

        if slug in _generating:
            _generating[slug].status = "done"
            _generating[slug].progress = 1.0
            _generating[slug].video_url = f"/api/video/{slug}"
            _generating[slug].error = None

    except Exception as e:
        if slug in _generating:
            _generating[slug].status = "failed"
            _generating[slug].error = str(e)


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

    for cat_dir in posts_dir.iterdir():
        if cat_dir.is_dir():
            vp = cat_dir / slug / "video.mp4"
            if vp.exists():
                return vp
    return None
