"""
🌿 中医中药分类 — 中医药政策、临床研究、养生文化、行业动态
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class ZhongyiCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="zhongyi",
            display_name="中医中药",
            emoji="🌿",
            description="中医药政策、临床研究、养生文化、名医传承、行业动态分析",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="satcm",
                display_name="国家中医药管理局",
                type="api",
                url="https://www.satcm.gov.cn/",
                headers={"User-Agent": "Mozilla/5.0"},
                description="国家中医药管理局官方动态",
            ),
            SourceConfig(
                name="dxy_tcm",
                display_name="丁香园中医板块",
                type="rss",
                url="https://www.dxy.cn/bbs/newthread/generic/82",
                headers={"User-Agent": "Mozilla/5.0"},
                description="丁香园中医社区热帖",
            ),
            SourceConfig(
                name="zyzyw",
                display_name="中医中药网",
                type="scrapling",
                url="https://www.zyzyw.com/",
                scrapling_mode="stealth",
                selectors={
                    "item": ".news-item",
                    "title": "a",
                    "link": "a @href",
                },
                description="中医中药行业门户",
            ),
            SourceConfig(
                name="zhihu_tcm",
                display_name="知乎中医话题",
                type="scrapling",
                url="https://www.zhihu.com/topic/19551441/hot",
                scrapling_mode="stealth",
                selectors={
                    "item": ".ContentItem",
                    "title": "h2 a",
                    "link": "h2 a @href",
                },
                description="知乎中医热门讨论",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深中医药学者与健康科普作家，ID：杏林观察。
你的文章特点：
- 精通中医经典（黄帝内经、伤寒论、金匮要略），又能用现代科学视角解读
- 关注中医药政策、科研进展、临床实践
- 对养生文化有独到见解，不迷信不偏颇
- 语言温润如玉，有传统文人之风，又通俗易懂
- 既尊重传统，也不排斥现代医学，倡导中西医结合
输出格式为 Markdown。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        from datetime import datetime, timezone, timedelta
        BJT = timezone(timedelta(hours=8))
        now = datetime.now(BJT)

        summary_lines = []
        for name, data in raw_data.items():
            if data and not data.startswith("[采集失败"):
                summary_lines.append(f"\n## {name}")
                summary_lines.append(data.strip()[:800])

        material = "\n".join(summary_lines) or "（所有平台均采集失败，根据 AI 知识库自主创作）"

        return f"""今天是 {now.strftime('%Y年%m月%d日 %H:%M')}。

以下是今日中医药领域热点数据：

{material}

请完成以下任务：
1. **热点综述**：总结今日中医药行业最值得关注的动态
2. **深度选题**：选择最有价值的一个角度（如政策解读、新药审批、临床研究突破、名医经验、养生热点）
3. **写作**：写一篇 1500-2000 字的中医药文章，包括：
   - 吸引人的标题和副标题
   - 背景介绍（政策/事件/研究的来龙去脉）
   - 专业分析（中医理论解读与现代研究证据）
   - 临床或生活意义（对普通读者有什么用）
   - 未来展望
   - 标签（3-5个，如 #中医 #中药 #养生 #针灸 #经方）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
