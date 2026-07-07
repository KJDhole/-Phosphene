#!/usr/bin/env python3
"""
熠觉 · Phosphene v2.0
================
多分类热点采集 → AI 分析 → 多格式输出 → 自动发布

一条命令跑一个分类：
    python main.py --category finance

可用分类：
    python main.py --list-categories

环境变量：
    OPENAI_API_KEY=sk-xxx
"""

import os
import sys
import yaml
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 项目根目录
ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
CONSOLE = Console()
BJT = timezone(timedelta(hours=8))


def load_config() -> dict:
    """加载并校验配置"""
    if not CONFIG_PATH.exists():
        CONSOLE.print(f"[red]❌ 配置文件不存在: {CONFIG_PATH}[/]")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if "ai" not in config or not config["ai"]:
        CONSOLE.print("[red]❌ 配置缺少必填项: ai[/]")
        sys.exit(1)
    return config


def run_once_for_category(category_name: str, debug: bool = False) -> bool:
    """执行指定分类的一次完整流水线"""
    from core.ai_client import AIClient
    from core.output import OutputManager
    from core.publisher import Publisher
    from core.registry import get_category

    start = time.time()
    config = load_config()
    if debug:
        config["runtime"]["debug"] = True

    # 获取分类
    cat = get_category(category_name)
    if not cat:
        CONSOLE.print(f"[red]❌ 未知分类: {category_name}[/]")
        CONSOLE.print(f"   可用分类: {', '.join(list_categories())}")
        return False

    cat_info = cat.info
    ai_client = AIClient(config)
    output_mgr = OutputManager(config, category_name=category_name)
    publisher = Publisher(config)

    CONSOLE.print(Panel(
        f"[bold]{cat_info.emoji} {cat_info.display_name}[/]\n"
        f"{cat_info.description}\n"
        f"[dim]分类ID: {cat_info.name}[/]",
        title="🚀 熠觉 · Phosphene v2.0"
    ))

    try:
        # ── Step 1: 采集 ──
        raw_data = asyncio.run(cat.collect(debug=debug))

        # ── Step 2: AI 生成博客 ──
        CONSOLE.print(f"\n[bold cyan]🧠 生成 {cat_info.display_name} 文章...[/]")
        system_prompt, user_prompt = cat.get_prompts(raw_data)
        blog = ai_client.generate_blog(system_prompt, user_prompt)
        word_count = len(blog.replace(" ", "").replace("\n", ""))
        CONSOLE.print(f"  [green]✅ 文章生成完成 ({word_count} 字)[/]")

        # ── Step 3: 多格式输出 ──
        CONSOLE.print(f"\n[bold cyan]🔄 多格式内容生成...[/]")
        extra_formats = {}

        enabled_formats = [f for f in ["twitter", "newsletter", "video_script", "english"]
                           if config["output"]["formats"].get(f, True)]
        if enabled_formats:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            CONSOLE.print(f"  [dim]🔀 并行生成 {len(enabled_formats)} 种格式...[/]")

            with ThreadPoolExecutor(max_workers=config["runtime"].get("concurrency", 2)) as pool:
                fut_map = {
                    pool.submit(ai_client.generate_format, fmt, blog, cat_info.display_name): fmt
                    for fmt in enabled_formats
                }
                for fut in as_completed(fut_map):
                    fmt = fut_map[fut]
                    try:
                        content = fut.result()
                        extra_formats[fmt] = content
                        fmt_label = {"twitter": "🐦 推文串", "newsletter": "📧 通讯",
                                     "video_script": "🎬 脚本", "english": "🌍 英文"}.get(fmt, fmt)
                        CONSOLE.print(f"  [green]✅ {fmt_label} 完成 ({len(content)} 字)[/]")
                    except Exception as e:
                        CONSOLE.print(f"  [red]❌ {fmt} 生成失败: {e}[/]")

        # ── Step 4: 保存 ──
        slug_dir = output_mgr.save_all(blog, extra_formats)
        output_mgr.update_index(blog)

        # ── Step 5: 发布 ──
        publisher.publish(blog, output_mgr.slug)

        # ── 统计 ──
        elapsed = time.time() - start
        total_outputs = 1 + len(extra_formats)
        total_chars = word_count + sum(len(v) for v in extra_formats.values())

        CONSOLE.print(Panel(
            f"[bold green]✅ 全链路完成![/]\n\n"
            f"🏷  分类: {cat_info.emoji} {cat_info.display_name}\n"
            f"⏱  耗时: {elapsed:.1f}秒\n"
            f"📝 产出: {total_outputs} 份内容 ({total_chars:,} 字)\n"
            f"📁 位置: {slug_dir}",
            title="📊 本轮统计"
        ))

        return True

    except Exception as e:
        CONSOLE.print(f"\n[bold red]❌ 流水线异常: {e}[/]")
        if debug:
            import traceback
            traceback.print_exc()
        return False


def list_categories() -> list[str]:
    """列出所有已注册分类"""
    from core.registry import get_category_names
    return get_category_names()


def cmd_init():
    """初始化项目"""
    from core.ai_client import AIClient

    CONSOLE.print("[bold]🔧 初始化 熠觉 · Phosphene...[/]\n")

    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        key = input("请输入你的 API Key (OpenAI/DeepSeek/硅基流动): ").strip()
        if key:
            os.environ["OPENAI_API_KEY"] = key

    if not key:
        CONSOLE.print("[red]❌ 必须设置 API Key 才能运行[/]")
        return

    CONSOLE.print("\n[cyan]🔌 测试 AI API 连接...[/]")
    config = load_config()
    try:
        ai = AIClient(config)
        resp = ai.call(
            "你是一个简短的测试助手。",
            "请回复'连接成功'四个字。",
            temperature=0.1,
            max_tokens=50,
        )
        if "成功" in resp:
            CONSOLE.print(f"  [green]✅ 连接成功! 回复: {resp.strip()}[/]")
        else:
            CONSOLE.print(f"  [yellow]⚠️  已连接, 回复: {resp.strip()}[/]")
    except Exception as e:
        CONSOLE.print(f"  [red]❌ 连接失败: {e}[/]")
        return

    CONSOLE.print(f"\n[bold green]✅ 初始化完成! 运行 python main.py --category tech 即可开始[/]")


def cmd_deploy():
    """部署到 GitHub Pages"""
    from core.publisher import Publisher

    CONSOLE.print("[bold]🚀 部署到 GitHub Pages...[/]\n")
    config = load_config()
    publisher = Publisher(config)

    posts_dir = ROOT / config["output"]["output_dir"] / "posts"
    if not posts_dir.exists():
        CONSOLE.print("[red]❌ 没有已生成的文章[/]")
        return

    slugs = sorted([p.name for p in posts_dir.iterdir() if p.is_dir()])
    CONSOLE.print(f"[dim]找到 {len(slugs)} 篇文章[/]")

    pub_config = config.get("publish", {})
    if pub_config.get("mode") != "github-pages":
        CONSOLE.print("[yellow]⚠️  配置中发布模式不是 github-pages[/]")
        CONSOLE.print("   请修改 config.yaml → publish.mode: github-pages")
        return

    for slug in slugs:
        blog_path = posts_dir / slug / "blog.md"
        if not blog_path.exists():
            continue
        blog = blog_path.read_text(encoding="utf-8")
        publisher.publish(blog, slug)

    CONSOLE.print(f"\n[bold green]✅ 部署完成![/]")


def cmd_daemon():
    """守护模式"""
    from core.scheduler import Scheduler

    config = load_config()
    sched = Scheduler(config)
    sched.run_forever()


def main():
    parser = argparse.ArgumentParser(
        description="🤖 熠觉 · Phosphene v2.0 — 多分类采集→AI分析→多格式输出→发布",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--init", action="store_true", help="初始化 (设置 API Key + 测试连接)")
    parser.add_argument("--deploy", action="store_true", help="部署已生成的文章到 GitHub Pages")
    parser.add_argument("--daemon", action="store_true", help="守护模式 (定时循环执行)")
    parser.add_argument("--once", action="store_true", help="执行一次流水线 (默认)")
    parser.add_argument("--category", type=str, default="tech", help="指定分类 (默认: tech)")
    parser.add_argument("--list-categories", action="store_true", help="列出所有可用分类")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()

    # 初始化注册表（加载所有分类）
    from core.registry import discover_categories, list_categories as get_cat_info
    discover_categories()

    if args.list_categories:
        cats = get_cat_info()
        CONSOLE.print(Panel(
            "\n".join(f"  {c.emoji} {c.display_name:<10} — {c.description}" for c in cats),
            title="📋 可用分类"
        ))
        return

    if args.init:
        cmd_init()
    elif args.deploy:
        cmd_deploy()
    elif args.daemon:
        config = load_config()
        config["categories"] = {"active": list_categories()}
        cmd_daemon()
    else:
        run_once_for_category(args.category, debug=args.debug)


if __name__ == "__main__":
    main()
