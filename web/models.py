"""Pydantic 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


class SourceInfo(BaseModel):
    name: str
    display_name: str
    type: str


class CategoryOut(BaseModel):
    name: str
    display_name: str
    emoji: str
    description: str
    sources: list[SourceInfo]


class RunRequest(BaseModel):
    categories: list[str] = Field(min_length=1, max_length=10)
    debug: bool = False
    use_scrapling: bool = True


class RunStatus(BaseModel):
    running: bool
    current_category: Optional[str] = None
    task_id: Optional[str] = None
    status: str = "idle"


class ArticleSummary(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: list[str]
    review_status: str = "legacy_unverified"
    quality_passed: bool = False
    evidence_count: int = 0
    issue_count: int = 0
    deployment_ready: bool = False


class ArticleDetail(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: dict[str, str]
    review_status: str = "legacy_unverified"
    review_note: str = ""
    quality: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    deployment_ready: bool = False


class ReviewUpdate(BaseModel):
    status: Literal["awaiting_review", "changes_requested", "approved"]
    note: str = Field(default="", max_length=1000)


class ConfigOut(BaseModel):
    content: str


class ConfigIn(BaseModel):
    content: str

class VideoStatus(BaseModel):
    slug: str
    status: str = "pending"  # pending | generating | done | failed
    progress: float = 0.0
    video_url: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    review_status: str = "awaiting_review"


class VideoReviewUpdate(BaseModel):
    status: Literal["awaiting_review", "changes_requested", "approved"]
    note: str = Field(default="", max_length=1000)

class VideoConfig(BaseModel):
    """✅ 预留 — 下版本使用"""
    prompt_template: str = ""
    voice: str = "zh-CN-XiaoxiaoNeural"
    scene_overrides: dict = Field(default_factory=dict)
