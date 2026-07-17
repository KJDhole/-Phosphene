"""Atomic output storage and deterministic index generation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rich.table import Table

from core.console import FailureSafeConsole

BJT = timezone(timedelta(hours=8))
CONSOLE = FailureSafeConsole()


class OutputManager:
    CATEGORY_META = {
        "tech": ("🔧", "技术趋势"),
        "finance": ("💰", "金融财经"),
        "business": ("🏢", "商业"),
        "entertainment": ("🎬", "娱乐文化"),
        "literature": ("📚", "文学艺术"),
        "world": ("🌐", "国际新闻"),
        "zhongyi": ("🌿", "中医中药"),
    }

    FORMAT_META = {
        "blog": ("📝", "博客"),
        "twitter": ("🐦", "推文串"),
        "newsletter": ("📧", "通讯"),
        "video_script": ("🎬", "脚本"),
        "english": ("🌍", "English"),
        "video": ("🎥", "视频"),
    }

    def __init__(self, config: dict, category_name: str = "unknown"):
        root = Path(__file__).parent.parent
        self.base_dir = (root / config["output"]["output_dir"]).resolve()
        self.posts_dir = self.base_dir / "posts"
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.formats_config = config["output"]["formats"]
        self.category = category_name
        self.cat_dir = self.posts_dir / self.category
        self.cat_dir.mkdir(parents=True, exist_ok=True)
        self.slug = self._new_slug()

    def _new_slug(self) -> str:
        base = datetime.now(BJT).strftime("%Y%m%d_%H%M%S")
        slug = base
        counter = 1
        while (self.cat_dir / slug).exists():
            counter += 1
            slug = f"{base}_{counter}"
        return slug

    def _rel_path(self, filename: str) -> str:
        return f"{self.category}/{self.slug}/{filename}"

    def save_all(
        self,
        blog: str,
        extra_formats: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        slug_dir = self.cat_dir / self.slug
        slug_dir.mkdir(parents=True, exist_ok=False)
        saved: dict[str, Path] = {}

        if self.formats_config.get("blog", True):
            saved["blog"] = self._write_text(slug_dir / "blog.md", blog)

        for fmt, content in extra_formats.items():
            if self.formats_config.get(fmt, True) and content.strip():
                saved[fmt] = self._write_text(slug_dir / f"{fmt}.md", content)

        metadata_payload = {
            "slug": self.slug,
            "category": self.category,
            "created_at": datetime.now(BJT).isoformat(),
            "formats": sorted(saved),
            **(metadata or {}),
        }
        self._write_text(
            slug_dir / "metadata.json",
            json.dumps(metadata_payload, ensure_ascii=False, indent=2),
        )

        CONSOLE.print(f"\n[bold green]💾 已保存至 {slug_dir}/[/]")
        table = Table(box=None, padding=(0, 2))
        table.add_column("格式", style="cyan")
        table.add_column("文件")
        table.add_column("大小")
        for fmt, path in saved.items():
            emoji, label = self.FORMAT_META.get(fmt, ("📄", fmt))
            table.add_row(
                f"{emoji} {label}",
                f"posts/{self._rel_path(path.name)}",
                f"{len(path.read_text(encoding='utf-8'))} 字",
            )
        CONSOLE.print(table)
        return slug_dir

    @staticmethod
    def _write_text(path: Path, content: str) -> Path:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
        return path

    def update_index(self, _blog: str = "") -> None:
        """Rebuild the complete index from files, preserving all history."""
        lines = [
            "# ✦ 熠觉 · Phosphene",
            "",
            "信息如流，落笔为舟",
            "",
            "---",
            "",
            "## 📂 按分类浏览",
            "",
        ]

        for category_dir in sorted(self.posts_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            emoji, display = self.CATEGORY_META.get(
                category_dir.name,
                ("📄", category_dir.name),
            )
            articles = []
            for slug_dir in sorted(category_dir.iterdir(), reverse=True):
                blog_path = slug_dir / "blog.md"
                if not slug_dir.is_dir() or not blog_path.exists():
                    continue
                blog = blog_path.read_text(encoding="utf-8")
                title = self._extract_title(blog)
                articles.append((slug_dir, title))
            if not articles:
                continue

            lines.extend([f"### {emoji} {display}", ""])
            for slug_dir, title in articles:
                rel = f"posts/{category_dir.name}/{slug_dir.name}"
                lines.append(f"- [**{title}**]({rel}/blog.md) ({self._display_date(slug_dir.name)})")
                format_links = []
                for fmt, (fmt_emoji, fmt_label) in self.FORMAT_META.items():
                    suffix = ".mp4" if fmt == "video" else ".md"
                    filename = f"{fmt}{suffix}"
                    if (slug_dir / filename).exists() and fmt != "blog":
                        format_links.append(f"{fmt_emoji} [{fmt_label}]({rel}/{filename})")
                if format_links:
                    lines.append("  - " + " · ".join(format_links))
            lines.append("")

        timestamp = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
        lines.extend(
            [
                "---",
                "",
                f"*由 熠觉 · Phosphene 生成 · 最后更新: {timestamp}*",
                "",
            ]
        )
        self._write_text(self.base_dir / "index.md", "\n".join(lines))
        CONSOLE.print("  [green]✅ 首页索引已完整重建[/]")

    @staticmethod
    def _extract_title(blog: str) -> str:
        match = re.search(r"(?m)^#\s+(.+)$", blog)
        return match.group(1).strip() if match else "未命名文章"

    @staticmethod
    def _display_date(slug: str) -> str:
        value = slug.split("_", 2)
        for fmt in ("%Y%m%d_%H%M%S", "%Y%m%d_%H%M"):
            try:
                candidate = "_".join(value[:2])
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        return slug
