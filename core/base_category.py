"""
分类基类 — 每个分类继承此类，实现自己的采集和提示词
"""

from __future__ import annotations
import abc
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    """单个信源配置"""
    name: str                        # 信源唯一标识
    display_name: str                # 展示名称
    type: str                        # "api" | "rss" | "scrapling"
    url: str                         # 请求 URL
    headers: Optional[dict] = None   # 请求头
    description: str = ""            # 描述
    # Scrapling 专用
    scrapling_mode: str = "stealth"  # "stealth" | "dynamic" | "requests"
    selectors: dict = field(default_factory=dict)  # CSS 选择器


@dataclass
class CategoryInfo:
    """分类元信息"""
    name: str            # "finance"
    display_name: str    # "金融财经"
    emoji: str           # "💰"
    description: str     # "金融财经热点分析"


class BaseCategory(abc.ABC):
    """所有分类的抽象基类

    子类必须实现:
      - info: CategoryInfo
      - sources: list[SourceConfig]
      - system_prompt: str
      - user_prompt_template(data) -> str

    可选覆盖:
      - collect() — 默认实现遍历 sources 自动采集
      - get_prompts(data) — 默认组合 system_prompt + user_prompt_template
    """

    @property
    @abc.abstractmethod
    def info(self) -> CategoryInfo:
        ...

    @property
    @abc.abstractmethod
    def sources(self) -> list[SourceConfig]:
        ...

    @property
    @abc.abstractmethod
    def system_prompt(self) -> str:
        """AI 系统提示词 — 定义 AI 的角色身份和写作风格"""
        ...

    @abc.abstractmethod
    def user_prompt_template(self, raw_data: dict) -> str:
        """AI 用户提示词 — 根据采集数据生成提示"""
        ...

    async def collect(self, debug: bool = False) -> dict:
        """采集该分类的所有信源数据

        默认实现：遍历 self.sources，按 type 分发到对应采集器。
        子类可覆盖此方法实现自定义采集逻辑。
        """
        from core.collector import collect_sources
        return await collect_sources(self.sources, debug=debug)

    def get_prompts(self, raw_data: dict) -> tuple[str, str]:
        """生成 system/user 提示词对"""
        user = self.user_prompt_template(raw_data)
        return self.system_prompt, user
