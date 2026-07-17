#!/usr/bin/env python3
"""
熠觉 · Phosphene v2.2
================
多分类热点采集 → 证据规范化 → AI 分析 → 人工审核发布

一条命令跑一个分类：
    python main.py --category finance

可用分类：
    python main.py --list-categories

环境变量：
    OPENAI_API_KEY=sk-xxx
"""

import argparse
import hashlib
import json
import os
from rich.panel import Panel

from core.config import ROOT, CONSOLE, load_config


from core.runner import run_once_for_category


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

    if not key:
        CONSOLE.print("[red]❌ 必须设置 API Key 才能运行[/]")
        return

    # 密钥只用于当前进程，不落盘。
    os.environ["OPENAI_API_KEY"] = key

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

    CONSOLE.print("\n[bold green]✅ 连接测试通过[/]")
    CONSOLE.print("[yellow]安全提示：密钥未写入磁盘。启动服务前请设置 OPENAI_API_KEY 环境变量。[/]")


def cmd_deploy():
    """部署到 GitHub Pages"""
    from core.publisher import Publisher
    from core.quality import ContentQualityError, validate_generated_content

    CONSOLE.print("[bold]🚀 部署到 GitHub Pages...[/]\n")
    config = load_config()
    publisher = Publisher(config)

    posts_dir = ROOT / config["output"]["output_dir"] / "posts"
    if not posts_dir.exists():
        CONSOLE.print("[red]❌ 没有已生成的文章[/]")
        return

    articles = []
    for category_dir in posts_dir.iterdir():
        if not category_dir.is_dir():
            continue
        for slug_dir in category_dir.iterdir():
            blog_path = slug_dir / "blog.md"
            metadata_path = slug_dir / "metadata.json"
            if not (slug_dir.is_dir() and blog_path.exists() and metadata_path.exists()):
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if metadata.get("review_status") != "approved":
                continue
            blog = blog_path.read_text(encoding="utf-8")
            approved_hash = metadata.get("approved_content_sha256")
            current_hash = hashlib.sha256(blog.encode("utf-8")).hexdigest()
            if not approved_hash or approved_hash != current_hash:
                CONSOLE.print(f"[yellow]⚠️  跳过 {category_dir.name}/{slug_dir.name}：审核后内容已变更[/]")
                continue
            evidence = metadata.get("evidence")
            if not isinstance(evidence, dict):
                continue
            try:
                validate_generated_content(blog, evidence, category_dir.name)
            except ContentQualityError as exc:
                CONSOLE.print(f"[yellow]⚠️  跳过 {category_dir.name}/{slug_dir.name}：{exc}[/]")
                continue
            articles.append((category_dir.name, slug_dir.name, blog_path))
    CONSOLE.print(f"[dim]找到 {len(articles)} 篇已审核文章[/]")
    if not articles:
        CONSOLE.print("[yellow]⚠️  没有可部署文章；请在 Web 审核室完成审核[/]")
        return

    pub_config = config.get("publish", {})
    if pub_config.get("mode") != "github-pages":
        CONSOLE.print("[yellow]⚠️  配置中发布模式不是 github-pages[/]")
        CONSOLE.print("   请修改 config.yaml → publish.mode: github-pages")
        return

    for category, slug, blog_path in articles:
        blog = blog_path.read_text(encoding="utf-8")
        publisher.publish(blog, category, slug)

    CONSOLE.print("\n[bold green]✅ 部署完成![/]")


def cmd_daemon(use_scrapling: bool = True):
    """守护模式"""
    from core.scheduler import Scheduler

    config = load_config()
    config["runtime"]["scrapling"] = use_scrapling
    sched = Scheduler(config)
    sched.run_forever()


def main():
    parser = argparse.ArgumentParser(
        description="🤖 熠觉 · Phosphene v2.2 — 证据采集→AI分析→质量校验→人工审核",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--init", action="store_true", help="初始化 (设置 API Key + 测试连接)")
    parser.add_argument("--deploy", action="store_true", help="部署已生成的文章到 GitHub Pages")
    parser.add_argument("--daemon", action="store_true", help="守护模式 (定时循环执行)")
    parser.add_argument("--once", action="store_true", help="执行一次流水线 (默认)")
    parser.add_argument("--category", type=str, default="tech", help="指定分类 (默认: tech)")
    parser.add_argument("--list-categories", action="store_true", help="列出所有可用分类")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--scrapling", action=argparse.BooleanOptionalAction,
                        default=True, help="是否启用 Scrapling 浏览器采集 (默认: 启用)")
    parser.add_argument("--serve", action="store_true", help="启动 Web 管理界面")
    parser.add_argument("--host", default="127.0.0.1", help="Web 监听地址（P0 安全版仅允许本机地址）")
    parser.add_argument("--port", type=int, default=5000, help="Web 监听端口")
    parser.add_argument("--generate-video", nargs=2, metavar=("CATEGORY", "SLUG"),
                        help="为指定文章生成 Remotion 视频")

    args = parser.parse_args()

    # 初始化注册表（加载所有分类）
    from core.registry import discover_categories, list_categories as get_cat_info
    discover_categories()

    if args.serve:
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            CONSOLE.print("[red]❌ 安全限制：当前版本不允许直接监听公网地址。[/]")
            CONSOLE.print("   请监听 127.0.0.1，并通过带身份认证的反向代理或 SSH 隧道访问。")
            return

        from web.server import create_app
        import uvicorn
        app = create_app(static_dir=ROOT / "web" / "static")
        CONSOLE.print(f"[bold green]🌐 Web UI 启动: http://{args.host}:{args.port}[/]")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return

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
        cmd_daemon(use_scrapling=args.scrapling)
    elif args.generate_video:
        category, slug = args.generate_video
        from core.video_generator import generate_video
        result = generate_video(category, slug, ROOT / "docs" / "posts")
        CONSOLE.print(f"[green]✅ 视频已生成: {result}[/]")
    else:
        run_once_for_category(args.category, debug=args.debug, use_scrapling=args.scrapling)


if __name__ == "__main__":
    main()
