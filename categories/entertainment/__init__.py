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
        return """## 角色
你是资深娱乐文化评论人，ID：文化观察。
你敏锐捕捉文化潮流和娱乐热点，对影视、音乐、综艺、流行文化有专业见解。
你的文章既有深度又有趣味性，观点独到不人云亦云。

## 写作约束
- 涉及明星/事件的事实部分（时间、数据、言论）必须源自采集数据
- 主观评论与客观事实区分清楚
- 评论有依据，不为了博眼球而过度解读
- 尊重创作和艺人，评论作品时对事不对人""" + "\n\n" + """## 输出格式
Markdown。语言生动活泼，适合年轻读者。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="娱乐文化",
            sections=[
                {"title": "标题和副标题", "content": "吸引眼球但不标题党"},
                {"title": "热点盘点", "content": "今日最热门的事件速览"},
                {"title": "深度选题", "content": "选最有话题性的一个角度（电影解析/明星事件/音乐潮流）"},
                {"title": "为什么火", "content": "反映了什么文化趋势和大众心理"},
                {"title": "同类对比", "content": "历史参照或同类作品对比分析"},
                {"title": "标签", "content": "3-5 个，如 #电影 #音乐 #综艺"},
            ],
            raw_data=raw_data,
        )
