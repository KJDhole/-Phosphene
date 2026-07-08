"""
Remotion 视频生成编排器

工作流：
  1. parse_script() — 解析 video_script.md 为 JSON 场景数据
  2. generate_tts() — edge-tts 生成 8 段配音，测量帧数
  3. render_video() — 调用 Remotion CLI 渲染
  4. generate_video() — 对外入口
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

REMOTION_DIR = Path(__file__).parent.parent / "remotion-video"


def parse_script(script_text: str) -> dict:
    """解析 video_script.md → scenes JSON

    格式：
    ## S0 | 场景名 | visualType | gradient
    文案：第一行
           第二行
    """
    scenes = []
    category = "tech"
    title = ""

    # 提取标题
    for line in script_text.split("\n"):
        m = re.match(r'^#\s+(.+)$', line.strip())
        if m and not line.startswith("##"):
            title = m.group(1).strip()
            break

    # 提取分类
    m = re.search(r'>\s*分类[：:]\s*(\S+)', script_text)
    if m:
        category = m.group(1).strip()

    # 解析场景
    current_scene = None
    current_lines = []

    for line in script_text.split("\n"):
        # 匹配 ## S0 | xxx | explode | a1
        m = re.match(r'^##\s+S(\d+)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|\s*(\w+)', line)
        if m:
            # 保存上一个场景
            if current_scene is not None and current_lines:
                current_scene["lines"] = current_lines
                scenes.append(current_scene)

            current_scene = {
                "id": int(m.group(1)),
                "name": m.group(2).strip(),
                "visualType": m.group(3).strip(),
                "gradient": m.group(4).strip(),
            }
            current_lines = []
            continue

        # 匹配文案行
        if current_scene is not None:
            m2 = re.match(r'^文案[：:]\s*(.+)', line)
            if m2:
                text = m2.group(1).strip()
                if text:
                    current_lines.append(text)

    # 保存最后一个场景
    if current_scene is not None and current_lines:
        current_scene["lines"] = current_lines
        scenes.append(current_scene)

    return {
        "title": title,
        "category": category,
        "scenes": scenes,
    }


def generate_tts(scenes: list, slug: str, work_dir: Path) -> tuple:
    """edge-tts 生成 8 段配音，返回 (audio_files, audio_frames)"""
    import asyncio
    import edge_tts

    audio_files = []
    audio_frames = []

    for i, scene in enumerate(scenes):
        text = "，".join(scene["lines"])
        output = work_dir / f"{slug}_audio_{i:02d}.mp3"

        async def _gen(out: Path, txt: str):
            await edge_tts.Communicate(
                txt, voice="zh-CN-XiaoxiaoNeural"
            ).save(str(out))

        asyncio.run(_gen(output, text))

        # 测量帧数
        try:
            from moviepy import AudioFileClip
            clip = AudioFileClip(str(output))
            frames = round(clip.duration * 30)
            clip.close()
        except ImportError:
            # 回退：粗略估计（平均每字 0.3s）
            char_count = len(text)
            estimated_s = char_count * 0.3
            frames = round(estimated_s * 30)

        audio_files.append(output.name)
        audio_frames.append(max(frames, 30))  # 最少 1 秒

    return audio_files, audio_frames


def render_video(
    slug: str,
    scenes: list,
    audio_files: list,
    audio_frames: list,
    output_path: Path,
) -> str:
    """调用 Remotion CLI 渲染视频"""
    total_frames = sum(audio_frames)

    props = {
        "slug": slug,
        "scenes": scenes,
        "audioFiles": audio_files,
        "audioFrames": audio_frames,
        "totalFrames": total_frames,
    }

    props_json = json.dumps(props, ensure_ascii=False)

    cmd = [
        "npx.cmd", "remotion", "render",
        str(REMOTION_DIR / "src" / "index.ts"),
        "GenericVideo",
        str(output_path),
        "--props", props_json,
        "--overwrite",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(REMOTION_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Remotion render failed:\n{result.stderr[:2000]}"
        )

    return str(output_path)


def generate_video(
    category: str,
    slug: str,
    posts_base: Path,
) -> Path:
    """对外入口：生成视频并保存到文章目录

    Args:
        category: 分类名 (tech/finance/...)
        slug: 文章 slug (20260708_1454)
        posts_base: docs/posts/ 路径

    Returns:
        video.mp4 的 Path
    """
    script_path = posts_base / category / slug / "video_script.md"
    if not script_path.exists():
        raise FileNotFoundError(f"video_script.md not found: {script_path}")

    # 1. 解析脚本
    script_text = script_path.read_text(encoding="utf-8")
    parsed = parse_script(script_text)
    scenes = parsed["scenes"]

    if not scenes:
        raise ValueError("No scenes found in video_script.md")

    # 2. 创建临时工作目录
    with tempfile.TemporaryDirectory(prefix=f"video_{slug}_") as tmp_dir:
        work_dir = Path(tmp_dir)

        # 3. 生成 TTS
        audio_files, audio_frames = generate_tts(scenes, slug, work_dir)

        # 4. 拷贝音频到 Remotion public/
        public_dir = REMOTION_DIR / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        for af in audio_files:
            shutil.copy2(work_dir / af, public_dir / af)

        try:
            # 5. 渲染视频
            tmp_output = work_dir / f"{slug}.mp4"
            render_video(
                slug, scenes, audio_files, audio_frames,
                tmp_output,
            )

            # 6. 保存到文章目录
            output_dir = posts_base / category / slug
            output_dir.mkdir(parents=True, exist_ok=True)
            final_path = output_dir / "video.mp4"
            shutil.copy2(tmp_output, final_path)

            return final_path

        finally:
            # 清理 public/ 中的临时音频
            for af in audio_files:
                fpath = public_dir / af
                if fpath.exists():
                    fpath.unlink()
