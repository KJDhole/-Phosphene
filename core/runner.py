"""
流水线执行器 — 运行单个分类的完整采集→AI→保存→发布流程
"""

from __future__ import annotations
import time
import asyncio
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.panel import Panel

from core.ai_client import AIClient
from core.output import OutputManager
from core.publisher import Publisher
from core.registry import get_category, list_categories
from core.config import load_config, CONSOLE
from core.diagnostics import (
    diagnostic_event,
    diagnostic_exception,
    end_diagnostic_run,
    set_diagnostic_context,
    start_diagnostic_run,
)
from core.quality import normalize_citation_syntax, validate_generated_content


def run_once_for_category(category_name: str, debug: bool = False,
                          use_scrapling: bool = True) -> bool:
    """执行指定分类的一次完整流水线"""

    start = time.time()
    config = deepcopy(load_config())
    if debug:
        config["runtime"]["debug"] = True
    run_id = f"cli-{category_name}-{time.time_ns()}"
    start_diagnostic_run(
        run_id,
        [category_name],
        config,
        use_scrapling=use_scrapling,
        origin="cli",
    )
    set_diagnostic_context(category=category_name, stage="category.start")

    # 获取分类
    cat = get_category(category_name)
    if not cat:
        CONSOLE.print(f"[red]❌ 未知分类: {category_name}[/]")
        CONSOLE.print(f"   可用分类: {', '.join(c.name for c in list_categories())}")
        diagnostic_event("pipeline.category_unknown", "ERROR", requested_category=category_name)
        end_diagnostic_run("failed", reason="unknown_category")
        return False

    cat_info = cat.info
    try:
        diagnostic_event(
            "pipeline.category_started",
            display_name=cat_info.display_name,
            source_count=len(cat.sources),
        )
        ai_client = AIClient(config)
        output_mgr = OutputManager(config, category_name=category_name)
        publisher = Publisher(config)

        CONSOLE.print(Panel(
            f"[bold]{cat_info.emoji} {cat_info.display_name}[/]\n"
            f"{cat_info.description}\n"
            f"[dim]分类ID: {cat_info.name}[/]",
            title="🚀 熠觉 · Phosphene v2.2"
        ))

        # ── Step 1: 采集 ──
        set_diagnostic_context(stage="collect")
        scrapling_label = "Scrapling浏览器" if use_scrapling else "HTTP直连"
        CONSOLE.print(f"\n[bold cyan]📡 采集数据... (模式: {scrapling_label})[/]")
        raw_data = asyncio.run(cat.collect(debug=debug, use_scrapling=use_scrapling))

        # ── Step 2: AI 生成博客 ──
        set_diagnostic_context(stage="ai.generate_blog")
        CONSOLE.print(f"\n[bold cyan]🧠 生成 {cat_info.display_name} 文章...[/]")
        system_prompt, user_prompt = cat.get_prompts(raw_data)
        blog = normalize_citation_syntax(ai_client.generate_blog(system_prompt, user_prompt))
        quality_report = validate_generated_content(blog, raw_data, category_name)
        diagnostic_event(
            "pipeline.quality_passed",
            cited_sources=quality_report.cited_sources,
            evidence_count=quality_report.evidence_count,
        )
        word_count = len(blog.replace(" ", "").replace("\n", ""))
        CONSOLE.print(
            f"  [green]✅ 文章生成并通过证据检查 "
            f"({word_count} 字, {len(quality_report.cited_sources)} 个引用)[/]"
        )

        # ── Step 3: 多格式输出 ──
        set_diagnostic_context(stage="formats")
        CONSOLE.print("\n[bold cyan]🔄 多格式内容生成...[/]")
        extra_formats = {}

        enabled_formats = [f for f in ["twitter", "newsletter", "video_script", "english"]
                           if config["output"]["formats"].get(f, True)]
        if enabled_formats:
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
                        diagnostic_exception("pipeline.derived_format_failed", e, format=fmt)
                        CONSOLE.print(f"  [red]❌ {fmt} 生成失败: {e}[/]")

        # ── Step 4: 保存 ──
        set_diagnostic_context(stage="save")
        slug_dir = output_mgr.save_all(
            blog,
            extra_formats,
            metadata={
                "category": category_name,
                "evidence": raw_data,
                "quality": quality_report.to_dict(),
                "review_status": (
                    "awaiting_review"
                    if config.get("quality", {}).get("require_human_review", True)
                    else "not_required"
                ),
            },
        )
        output_mgr.update_index(blog)

        # ── Step 5: 发布 ──
        set_diagnostic_context(stage="publish")
        if (config.get("publish", {}).get("mode") != "local"
                and config.get("quality", {}).get("require_human_review", True)):
            CONSOLE.print("  [yellow]🛡️ 草稿等待人工审核，未自动发布[/]")
        else:
            publish_result = publisher.publish(blog, category_name, output_mgr.slug)
            if publish_result.get("status") == "error":
                raise RuntimeError("内容已保存，但发布失败")

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

        end_diagnostic_run("completed", slug=output_mgr.slug, elapsed_seconds=round(elapsed, 3))
        return True

    except Exception as e:
        diagnostic_exception("pipeline.cli_failed", e)
        end_diagnostic_run("failed")
        CONSOLE.print(f"\n[bold red]❌ 流水线异常: {e}[/]")
        if debug:
            import traceback
            traceback.print_exc()
        return False
