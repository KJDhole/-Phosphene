"""
分类注册表 — 自动发现 categories/ 下的所有分类
"""

from __future__ import annotations
import importlib
import pkgutil
from pathlib import Path
from typing import Optional

from core.base_category import BaseCategory, CategoryInfo
from rich.console import Console

CONSOLE = Console()

_registry: dict[str, BaseCategory] = {}


def discover_categories(categories_dir: Optional[Path] = None) -> dict[str, BaseCategory]:
    """扫描 categories/ 目录，自动发现并注册所有分类"""
    if _registry:
        return _registry

    if categories_dir is None:
        categories_dir = Path(__file__).parent.parent / "categories"

    if not categories_dir.exists():
        CONSOLE.print(f"[yellow]⚠️  分类目录不存在: {categories_dir}[/]")
        return {}

    # 遍历 categories/ 下的每个子目录
    for entry in sorted(categories_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("__"):
            continue

        module_name = f"categories.{entry.name}"
        try:
            module = importlib.import_module(module_name)
            # 查找模块中定义 Category 类的地方：寻找到 BaseCategory 的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, BaseCategory)
                        and attr is not BaseCategory):
                    instance = attr()
                    cat_info = instance.info
                    _registry[cat_info.name] = instance
                    CONSOLE.print(f"  [green]✅ 已注册分类: {cat_info.emoji} {cat_info.display_name}[/]")
                    break
        except Exception as e:
            CONSOLE.print(f"  [red]❌ 加载分类失败: {module_name} → {e}[/]")

    return _registry


def get_category(name: str) -> Optional[BaseCategory]:
    """按名称获取分类实例"""
    if not _registry:
        discover_categories()
    return _registry.get(name)


def list_categories() -> list[CategoryInfo]:
    """列出所有已注册分类的元信息"""
    if not _registry:
        discover_categories()
    return [cat.info for cat in _registry.values()]


def get_category_names() -> list[str]:
    """列出所有分类名称"""
    if not _registry:
        discover_categories()
    return list(_registry.keys())
