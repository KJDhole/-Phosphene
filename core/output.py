"""
输出管理器 — 保存文章文件、更新首页索引
"""

from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from rich.console import Console
from rich.table import Table

# 北京时间
BJT = timezone(timedelta(hours=8))
CONSOLE = Console()


class OutputManager:
    """管理输出文件的保存和索引更新（按分类子目录存储）"""

    CATEGORY_META = {
        "tech":          ("🔧", "技术趋势"),
        "finance":       ("💰", "金融财经"),
        "business":      ("🏢", "商业"),
        "entertainment": ("🎬", "娱乐文化"),
        "literature":    ("📚", "文学艺术"),
        "world":         ("🌐", "国际新闻"),
        "zhongyi":       ("🌿", "中医中药"),
    }

    def __init__(self, config: dict, category_name: str = "unknown"):
        out_dir = config["output"]["output_dir"]
        self.base_dir = Path(__file__).parent.parent / out_dir
        self.posts_dir = self.base_dir / "posts"
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.formats_config = config["output"]["formats"]
        self.slug = datetime.now(BJT).strftime("%Y%m%d_%H%M")
        self.category = category_name
        # 按分类子目录：posts/{category}/{slug}/
        self.cat_dir = self.posts_dir / self.category
        self.cat_dir.mkdir(parents=True, exist_ok=True)

    def _rel_path(self, filename: str) -> str:
        """返回相对 posts_dir 的路径"""
        return f"{self.category}/{self.slug}/{filename}"

    def save_all(self, blog: str, extra_formats: dict) -> Path:
        """保存所有格式到 posts/{category}/{slug}/"""
        slug_dir = self.cat_dir / self.slug
        slug_dir.mkdir(parents=True, exist_ok=True)

        saved = {}
        fmt_labels = {
            "blog": "📝 博客", "twitter": "🐦 推文",
            "newsletter": "📧 通讯", "video_script": "🎬 脚本",
            "english": "🌍 英文",
        }

        # 主博客
        if self.formats_config.get("blog", True):
            path = slug_dir / "blog.md"
            path.write_text(blog, encoding="utf-8")
            saved["blog"] = path

        # 其他格式
        for fmt, content in extra_formats.items():
            if not self.formats_config.get(fmt, True):
                continue
            path = slug_dir / f"{fmt}.md"
            path.write_text(content, encoding="utf-8")
            saved[fmt] = path

        # 打印保存结果
        CONSOLE.print(f"\n[bold green]💾 已保存至 {slug_dir}/[/]")
        table = Table(box=None, padding=(0, 2))
        table.add_column("格式", style="cyan")
        table.add_column("文件")
        table.add_column("大小")
        for fmt, path in saved.items():
            size = len(path.read_text(encoding="utf-8"))
            label = fmt_labels.get(fmt, fmt)
            table.add_row(label, f"posts/{self._rel_path(path.name)}", f"{size} 字")
        CONSOLE.print(table)

        return slug_dir

    def update_index(self, blog: str) -> None:
        """更新 docs/index.md —— 按分类分区展示文章"""
        index_path = self.base_dir / "index.md"

        # 提取标题
        title = "未命名文章"
        for line in blog.split("\n"):
            m = re.match(r'^#\s+(.+)$', line.strip())
            if m and not line.startswith("##"):
                title = m.group(1).strip()
                break

        date_str = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
        emoji, display = self.CATEGORY_META.get(self.category, ("📄", self.category))

        # 新文章的 Markdown 条目
        blog_link = f"posts/{self._rel_path('blog.md')}"
        entry_lines = [
            f"- [**{title}**]({blog_link}) ({date_str})",
            f"  - 🐦 [推文串](posts/{self._rel_path('twitter.md')})"
            f" · 📧 [通讯](posts/{self._rel_path('newsletter.md')})"
            f" · 🎬 [脚本](posts/{self._rel_path('video_script.md')})"
            f" · 🌍 [English](posts/{self._rel_path('english.md')})",
        ]

        # 构建首页内容
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
        else:
            content = (
                "# 🤖 熠觉 · Phosphene\n\n"
                "信息如流，落笔为舟\n\n"
                "---\n\n"
                "## 📂 按分类浏览\n\n"
                "<!-- CATEGORY_SECTION -->\n"
                "<!-- CATEGORY_SECTION_END -->\n\n"
                "---\n\n"
                f"*👤 Glenn · 由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com · 最后更新: {date_str}*\n"
            )

        # 在 CATEGORY_SECTION 中按分类插入/追加
        marker_start = "<!-- CATEGORY_SECTION -->"
        marker_end = "<!-- CATEGORY_SECTION_END -->"
        section_start = content.find(marker_start)
        section_end = content.find(marker_end)

        if section_start >= 0 and section_end > section_start:
            # 在分类区间内查找是否已有该分类的区块
            between = content[section_start + len(marker_start):section_end]
            cat_header = f"### {emoji} {display}"
            cat_block_start = between.find(cat_header)

            new_block = f"\n### {emoji} {display}\n" + "\n".join(entry_lines) + "\n"

            if cat_block_start >= 0:
                # 已有该分类区块，替换
                cat_block_end = between.find("\n### ", cat_block_start + 1)
                if cat_block_end < 0:
                    cat_block_end = len(between)
                old_block = between[cat_block_start:cat_block_end]
                new_between = between.replace(old_block, new_block.strip())
            else:
                # 新分类，追加到最后
                new_between = between + new_block

            content = (content[:section_start + len(marker_start)]
                       + new_between
                       + content[section_end:])
        else:
            # 没有标记，追加
            content = content.replace(
                "---\n\n*🤖",
                f"## 📂 按分类浏览\n\n### {emoji} {display}\n"
                + "\n".join(entry_lines) + "\n\n---\n\n*🤖"
            )

        # 更新页脚时间戳
        from datetime import timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=8)))
        ts = now.strftime("%Y-%m-%d %H:%M")
        content = content.rstrip()
        # 替换已有时间戳
        import re as _re
        content = _re.sub(r'(最后更新: )\d{4}-\d{2}-\d{2} \d{2}:\d{2}', rf'\1{ts}', content)

        index_path.write_text(content, encoding="utf-8")
        CONSOLE.print(f"  [green]✅ 首页已更新: {index_path}[/]")
