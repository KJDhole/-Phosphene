"""Explicit publishing adapter for local output and GitHub Pages."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.console import FailureSafeConsole

BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
CONSOLE = FailureSafeConsole()


class Publisher:
    def __init__(self, config: dict):
        publish_config = config.get("publish", {})
        self.mode = publish_config.get("mode", "local")
        self.gh = publish_config.get("github_pages", {})
        self.output_dir = (ROOT / config["output"]["output_dir"]).resolve()

    def publish(self, blog: str, category: str, slug: str) -> dict:
        """Publish one exact category/slug pair."""
        article_dir = self.output_dir / "posts" / category / slug
        if self.mode == "local":
            CONSOLE.print(f"\n[green]📂 草稿已保存至: {article_dir}[/]")
            return {"status": "local", "published": 0, "errors": 0}
        if self.mode == "github-pages":
            return self._publish_gh_pages(blog, category, slug)
        return {"status": "error", "published": 0, "errors": 1}

    def _publish_gh_pages(self, blog: str, category: str, slug: str) -> dict:
        if not self.gh.get("enabled"):
            return {"status": "skipped", "published": 0, "errors": 0}

        repo_value = str(self.gh.get("local_repo_path", "")).strip()
        repo_path = Path(repo_value).expanduser().resolve() if repo_value else None
        if not repo_path or not (repo_path / ".git").exists():
            CONSOLE.print("  [red]❌ GitHub Pages 本地仓库无效[/]")
            return {"status": "error", "published": 0, "errors": 1}

        src = self.output_dir / "posts" / category / slug / "blog.md"
        if not src.exists():
            CONSOLE.print(f"  [red]❌ 博客文件不存在: {src}[/]")
            return {"status": "error", "published": 0, "errors": 1}

        target = repo_path / "_posts"
        target.mkdir(parents=True, exist_ok=True)
        title_match = re.search(r"(?m)^#\s+(.+)$", blog)
        title = title_match.group(1).strip() if title_match else "untitled"
        safe_title = re.sub(r"[^\w\u4e00-\u9fff-]", "-", title[:50]).strip("-")
        today = datetime.now(BJT).strftime("%Y-%m-%d")
        destination = target / f"{today}-{category}-{safe_title}.md"
        shutil.copy2(src, destination)

        try:
            self._git(repo_path, "add", str(destination.relative_to(repo_path)))
            diff = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if diff.returncode == 0:
                return {"status": "unchanged", "published": 0, "errors": 0}

            template = self.gh.get("commit_message", "AI 内容发布: {title} [{date}]")
            message = template.format(title=title[:30], date=today)
            self._git(repo_path, "commit", "-m", message)
            self._git(repo_path, "push", "origin", self.gh.get("branch", "main"), timeout=120)
            return {"status": "success", "published": 1, "errors": 0}
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            CONSOLE.print(f"  [red]❌ Git 发布失败: {detail[:300]}[/]")
            return {"status": "error", "published": 0, "errors": 1}

    @staticmethod
    def _git(repo_path: Path, *args: str, timeout: int = 30) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
