"""
发布器 — 支持本地保存和 GitHub Pages 自动发布
"""

from __future__ import annotations
import os
import re
import subprocess as sp
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from rich.console import Console

# 北京时间
BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
CONSOLE = Console()


class Publisher:
    """发布文章到 GitHub Pages"""

    def __init__(self, config: dict):
        pub = config.get("publish", {})
        self.mode = pub.get("mode", "local")
        self.gh = pub.get("github_pages", {})
        self.output_dir = ROOT / config["output"]["output_dir"]

    def publish(self, blog: str, slug: str) -> dict:
        """执行发布"""
        if self.mode == "local":
            CONSOLE.print(f"\n[green]📂 文章已保存至: {self.output_dir}/posts/{slug}/[/]")
            CONSOLE.print(f"   [dim]部署到 GitHub Pages 请运行: python main.py --deploy[/]")
            return {"status": "local", "published": 1, "errors": 0}

        if self.mode == "github-pages":
            return self._publish_gh_pages(blog, slug)

        CONSOLE.print(f"  [yellow]⚠️  未知发布模式: {self.mode}[/]")
        return {"status": "unknown", "published": 0, "errors": 1}

    def _publish_gh_pages(self, blog: str, slug: str) -> dict:
        """推送到 GitHub Pages 仓库"""
        if not self.gh.get("enabled"):
            CONSOLE.print("  [yellow]⏭️  GitHub Pages 发布未启用[/]")
            return {"status": "skipped", "published": 0, "errors": 0}

        repo_path = Path(self.gh.get("local_repo_path", ""))
        if not repo_path.exists():
            CONSOLE.print(f"  [red]❌ 本地仓库不存在: {repo_path}[/]")
            return {"status": "error", "published": 0, "errors": 1}

        target = repo_path / "_posts"
        target.mkdir(parents=True, exist_ok=True)

        src = self.output_dir / "posts" / slug / "blog.md"
        if not src.exists():
            CONSOLE.print(f"  [red]❌ 博客文件不存在: {src}[/]")
            return {"status": "error", "published": 0, "errors": 1}

        # Jekyll 格式文件名
        title = "untitled"
        for line in blog.split("\n"):
            m = re.match(r'^#\s+(.+)$', line.strip())
            if m and not line.startswith("##"):
                title = m.group(1).strip()[:30]
                break
        safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '-', title).strip('-')
        today = datetime.now(BJT).strftime("%Y-%m-%d")
        jekyll_name = f"{today}-{safe_title}.md"
        dst = target / jekyll_name

        shutil.copy2(str(src), str(dst))
        CONSOLE.print(f"  [green]📋 已复制: {jekyll_name}[/]")

        try:
            cwd = os.getcwd()
            os.chdir(str(repo_path))
            sp.run(["git", "add", "_posts/"], capture_output=True, check=True)
            result = sp.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
            if result.returncode != 0:
                commit_msg = self.gh.get("commit_message", "🤖 AI 自动发布: {title} [{date}]")
                msg = commit_msg.format(title=title[:30], date=today)
                sp.run(["git", "commit", "-m", msg], capture_output=True, check=True)
                CONSOLE.print(f"  [green]📦 已提交: {msg}[/]")
                sp.run(["git", "push", "origin", self.gh.get("branch", "main")],
                       capture_output=True, check=True)
                CONSOLE.print(f"  [green]🚀 已推送至 GitHub![/]")
            else:
                CONSOLE.print("  [yellow]⏭️  没有新变更[/]")
            os.chdir(cwd)
        except sp.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            CONSOLE.print(f"  [red]❌ Git 操作失败: {stderr[:200]}[/]")
            return {"status": "error", "published": 0, "errors": 1}
        except Exception as e:
            CONSOLE.print(f"  [red]❌ 发布异常: {e}[/]")
            return {"status": "error", "published": 0, "errors": 1}

        return {"status": "success", "published": 1, "errors": 0}
