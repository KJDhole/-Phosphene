"""
💰 金融财经分类 — 股票、加密货币、宏观经济
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class FinanceCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="finance",
            display_name="金融财经",
            emoji="💰",
            description="股市、加密货币、宏观经济、央行政策等金融热点分析",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="yahoo_finance",
                display_name="Yahoo Finance",
                type="rss",
                url="https://finance.yahoo.com/news/rssindex",
                description="雅虎财经 RSS",
            ),
            SourceConfig(
                name="sina_finance",
                display_name="新浪财经",
                type="rss",
                url="https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=10",
                description="新浪财经滚动新闻",
            ),
            SourceConfig(
                name="cls",
                display_name="财联社",
                type="rss",
                url="https://www.cls.cn/telegraph",
                headers={"User-Agent": "Mozilla/5.0"},
                description="财联社电报",
            ),
            SourceConfig(
                name="xueqiu",
                display_name="雪球热帖",
                type="scrapling",
                url="https://xueqiu.com/hq",
                scrapling_mode="stealth",
                selectors={
                    "item": ".stock-item",
                    "title": "h3 a",
                    "link": "h3 a @href",
                },
                description="雪球投资社区热帖",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深财经分析师与金融博主，ID：财经观察。
你的文章特点：
- 深度分析金融市场动态，有独到见解
- 数据驱动，引用具体指标（涨跌幅、PE、成交量等）
- 结构清晰，从宏观到微观层层递进
- 专业但不晦涩，普通投资者也能看懂
- 对风险有充分提醒，不鼓吹投机
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

以下是今日金融市场热点数据：

{material}

请完成以下任务：
1. **市场概览**：总结今日金融市场核心动态
2. **主题分析**：选择最有价值的一个热点（如某政策出台、某板块爆发），深入分析
3. **写作**：写一篇 1500-2000 字的金融分析文章，包括：
   - 吸引人的标题和副标题
   - 事件背景与核心数据
   - 影响分析（对哪些行业/资产影响最大）
   - 投资者应对建议（风险与机会）
   - 标签（3-5个，如 #股市 #加密货币 #央行政策）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
