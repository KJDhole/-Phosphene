"""
📚 文学艺术分类 — 书籍、出版、文学奖、书评
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class LiteratureCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="literature",
            display_name="文学艺术",
            emoji="📚",
            description="文学出版、书评、文学奖、艺术展览等文化动态",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="goodreads",
                display_name="Goodreads 热门",
                type="rss",
                url="https://www.goodreads.com/choiceawards/best-books-2025",
                headers={"User-Agent": "Mozilla/5.0"},
                description="Goodreads 热门书籍",
            ),
            SourceConfig(
                name="douban_book",
                display_name="豆瓣读书热门",
                type="api",
                url="https://book.douban.com/j/search_subjects?type=book&tag=热门&page_limit=10",
                headers={"User-Agent": "Mozilla/5.0"},
                description="豆瓣读书热门榜单",
            ),
            SourceConfig(
                name="nytimes_books",
                display_name="纽约时报书评",
                type="rss",
                url="https://www.nytimes.com/svc/collections/v1/publish/"
                    "www.nytimes.com/section/books/review/rss.xml",
                description="纽约时报书评 RSS",
            ),
            SourceConfig(
                name="artforum",
                display_name="Artforum 艺术论坛",
                type="rss",
                url="https://www.artforum.com/feed",
                description="Artforum 艺术新闻",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """## 角色
你是资深文学评论人与文化学者，ID：文学观察。
你有深厚的文学功底，能从写作技法、主题思想、社会背景多角度分析作品。
你的书评精准独到，文笔有文学性，让读者产生阅读的欲望。

## 写作约束
- 引用作品内容（情节、人物、原文）需注明作品名称
- 评论他人作品时秉持善意，批评有依据
- 涉及文学奖/出版业数据时以采集数据为准
- 推荐语不夸张，让读者对作品有合理预期""" + "\n\n" + """## 输出格式
Markdown。文字优美有文学性，结构清晰。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="文学艺术",
            sections=[
                {"title": "标题和副标题", "content": "文学性 + 信息量"},
                {"title": "文坛动态", "content": "今日最值得关注的文学出版事件"},
                {"title": "深度书评/分析", "content": "选择一部作品/一个事件深入分析"},
                {"title": "延伸推荐", "content": "相关作品或作者推荐"},
                {"title": "文化意义", "content": "这部作品/事件反映的时代与文化信号"},
                {"title": "标签", "content": "3-5 个，如 #文学 #书评 #出版 #艺术"},
            ],
            raw_data=raw_data,
        )
