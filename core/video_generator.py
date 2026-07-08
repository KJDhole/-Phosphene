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

    # 解析场景 — 先尝试新格式
    scenes = _parse_structured(script_text)

    # 如果新格式解析不到场景，回退到旧格式
    if not scenes:
        scenes = _parse_legacy(script_text)

    return {
        "title": title,
        "category": category,
        "scenes": scenes,
    }


def _parse_structured(script_text: str) -> list:
    """解析新格式：## S0 | xxx | explode | a1"""
    scenes = []
    current_scene = None
    current_lines = []

    for line in script_text.split("\n"):
        m = re.match(r'^##\s+S(\d+)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|\s*(\w+)', line)
        if m:
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
        if current_scene is not None:
            m2 = re.match(r'^文案[：:]\s*(.+)', line)
            if m2:
                text = m2.group(1).strip()
                if text:
                    current_lines.append(text)

    if current_scene is not None and current_lines:
        current_scene["lines"] = current_lines
        scenes.append(current_scene)
    return scenes


# 旧格式 → 视觉类型映射（按场景位置）
_DEFAULT_VISUAL_TYPES = [
    "explode", "number", "text", "pop", "text", "tag", "chain", "ending"
]


def _parse_legacy(script_text: str) -> list:
    """解析旧格式（长文分镜脚本）"""
    import re as _re

    lines = script_text.split("\n")

    # 找到第一个 #### 或 --- 作为实际内容的开始
    content_start = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("####") or stripped.startswith("---"):
            content_start = idx
            break
        # 跳过 AI 开场白（"好的，没问题！" 行）
        if re.match(r'^(好的|没问题|当然|首先)', stripped):
            content_start = idx + 1

    lines = lines[content_start:]

    # 按 #### 标题、--- 分隔线、**制作备注** 分节
    sections = []
    current = []
    section_headers = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("####") or stripped.startswith("---"):
            if current:
                sections.append((section_headers[-1] if section_headers else "", "\n".join(current)))
                current = []
            # 提取标题（如 "#### 【0:00-0:05】开场钩子"）
            header = _re.sub(r'^#{1,4}\s*|【[^】]+】', '', stripped).strip()
            section_headers.append(header)
        elif stripped and not stripped.startswith("**制作"):
            current.append(stripped)

    if current:
        sections.append((section_headers[-1] if section_headers else "", "\n".join(current)))

    # 跳过纯元信息/备注节
    skip_sec_patterns = [
        r'总时长', r'风格', r'目标', r'适用平台',
        r'脚本设计思路', r'制作备注', r'^[0-9.]+$',
        r'以下是完整', r'完整的脚本方案',
    ]

    # 跳过 header 为 --- 或空且 body 短于 15 字的节
    def _is_skip_section(header: str, body: str) -> bool:
        if len(body.strip()) < 15:
            return True
        if header in ('---', '') and not _re.search(r'(?:口播|文案)', body):
            return True
        for pat in skip_sec_patterns:
            if _re.search(pat, header + body[:60]):
                return True
        return False

    def _clean_text(raw: str) -> str:
        """去除 markdown 标记和舞台指示，返回纯文本"""
        text = _re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', raw)          # **加粗**
        text = _re.sub(r'^\s*\*\s+', '', text)                         # 行首 *
        text = _re.sub(r'^#{1,4}\s+', '', text)                        # ### 标记
        text = _re.sub(r'【[\d:→\-\[\]\.]+】', '', text)               # 【0:00-0:05】
        text = _re.sub(r'^\*{0,2}(?:口播|画面|文案|字幕)\*{0,2}[：:（(]', '', text)  # 口播：
        text = _re.sub(r'[（(](?:画面|口播|字幕|建议|备注|数据)[）)]', '', text)       # (画面)
        text = _re.sub(r'\s{2,}', ' ', text)                           # 多余空白
        text = text.strip().strip('，。！？；、：').strip()
        return text

    scenes = []
    for i, (header, body) in enumerate(sections[:10]):
        if _is_skip_section(header, body):
            continue
        if len(scenes) >= 8:
            break

        # 提取文本：优先找口播行
        text = ""
        body_lines = body.split("\n")
        for li, line in enumerate(body_lines):
            # 匹配 **口播：**、**（口播）** 等多种格式
            m = _re.match(r'.*?口播.*?(?:[：:]\s*(.+))?', line)
            if m:
                if m.group(1):
                    # 有冒号：**口播：** 文字
                    candidate = _clean_text(m.group(1))
                    if len(candidate) > 5:
                        text = candidate
                        break
                else:
                    # 无冒号：**（口播）**，文字在下一行
                    if li + 1 < len(body_lines):
                        next_line = body_lines[li + 1].strip().strip('"「」""')
                        if next_line and len(next_line) > 5:
                            text = _clean_text(next_line)
                            break

        if not text:
            # 找第一个有意义的句子
            for line in body.split("\n"):
                if (len(line) > 8
                        and not _re.match(r'^\s*#|\-\-\-|\*{2}$|【', line)
                        and '画面' not in line[:8]
                        and '制作' not in line[:8]):
                    candidate = _clean_text(line)
                    if len(candidate) > 5:
                        text = candidate
                        break

        if text:
            parts = _re.split(r'[，。！？；、]', text)
            lines_out = []
            for p in parts:
                p = p.strip(' "\'「」""（）()\u3000')
                if not p or len(p) < 2:
                    continue
                # CJK-safe 分行：每行 ≤15 中文字符
                while len(p) > 15:
                    # 在标点或空格处分，否则硬切
                    split_at = max(p.rfind('，', 0, 15), p.rfind(' ', 0, 15),
                                   p.rfind('、', 0, 15), 12)
                    if split_at <= 0 or split_at > 15:
                        split_at = 15
                    lines_out.append(p[:split_at])
                    p = p[split_at:]
                if p:
                    lines_out.append(p)

            if lines_out:
                scenes.append({
                    "id": len(scenes),
                    "name": header or f"场景{len(scenes)}",
                    "visualType": _DEFAULT_VISUAL_TYPES[len(scenes)] if len(scenes) < len(_DEFAULT_VISUAL_TYPES) else "text",
                    "gradient": "a1",
                    "lines": lines_out[:3],
                })

    return scenes


def generate_tts(scenes: list, slug: str, work_dir: Path, voice: str = "zh-CN-XiaoxiaoNeural") -> tuple:
    """edge-tts 生成 8 段配音，返回 (audio_files, audio_frames)

    支持代理：设置 HTTP_PROXY / HTTPS_PROXY 环境变量
    """
    import asyncio
    import edge_tts

    audio_files = []
    audio_frames = []

    for i, scene in enumerate(scenes):
        text = "，".join(scene["lines"])
        output = work_dir / f"{slug}_audio_{i:02d}.mp3"

        async def _gen(out: Path, txt: str, attempt: int = 1):
            try:
                communicate = edge_tts.Communicate(txt, voice=voice)
                await communicate.save(str(out))
            except Exception as e:
                if attempt < 3:
                    import time as _time
                    _time.sleep(2 * attempt)
                    await _gen(out, txt, attempt + 1)
                else:
                    raise RuntimeError(
                        f"TTS 生成失败（已重试3次）: {e}\n"
                        f"提示：可设置 HTTP_PROXY 环境变量使用代理"
                    )

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
    progress_callback: any = None,
) -> Path:
    """对外入口：生成视频并保存到文章目录

    Args:
        category: 分类名 (tech/finance/...)
        slug: 文章 slug (20260708_1454)
        posts_base: docs/posts/ 路径
        progress_callback: 可选的回调函数(percent: float, message: str)

    Returns:
        video.mp4 的 Path
    """
    def _progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    script_path = posts_base / category / slug / "video_script.md"
    if not script_path.exists():
        raise FileNotFoundError(f"video_script.md not found: {script_path}")

    # 1. 解析脚本
    _progress(0.05, "解析视频脚本...")
    script_text = script_path.read_text(encoding="utf-8")
    parsed = parse_script(script_text)
    scenes = parsed["scenes"]

    if not scenes:
        raise ValueError("No scenes found in video_script.md")

    _progress(0.1, f"已解析 {len(scenes)} 个场景")

    # 2. 创建临时工作目录
    with tempfile.TemporaryDirectory(prefix=f"video_{slug}_") as tmp_dir:
        work_dir = Path(tmp_dir)

        # 3. 生成 TTS
        _progress(0.2, "正在生成配音 (1/8)...")
        audio_files, audio_frames = generate_tts(scenes, slug, work_dir)
        _progress(0.4, "配音生成完成")

        # 4. 拷贝音频到 Remotion public/
        _progress(0.45, "准备渲染素材...")
        public_dir = REMOTION_DIR / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        for af in audio_files:
            shutil.copy2(work_dir / af, public_dir / af)

        try:
            # 5. 渲染视频
            _progress(0.5, "Remotion 渲染中...")
            tmp_output = work_dir / f"{slug}.mp4"
            render_video(
                slug, scenes, audio_files, audio_frames,
                tmp_output,
            )

            # 6. 保存到文章目录
            _progress(0.9, "保存视频文件...")
            output_dir = posts_base / category / slug
            output_dir.mkdir(parents=True, exist_ok=True)
            final_path = output_dir / "video.mp4"
            shutil.copy2(tmp_output, final_path)

            _progress(1.0, "视频生成完成")
            return final_path

        finally:
            # 清理 public/ 中的临时音频
            for af in audio_files:
                fpath = public_dir / af
                if fpath.exists():
                    fpath.unlink()
