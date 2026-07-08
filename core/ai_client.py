"""
AI API 客户端 — 兼容 OpenAI / DeepSeek / 硅基流动 / 通义千问
"""

from __future__ import annotations
import os
import time
import re
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from rich.console import Console

CONSOLE = Console()


class AIClient:
    """AI API 客户端"""

    def __init__(self, config: dict):
        ai = config["ai"]
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv(ai.get("api_key", "")) or ai.get("api_key", "")
        # 替换 ${VAR} 占位符
        api_key_str = str(api_key) if api_key else ""
        if api_key_str.startswith("${"):
            env_var = api_key_str.strip("${}")
            api_key = os.getenv(env_var, "")

        if not api_key:
            raise ValueError(
                "\n❌ 未设置 API 密钥！请通过环境变量设置:\n"
                "   set OPENAI_API_KEY=sk-xxxxx\n"
                "   或在 config.yaml 中填写 api_key"
            )

        self.client = OpenAI(api_key=str(api_key), base_url=ai["base_url"])
        self.model = ai["model"]
        self.temperature = ai.get("temperature", 0.8)
        self.max_tokens = ai.get("max_tokens", 4096)
        self.debug = config["runtime"].get("debug", False)
        self.concurrency = config["runtime"].get("concurrency", 2)

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

        retries = 2
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
        style = self.CATEGORY_STYLES.get(category_display, self.CATEGORY_STYLES["技术趋势"])
        return f"""你是短视频内容策划专家，擅长制作高质量的 8 场景短视频。

当前分类：{category_display}
视频风格：{style['vibe']}
渐变色：{style['gradient']}

你的输出必须严格按照以下格式，每场景一行，用 | 分隔字段。"""

    def _video_script_user(self, blog: str, category_display: str) -> str:
        style = self.CATEGORY_STYLES.get(category_display, self.CATEGORY_STYLES["技术趋势"])
        gradient = style["gradient"]
        return f"""将以下关于「{category_display}」的文章改写为「8 场景短视频脚本」，格式如下：

## S0 | 场景名称 | 视觉类型 | {gradient}
文案：第一行
       第二行（可选）

## S1 | 场景名称 | 视觉类型 | {gradient}
文案：第一行
...

【叙事顺序】（固定，不可改变）：
S0 钩子 — S1 点名 — S2 解释 — S3 类比 — S4 金句 — S5 展开 — S6 升华 — S7 收尾

【视觉类型】（从以下选择）：
- explode：爆炸开场，放大+模糊消散
- number：数字/数据，左右分屏对撞
- text：纯文字上滑淡入
- pop：关键词弹性弹入
- tag：多标签逐个弹出
- chain：链条式递进
- ending：五彩渐变结尾

【规范】
1. 每行文案 ≤15 个中文字符
2. 不写"画面建议""口播"等舞台指示，只写最终屏幕显示的文字
3. 复杂场景可拆 2-3 行（每行单独显示）
4. 视觉类型根据场景内容选择最合适的

风格提示：{style['vibe']}

文章：
{blog[:3000]}"""

    def generate_format(self, fmt: str, blog: str, category_display: str = "") -> str:
        """单独生成某一种衍生格式"""
        prompts = {
            "twitter": (
                "你是社交媒体运营专家，擅长把长文提炼为吸引人的推文串。",
                f"""以下是一篇关于「{category_display}」的文章，请提炼为一条 Twitter/X 推文串（5-8条）：
每条≤280字，有钩子（hook），用序号 1/8 2/8 标注。
语言：中文。

文章内容：
{blog[:3000]}"""
            ),
            "newsletter": (
                "你是邮件营销专家，擅长写高打开率的 Newsletter。",
                f"""将以下关于「{category_display}」的文章改写为邮件 Newsletter：
- 吸引标题 + 预览文字
- 开篇问候
- 核心摘要（300字内）
- 行动号召
- 祝福结尾

文章：
{blog[:3000]}"""
            ),
            "video_script": (
                self._video_script_system(category_display),
                self._video_script_user(blog, category_display),
            ),
            "english": (
                "你是专业技术翻译，中译英地道、符合技术写作规范。",
                f"""将以下中文文章译为英文：
- 标题要吸引英文读者
- 保持内容准确性
- 符合英文写作风格

原文：
{blog[:4000]}"""
            ),
        }
        if fmt not in prompts:
            return f"// 不支持的格式: {fmt}"
        system, user = prompts[fmt]
        temp = 0.3 if fmt == "english" else 0.7
        return self.call(system, user, temperature=temp)

    def generate_all_formats(self, blog: str, category_display: str = "") -> dict:
        """一次性调用 AI 产出所有格式"""
        system = """你是多平台内容运营专家，擅长把一篇长文转化为不同平台的内容格式。
请严格按照要求输出每种格式，用 ===FORMAT:名称=== 作为分隔标记。"""
        user = f"""以下是一篇关于「{category_display}」的文章，请将其转化为 5 种不同格式的内容。

原文：
{blog[:4000]}

请严格按照以下分隔格式输出：

===FORMAT:BLOG===
（这里放原文即可，无需修改）

===FORMAT:TWITTER===
（推文串：5-8条推文，每条≤280字，带钩子引导点击，用序号 1/8 2/8 标注）

===FORMAT:NEWSLETTER===
（邮件通讯：吸引人的标题+预览文字+问候+300字摘要+行动号召+祝福）

===FORMAT:VIDEO_SCRIPT===
（短视频脚本：3-5分钟，分镜格式，开头5秒钩子，结尾引导关注）

===FORMAT:ENGLISH===
（英文版：地道英语，标题吸引英文读者，不要直译）"""
        raw = self.call(system, user, temp=0.7, max_tokens=6000)
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
