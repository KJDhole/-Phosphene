"""分类列表 API"""

from web.routes import router
from web.models import CategoryOut, SourceInfo
from core.registry import list_categories, get_category, discover_categories

discover_categories()


@router.get("/categories", response_model=list[CategoryOut])
def get_categories():
    cats = list_categories()
    result = []
    for cat_info in cats:
        # 通过分类名获取实际实例以访问 sources 属性
        cat = get_category(cat_info.name)
        sources = [
            SourceInfo(name=s.name, display_name=s.display_name, type=s.type)
            for s in cat.sources
        ]
        result.append(CategoryOut(
            name=cat_info.name,
            display_name=cat_info.display_name,
            emoji=cat_info.emoji,
            description=cat_info.description,
            sources=sources,
        ))
    return result
