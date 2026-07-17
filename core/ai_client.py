"""
AI API 客户端 — 兼容 OpenAI / DeepSeek / 硅基流动 / 通义千问
"""

from __future__ import annotations
import os
import time
import re
from pathlib import Path
from typing import Optional
from openai import OpenAI
from core.console import FailureSafeConsole

CONSOLE = FailureSafeConsole()

# 提示词模板目录
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """从 prompts/ 目录加载提示词模板"""
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class AIClient:
    """AI API 客户端"""

    def __init__(self, config: dict):
        ai = config["ai"]
        configured_key = str(ai.get("api_key", "")).strip()
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key and configured_key.startswith("${") and configured_key.endswith("}"):
            api_key = os.getenv(configured_key[2:-1], "")
        if not api_key:
            api_key = os.getenv("SILICONFLOW_API_KEY", "")
        if not api_key and os.getenv("PHOSPHENE_ALLOW_CONFIG_SECRET") == "1":
            api_key = configured_key

        if not api_key:
            raise ValueError(
                "\n❌ 未设置 API 密钥！请通过环境变量设置:\n"
                "   set OPENAI_API_KEY=sk-xxxxx\n"
                "   或在 config.yaml 中填写 api_key"
            )
        if not api_key.isascii():
            raise ValueError(
                "API 密钥必须仅包含 ASCII 字符；请更新 GitHub Secret "
                "或服务器的 OPENAI_API_KEY 环境变量。"
            )

        self.client = OpenAI(api_key=str(api_key), base_url=ai["base_url"], timeout=60.0)
        self.model = ai["model"]
        self.temperature = ai.get("temperature", 0.8)
        self.max_tokens = ai.get("max_tokens", 4096)
        self.debug = config["runtime"].get("debug", False)
        self.concurrency = config["runtime"].get("concurrency", 2)
        self.retry_count = max(1, int(config["runtime"].get("retry_count", 2)))

    def call(self, system: str, user: str, temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        """调用 AI 模型"""
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )
        if self.debug:
            CONSOLE.print(f"[dim]  🧠 AI 调用: model={self.model}, "
                          f"temperature={kwargs['temperature']}[/]")

        retries = self.retry_count
        for attempt in range(retries):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                if self.debug:
                    CONSOLE.print(f"[dim]  📥 返回: {len(content)} 字符[/]")
                return content
            except Exception as e:
                if attempt < retries - 1:
                    wait = (attempt + 1) * 2
                    CONSOLE.print(f"  [yellow]⚠️  AI 调用失败 ({e}), {wait}s 后重试...[/]")
                    time.sleep(wait)
                else:
                    raise

    def generate_blog(self, system_prompt: str, user_prompt: str) -> str:
        """生成主博客文章"""
        return self.call(system_prompt, user_prompt)

    CATEGORY_STYLES = {
        "技术趋势": {"vibe": "科技感、紫蓝渐变、数字爆炸", "gradient": "a1"},
        "金融财经": {"vibe": "专业财经、金橙渐变、K线数据", "gradient": "a2"},
        "商业": {"vibe": "商业简洁、蓝青渐变、趋势结构", "gradient": "a3"},
        "娱乐文化": {"vibe": "活泼炫彩、粉紫渐变、流行感", "gradient": "a4"},
        "文学艺术": {"vibe": "文艺优雅、暖棕渐变、文字意境", "gradient": "a5"},
        "国际新闻": {"vibe": "新闻权威、深蓝渐变、数据格局", "gradient": "a6"},
        "中医中药": {"vibe": "传统自然、翠绿渐变、典雅智慧", "gradient": "a7"},
    }

    def _video_script_system(self, category_display: str) -> str:
        return """你是短视频脚本专家。你的输出将被自动解析和渲染，必须稳定、可解析、可配音。

## 输出原则

- 仅输出最终脚本，禁止前言、解释、道歉、检查清单、Markdown 代码围栏和舞台指示。
- 只可使用原文中明确出现的事实、数字、日期、机构、书名、人名与引用结论；不得编造、扩写或猜测。
- 选择一个最有价值的主线，不堆砌多个无关事实；语气简洁、有张力、适合中文短视频。

## 固定 8 场景映射（顺序、编号、视觉类型均不得改变）

S0=explode：钩子，提出反常识、结果或核心问题。
S1=number：原文有明确数字时展示该数字；没有数字时展示一条已验证的关键事实，禁止虚构数据。
S2=chain：解释背景或因果的第一步。
S3=pop：用一个原文支持的对象、概念或对比强化理解。
S4=text：提炼可传播的核心金句。
S5=tag：列出 2-3 个原文支持的要点、案例或影响。
S6=chain：给出递进后的判断或下一步。
S7=ending：以克制、有余味的结论收尾，不添加互动引导。

## 严格格式与时长

- 恰好输出 S0 到 S7 共 8 个场景，每场必须有场景标题行和 `文案：` 行。
- 每场 1-3 行文案，每行不超过 12 个中文字符；总文案控制在 80-120 字，约 30 秒。
- 所有场景使用同一个渐变色；场景之间用一个空行分隔。
- 输出前静默自检：场景数量、视觉类型、渐变色、字数、事实来源和格式均正确；不要输出自检过程。"""

    def _video_script_user(self, blog: str, category_display: str) -> str:
        style = self.CATEGORY_STYLES.get(category_display, self.CATEGORY_STYLES["技术趋势"])
        gradient = style["gradient"]
        vibe = style["vibe"]
        preview = blog[:3000]
        return f"""将以下关于「{category_display}」的文章改写为约 30 秒的 8 场景短视频脚本。

分类风格：{vibe}
渐变色：{gradient}

只围绕一条主线讲述：钩子 → 已验证事实 → 解释 → 强化理解 → 金句 → 要点展开 → 递进判断 → 收尾。

严格按以下格式输出。不得替换分隔符、字段名或视觉类型：

## S0 | 场景名称 | explode | {gradient}
文案：第一行
       第二行（可选）

继续使用同一格式输出 S1 到 S7。S0-S7 的视觉类型必须依次为：
explode、number、chain、pop、text、tag、chain、ending。

静默自检后仅输出最终脚本：恰好 8 场、渐变色均为 {gradient}、每行不超过 12 个中文字符、总文案 80-120 字，并且所有事实均可在原文中找到。

## 文章原文

{preview}"""
    _TWITTER_SYSTEM = """你是社交媒体运营专家，精通 Twitter/X 中文内容策略。
你擅长把长篇深度内容提炼为高互动率的推文串（thread）。
每条推文都是一个独立的钩子，推动读者一条接一条往下读。"""

    _TWITTER_USER = """将以下关于「{category}」的文章提炼为一条 Twitter/X 推文串（5-8条）：

## 格式规范
- 每条推文 ≤280 字符（中文约 130 字以内）
- 用序号标注：1/6 2/6 3/6 ... 6/6
- 第1条必须有强钩子（悬念/反常识/问题/惊人事实）
- 从第2条开始逐层递进：背景 → 核心观点 → 证据 → 结论
- 最后一条引导互动（提问/投票/转发语）

## 质量要求
- 保留原文最核心的 1-2 个观点，不要贪多
- 每条推文独立可读，不依赖上下文
- 语言口语化、有网感，但不过度网络用语
- 不加 #标签，直接用文字表达

## 输出格式
纯文本，每条推文之间用空行分隔。

文章内容：
{blog}"""

    _NEWSLETTER_SYSTEM = """你是邮件营销内容专家，擅长写高打开率、高点击率的 Newsletter。
你理解邮件通讯的特点：读者是主动订阅的，但注意力极其有限。
你的目标是在 3 秒内让读者觉得「这封邮件值得读完」。"""

    _NEWSLETTER_USER = """将以下关于「{category}」的文章改写为一封邮件 Newsletter：

## 结构要求
1. **邮件主题行**：15 字以内，让读者想点开（不要只是标题复制）
2. **预览文字**：1 句话，在收件箱中紧跟在主题行后
3. **开篇问候**：简短亲切，像写给朋友的信
4. **核心内容**：300 字以内摘要，只保留最重要的信息
5. **行动号召**：读者读完可以做什么（阅读全文/回复观点/分享）
6. **结尾祝福**：「祝好，Glenn」

## 质量要求
- 语气亲切但不啰嗦，像朋友分享见解而非营销推销
- 段落简短（每段 ≤3 行），用空行分隔
- 关键信息可加粗
- 去掉原文的所有 Markdown 标题层级，改用自然段落

文章内容：
{blog}"""

    _ENGLISH_SYSTEM = """你是专业中英翻译与本地化专家。
你擅长将中文内容转化为地道、自然的英文，而不是字对字翻译。
你熟悉技术写作规范，译文符合英美读者的阅读习惯。"""

    _ENGLISH_USER = """将以下中文文章译为英文：

## 翻译要求
- **不要字对字翻译**：理解中文原意后用自然的英文重新表达
- **标题要吸引英文读者**：符合英文标题习惯（首字母大写/主动语态/简短有力）
- **保持术语准确**：技术术语、人名、品牌名使用英文通用写法
- **文化适配**：中文特有的文化概念（如"内卷""躺平"）需加简短解释或找英文对等概念
- **段落结构**：按英文习惯拆分段落（topic sentence first）

## 质量要求
- 每段不超过 5 行
- 句子以简洁为美，避免过长的从句堆叠
- 用词精准但不生僻，让非母语读者也能顺畅阅读
- 修订后通读一遍，确保读起来不像翻译

原文：
{blog}"""

    def generate_format(self, fmt: str, blog: str, category_display: str = "") -> str:
        """单独生成某一种衍生格式"""
        blog = blog[:6000]
        if fmt == "twitter":
            system = _load_prompt("twitter_system.md") or self._TWITTER_SYSTEM
            user = (_load_prompt("twitter_user.md") or self._TWITTER_USER).format(category=category_display, blog=blog)
            temp = 0.7
        elif fmt == "newsletter":
            system = _load_prompt("newsletter_system.md") or self._NEWSLETTER_SYSTEM
            user = (_load_prompt("newsletter_user.md") or self._NEWSLETTER_USER).format(category=category_display, blog=blog)
            temp = 0.7
        elif fmt == "english":
            system = _load_prompt("english_system.md") or self._ENGLISH_SYSTEM
            user = (_load_prompt("english_user.md") or self._ENGLISH_USER).format(blog=blog[:4000])
            temp = 0.3
        elif fmt == "video_script":
            system = self._video_script_system(category_display)
            user = self._video_script_user(blog, category_display)
            temp = 0.7
        else:
            return f"// 不支持的格式: {fmt}"

        return self.call(system, user, temperature=temp)

    # ── 单次调用多格式（省 token 时使用） ──

    _MULTI_FORMAT_SYSTEM = """你是多平台内容运营专家，擅长把一篇长文转化为 5 种不同平台的格式。

你的输出必须使用 ===FORMAT:名称=== 作为分隔标记，每种格式独立输出。

质量要求：
- 每种格式独立完整，不依赖上下文
- 各格式的风格需适配对应平台的特点
- 内容准确性保持一致，不因改写而失真"""

    _MULTI_FORMAT_USER = """将以下关于「{category}」的文章转化为 5 种格式。

原文：
{blog}

请严格按照以下分隔格式输出每种格式：

===FORMAT:BLOG===
（原文即可，无需修改。确保 Markdown 格式完整。）

===FORMAT:TWITTER===
（推文串：5-8条，每条 ≤280 字符。第1条钩子，逐层递进，最后一条引导互动。
 用序号标注：1/6 2/6 ... 6/6。每条之间空行分隔。
 不加 #标签，语言口语化有网感。）

===FORMAT:NEWSLETTER===
（邮件通讯。结构：主题行 | 预览文字 | 问候 | 300字核心摘要 | 行动号召 | 祝福。
 语气亲切不啰嗦，段落简短，去掉 Markdown 标题层级改用自然段落。）

===FORMAT:VIDEO_SCRIPT===
（短视频脚本：8 场景，叙事顺序固定。
 S0 钩子 → S1 点名 → S2 解释 → S3 类比 → S4 金句 → S5 展开 → S6 升华 → S7 收尾。
 每场景一句文案，≤15 中文字符。
 不写舞台指示，只写最终屏幕文字。
 格式：## S0 | 场景名 | 视觉类型 | 渐变色
 视觉类型可选：explode / number / text / pop / tag / chain / ending）

===FORMAT:ENGLISH===
（英文版：自然地道英语，不要字对字翻译。
 标题简洁有力，符合英文写作规范。
 段落不超过 5 行，每段 topic sentence 先行。）"""

    def generate_all_formats(self, blog: str, category_display: str = "") -> dict:
        """一次性调用 AI 产出所有格式"""
        blog = blog[:4000]
        user = self._MULTI_FORMAT_USER.format(category=category_display, blog=blog)
        raw = self.call(self._MULTI_FORMAT_SYSTEM, user, temperature=0.7, max_tokens=6000)
        return self._parse_formats(raw)

    @staticmethod
    def _parse_formats(raw: str) -> dict:
        """解析 AI 单次调用的多格式输出"""
        results = {}
        pattern = re.compile(r'===FORMAT:(\w+)===')
        parts = pattern.split(raw)
        i = 1
        while i < len(parts) - 1:
            fmt = parts[i].strip().lower()
            content = parts[i + 1].strip()
            if fmt not in results:
                results[fmt] = content
            i += 2
        return results
