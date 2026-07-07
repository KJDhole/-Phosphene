"""
🎬 娱乐文化分类 — 影视、音乐、综艺、明星、游戏
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class EntertainmentCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="entertainment",
            display_name="娱乐文化",
            emoji="🎬",
            description="影视、音乐、综艺、明星八卦、游戏等娱乐热点",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="douban_movie",
                display_name="豆瓣电影热门",
                type="api",
                url="https://movie.douban.com/j/search_subjects?type=movie&tag=热门&page_limit=10",
                headers={"User-Agent": "Mozilla/5.0"},
                description="豆瓣电影热门榜单",
            ),
            SourceConfig(
                name="163_music",
                display_name="网易云音乐热搜",
                type="api",
                url="https://music.163.com/api/search/hot",
                headers={"User-Agent": "Mozilla/5.0"},
                description="网易云音乐热搜榜",
            ),
            SourceConfig(
                name="weibo_hot",
                display_name="微博热搜",
                type="scrapling",
                url="https://weibo.com/ajax/side/hotSearch",
                scrapling_mode="stealth",
                selectors={},
                description="微博热搜榜",
            ),
            SourceConfig(
                name="douyin_hot",
                display_name="抖音热点",
                type="scrapling",
                url="https://www.douyin.com/hot",
                scrapling_mode="stealth",
                selectors={
                    "item": ".hot-list-item",
                    "title": ".hot-title",
                },
                description="抖音热点榜",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深娱乐文化评论人，ID：文化观察。
你的文章特点：
- 敏锐捕捉文化潮流和娱乐热点
- 深入浅出，既有深度又有趣味性
- 观点独到，不人云亦云
- 对影视、音乐、综艺等有专业见解
- 语言生动活泼，适合年轻读者
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

以下是今日娱乐文化领域热点数据：

{material}

请完成以下任务：
1. **热点盘点**：总结今日娱乐文化圈最热门的事件
2. **深度选题**：选择最有话题性的一个角度（如某部热映电影解析、明星事件、音乐潮流）
3. **写作**：写一篇 1500-2000 字的娱乐文化文章，包括：
   - 吸引人的标题和副标题
   - 热点事件描述（客观事实）
   - 深度分析（为什么火？反映了什么文化趋势？）
   - 同类对比或历史参照
   - 大众反响与争议点
   - 标签（3-5个，如 #电影 #音乐 #综艺 #流行文化）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
