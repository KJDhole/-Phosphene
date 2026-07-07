"""Pydantic 请求/响应模型"""

from pydantic import BaseModel
from typing import Optional


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
    categories: list[str]
    debug: bool = False


class RunStatus(BaseModel):
    running: bool
    current_category: Optional[str] = None


class ArticleSummary(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: list[str]


class ArticleDetail(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: dict[str, str]


class ConfigOut(BaseModel):
    content: str


class ConfigIn(BaseModel):
    content: str
