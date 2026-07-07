"""
定时调度器 — 守护模式，按间隔轮询执行
"""

from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# 北京时间
BJT = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
CONSOLE = Console()


class Scheduler:
    """定时调度器（守护模式）"""

    def __init__(self, config: dict):
        self.interval = config.get("schedule", {}).get("interval_hours", 6)
        self.categories = config.get("categories", {}).get("active", ["tech"])
        self._running = False

    def run_forever(self):
        """进入守护循环"""
        import schedule as sched

        self._running = True
        hours = self.interval

        # 注册任务 — 轮询所有启用的分类
        from main import run_once_for_category

        def _run_next():
            """轮询下一个分类"""
            # 简单实现：根据当前小时取模选分类
            idx = (datetime.now(BJT).hour // hours) % len(self.categories)
            cat = self.categories[idx]
            CONSOLE.print(f"[dim]📋 调度选择分类: {cat}[/]")
            run_once_for_category(cat)

        sched.every(hours).hours.do(_run_next)

        CONSOLE.print(Panel(
            f"[bold green]🔄 守护模式已启动[/]\n"
            f"   每 [bold]{hours}[/] 小时执行一次\n"
            f"   分类轮询: {', '.join(self.categories)}\n"
            f"   下次执行: {datetime.now(BJT) + timedelta(hours=hours):%Y-%m-%d %H:%M}\n"
            f"   按 Ctrl+C 停止",
            title="熠觉 · Phosphene"
        ))

        # 启动后立即执行一次
        _run_next()

        while self._running:
            try:
                sched.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                CONSOLE.print("\n[yellow]⏹  调度已停止[/]")
                self._running = False
                break
