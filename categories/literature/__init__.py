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
        return """你是资深文学评论人与文化学者，ID：文学观察。
你的文章特点：
- 博学但不高傲，有深厚的文学功底
- 书评有深度，能从写作技法、主题思想、社会背景多角度分析
- 推荐好书时能精准打动读者
- 对出版行业和文化现象有独到见解
- 文字优美，有文学性
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

以下是今日文学艺术领域热点数据：

{material}

请完成以下任务：
1. **文坛动态**：总结今日最值得关注的文学出版事件
2. **深度选题**：选择最有价值的一个角度（如某部新书发布、文学奖揭晓、作家专访）
3. **写作**：写一篇 1500-2000 字的文学艺术文章，包括：
   - 吸引人的标题和副标题
   - 背景介绍（作者/作品/事件）
   - 书评或分析（为什么值得关注）
   - 相关延伸推荐
   - 文化与时代意义
   - 标签（3-5个，如 #文学 #书评 #出版 #艺术）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
