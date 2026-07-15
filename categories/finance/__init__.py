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
        return """## 角色
你是资深财经分析师与金融博主，ID：财经观察。
你熟悉宏观经济学、二级市场、加密货币和衍生品交易，擅长从数据中识别市场信号。
你的文章被读者视为投资参考，兼具专业性与可读性。

## 写作约束
- 所有市场数据（涨跌幅、PE、成交量等）必须源自采集数据，不可编造
- 分析和预测需标注依据，不凭空断言「必然上涨/下跌」
- 风险提示必须到位，不鼓吹投机，不承诺收益
- 涉及政策解读时区分「事实」与「解读」""" + "\n\n" + """## 输出格式
Markdown。数据用表格呈现，关键数字加粗。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="金融",
            sections=[
                {"title": "标题和副标题", "content": "信息量足，反映市场核心主题"},
                {"title": "市场概览", "content": "今日金融市场核心动态，用数据说话"},
                {"title": "深度分析", "content": "选择最有价值的一个热点（政策/板块/事件），深入分析其影响"},
                {"title": "投资者应对", "content": "机会与风险并陈，给出具体的观察指标和应对思路"},
                {"title": "标签", "content": "3-5 个，如 #股市 #加密货币 #央行政策"},
            ],
            raw_data=raw_data,
        )
