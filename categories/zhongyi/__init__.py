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
                type="scrapling",
                url="https://www.satcm.gov.cn/",
                headers={"User-Agent": "Mozilla/5.0"},
                selectors={
                    "item": ".list li",
                    "title": "a",
                    "link": "a @href",
                },
                description="国家中医药管理局官方动态",
            ),
            SourceConfig(
                name="dxy_tcm",
                display_name="丁香园中医板块",
                type="scrapling",
                url="https://www.dxy.cn/bbs/newthread/generic/82",
                headers={"User-Agent": "Mozilla/5.0"},
                selectors={
                    "item": ".thread-list-item",
                    "title": "a",
                    "link": "a @href",
                },
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
        return """## 角色
你是资深中医药学者与健康科普作家，ID：杏林观察。
你精通中医经典（黄帝内经、伤寒论、金匮要略），又能用现代科学视角解读。
你关注中医药政策、科研进展、临床实践，对养生文化有独到见解。

## 写作约束
- 引用的中医典籍内容必须准确，注明出处
- 涉及疗效的表述必须基于研究数据或临床证据，不夸大不迷信
- 不鼓吹「替代西医」，倡导中西医结合视角
- 养生建议需注明适用人群和禁忌，不给出笼统的「每个人都该做」的建议""" + "\n\n" + """## 输出格式
Markdown。语言温润，有传统文人之风又通俗易懂。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="中医药",
            sections=[
                {"title": "标题和副标题", "content": "兼顾专业性和传播性"},
                {"title": "热点综述", "content": "今日中医药行业最值得关注的动态"},
                {"title": "深度选题", "content": "选择一个角度深入（政策解读/临床研究/养生热点/名医经验）"},
                {"title": "专业分析", "content": "中医理论解读 + 现代研究证据，二者不可偏废"},
                {"title": "现实意义", "content": "对普通读者的生活或健康有什么实际帮助"},
                {"title": "标签", "content": "3-5 个，如 #中医 #中药 #养生 #经方"},
            ],
            raw_data=raw_data,
        )
