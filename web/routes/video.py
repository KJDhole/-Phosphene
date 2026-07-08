"""视频生成 API — 触发/状态/下载/预留配置"""

import os
import time
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

    # 检查是否在生成中
    if slug in _generating:
        return _generating[slug]

    # 检查是否已生成
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

    from fastapi.responses import FileResponse
    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"{slug}.mp4",
    )


@router.post("/video/generate/{slug}")
def trigger_generate_video(slug: str, category: str):
    """触发视频生成"""
    from core.video_generator import generate_video as _gen_video

    if slug in _generating and _generating[slug].status == "generating":
        raise HTTPException(400, "视频正在生成中")

    status = VideoStatus(slug=slug, status="generating")
    _generating[slug] = status

    try:
        posts_dir = ROOT / "docs" / "posts"
        result = _gen_video(category, slug, posts_dir)
        status.status = "done"
        status.progress = 1.0
        status.video_url = f"/api/video/{slug}"
    except Exception as e:
        status.status = "failed"
        status.error = str(e)

    return status


# ✅ 预留 — 下版本实现
@router.put("/video/{slug}/config")
def update_video_config(slug: str, config: VideoConfig):
    """更新单篇文章的视频配置（预留）"""
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.put("/video/config")
def update_global_video_config(config: VideoConfig):
    """更新全局视频配置（预留）"""
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.get("/video/config")
def get_global_video_config():
    """获取全局视频配置（预留）"""
    cfg = load_config()
    video_cfg = cfg.get("video", {})
    return VideoConfig(
        prompt_template=video_cfg.get("prompt_template", ""),
        voice=video_cfg.get("audio_voice", "zh-CN-XiaoxiaoNeural"),
    )


def _find_video(slug: str, category: Optional[str], posts_dir: Path) -> Optional[Path]:
    """在所有分类中搜索视频文件"""
    if category:
        vp = posts_dir / category / slug / "video.mp4"
        return vp if vp.exists() else None

    for cat_dir in posts_dir.iterdir():
        if cat_dir.is_dir():
            vp = cat_dir / slug / "video.mp4"
            if vp.exists():
                return vp
    return None
