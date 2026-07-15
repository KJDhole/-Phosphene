"""  
分类基类 — 每个分类继承此类，实现自己的采集和提示词  
"""  

from __future__ import annotations  
import abc  
from typing import Optional  
from pathlib import Path  
from dataclasses import dataclass, field  
from datetime import datetime, timezone, timedelta  

# 北京时间  
BJT = timezone(timedelta(hours=8))  

# ── 质量准则 —— 所有分类共享 ──  
QUALITY_CRITERIA = """## 质量准则  

1. 事实核查：每个论断必须有数据支撑，不可凭空编造数字、引语或案例  
2. 来源透明：如果采集数据不足以支持某个观点，明确标注「基于AI知识补充」，不得伪装成数据结论  
3. 精度要求：涉及数字、版本号、日期、百分比时务必精确，不使用「很多人」「大量研究表明」等模糊表述  
4. 逻辑严谨：论点之间要有清晰的递进关系，避免跳跃式论证  
5. 公正客观：争议性话题呈现多方观点，不站队不煽动  
6. 长尾质量：标题不夸大、不标题党，内容对得起标题的承诺"""  

SIGNATURE_FOOTER = "\n\n---\n*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*"  


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

    # ── 共享 prompt 构建方法 ──  

    def _build_user_prompt(  
        self,  
        domain_label: str,  
        sections: list[dict],  
        raw_data: dict,  
        word_count: str = "1500-2000",  
    ) -> str:  
        """构建标准化的 user prompt  

        Args:  
            domain_label: 领域名称，如 "技术圈"  
            sections: 文章结构要求，每项含 title + content  
            raw_data: 采集数据 dict  
            word_count: 建议字数范围  
        """  
        now = datetime.now(BJT)  

        # ── 数据摘要 ──  
        summary_lines = []  
        for name, data in raw_data.items():  
            if data and not data.startswith("[采集失败"):  
                summary_lines.append(f"\n## {name}")  
                summary_lines.append(data.strip()[:800])  

        material = "\n".join(summary_lines) or "（所有平台均采集失败，根据 AI 知识库自主创作）"  

        # ── 章节指引 ──  
        section_texts = [f"- **{sec['title']}**：{sec['content']}" for sec in sections]  
        sections_str = "\n".join(section_texts)  

        return f"""今天是 {now.strftime('%Y年%m月%d日 %H:%M')}。

以下是今日{domain_label}热点数据：

{material}

请按以下流程完成写作：

**第一步：深度分析数据**  
识别其中的模式、趋势、反常信号和关键事件。找出数据之间的关联与矛盾。

**第二步：确定选题**  
选择最有价值/最有话题性的一个角度作为文章主题。说明为什么选这个角度。

**第三步：撰写文章**  
写一篇 {word_count} 字的专业文章，结构如下：

{sections_str}

{QUALITY_CRITERIA}

全文用 Markdown 格式。{SIGNATURE_FOOTER}"""

    async def collect(self, debug: bool = False, use_scrapling: bool = True) -> dict:  
        """采集该分类的所有信源数据  

        默认实现：遍历 self.sources，按 type 分发到对应采集器。  
        子类可覆盖此方法实现自定义采集逻辑。  

        :param use_scrapling: 是否启用 Scrapling 浏览器采集（type=scrapling 的信源）  
        """  
        from core.collector import collect_sources  
        return await collect_sources(self.sources, debug=debug, use_scrapling=use_scrapling)  

    def get_prompts(self, raw_data: dict) -> tuple[str, str]:  
        """生成 system/user 提示词对"""  
        user = self.user_prompt_template(raw_data)  
        return self.system_prompt, user  
