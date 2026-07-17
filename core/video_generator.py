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
from urllib.request import urlretrieve

from core.video_assets import select_asset
from core.video_storyboard import build_storyboard

REMOTION_DIR = Path(__file__).parent.parent / "remotion-video"


def write_video_manifest(destination: Path, storyboard: dict, assets: list[dict]) -> None:
    """Persist the exact render inputs and asset provenance for human review."""
    payload = {
        "review_status": "awaiting_review",
        "storyboard": storyboard,
        "assets": assets,
    }
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_video_review_status(manifest_path: Path, status: str, note: str = "") -> dict:
    """Persist the human decision that gates use of a generated video."""
    if status not in {"awaiting_review", "approved", "changes_requested"}:
        raise ValueError(f"Unsupported video review status: {status}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["review_status"] = status
    payload["review_note"] = note
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def allocate_audio_frames(weights: list[int], total_frames: int, minimum: int = 30) -> list[int]:
    """Allocate a measured narration duration across scenes by spoken length."""
    if not weights or total_frames < minimum * len(weights):
        raise ValueError("Not enough audio duration for the requested scenes")
    weight_sum = sum(max(weight, 1) for weight in weights)
    remaining = total_frames - minimum * len(weights)
    frames = [minimum + round(remaining * max(weight, 1) / weight_sum) for weight in weights]
    frames[-1] += total_frames - sum(frames)
    return frames


def _load_evidence_urls(output_dir: Path) -> list[str]:
    """Use only article evidence already retained by the pipeline."""
    metadata_path = output_dir / "metadata.json"
    if not metadata_path.exists():
        return []
    try:
        evidence = json.loads(metadata_path.read_text(encoding="utf-8")).get("evidence", {})
        urls = []
        for source in evidence.values() if isinstance(evidence, dict) else []:
            for item in source.get("items", []):
                if item.get("url"):
                    urls.append(item["url"])
        return urls
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def _stage_stock_assets(assets: list[dict], public_dir: Path, slug: str) -> list[str]:
    """Download selected Pexels videos so Remotion never depends on remote playback."""
    staged = []
    for index, asset in enumerate(assets):
        if asset.get("kind") != "stock_video" or not asset.get("download_url"):
            continue
        filename = f"{slug}_asset_{index:02d}.mp4"
        try:
            urlretrieve(asset["download_url"], public_dir / filename)  # nosec B310: selected HTTPS asset
            asset["file_name"] = filename
            staged.append(filename)
        except OSError:
            asset.clear()
            asset.update({"kind": "motion_graphic", "source": "generated", "attribution": {}})
    return staged


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
            elif current_lines and re.match(r'^\s{2,}\S+', line):
                continuation = line.strip()
                if continuation:
                    current_lines.append(continuation)

    if current_scene is not None and current_lines:
        current_scene["lines"] = current_lines
        scenes.append(current_scene)
    return scenes


# 旧格式 → 视觉类型映射（按场景位置）
# ── 默认视觉类型映射 ──
_DEFAULT_VISUAL_TYPES = [
    "explode", "number", "text", "pop", "text", "tag", "chain", "ending"
]

# ── 旧格式解析跳过模式 ──
_SKIP_SEC_PATTERNS = [
    r'总时长', r'风格', r'目标', r'适用平台',
    r'脚本设计思路', r'制作备注', r'^[0-9.]+$',
    r'以下是完整', r'完整的脚本方案',
]


def _find_content_start(lines: list[str]) -> int:
    """找到旧格式脚本的实际内容起始行"""
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("####") or stripped.startswith("---"):
            return idx
        if re.match(r'^(好的|没问题|当然|首先)', stripped):
            return idx + 1
    return 0


def _split_sections(lines: list[str]) -> list[tuple[str, str]]:
    """按 #### 标题 / --- 分隔线切分节"""
    import re as _re
    sections = []
    current = []
    section_headers = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("####") or stripped.startswith("---"):
            if current:
                sections.append((section_headers[-1] if section_headers else "", "\n".join(current)))
                current = []
            header = _re.sub(r'^#{1,4}\s*|【[^】]+】', '', stripped).strip()
            section_headers.append(header)
        elif stripped and not stripped.startswith("**制作"):
            current.append(stripped)
    if current:
        sections.append((section_headers[-1] if section_headers else "", "\n".join(current)))
    return sections


def _is_skip_section(header: str, body: str) -> bool:
    """判断是否跳过该节（元信息/备注/空内容）"""
    if len(body.strip()) < 15:
        return True
    if header in ('---', '') and not re.search(r'(?:口播|文案)', body):
        return True
    for pat in _SKIP_SEC_PATTERNS:
        if re.search(pat, header + body[:60]):
            return True
    return False


def _clean_text(raw: str) -> str:
    """去除 markdown 标记和舞台指示，返回纯文本"""
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', raw)          # **加粗**
    text = re.sub(r'^\s*\*\s+', '', text)                         # 行首 *
    text = re.sub(r'^#{1,4}\s+', '', text)                        # ### 标记
    text = re.sub(r'【[\d:→\-\[\]\.]+】', '', text)               # 【0:00-0:05】
    text = re.sub(r'^\*{0,2}(?:口播|画面|文案|字幕)\*{0,2}[：:（(]', '', text)  # 口播：
    text = re.sub(r'[（(](?:画面|口播|字幕|建议|备注|数据)[）)]', '', text)       # (画面)
    text = re.sub(r'\s{2,}', ' ', text)                           # 多余空白
    text = text.strip().strip('，。！？；、：').strip()
    return text


def _extract_text_from_section(body: str) -> str:
    """从一节文本中提取口播文案"""
    body_lines = body.split("\n")
    for li, line in enumerate(body_lines):
        m = re.match(r'.*?口播.*?(?:[：:]\s*(.+))?', line)
        if m:
            if m.group(1):
                candidate = _clean_text(m.group(1))
                if len(candidate) > 5:
                    return candidate
            else:
                if li + 1 < len(body_lines):
                    next_line = body_lines[li + 1].strip().strip('"「」""')
                    if next_line and len(next_line) > 5:
                        return _clean_text(next_line)
    # 没有口播标记，找第一个有意义的句子
    for line in body.split("\n"):
        if (len(line) > 8
                and not re.match(r'^\s*#|\-\-\-|\*{2}$|【', line)
                and '画面' not in line[:8]
                and '制作' not in line[:8]):
            candidate = _clean_text(line)
            if len(candidate) > 5:
                return candidate
    return ""


def _split_text_lines(text: str) -> list[str]:
    """将一段文案按 15 字/CJK 智能分行"""
    import re as _re
    parts = _re.split(r'[，。！？；、]', text)
    lines_out = []
    for p in parts:
        p = p.strip(' "\'「」""（）()\u3000')
        if not p or len(p) < 2:
            continue
        while len(p) > 15:
            split_at = max(p.rfind('，', 0, 15), p.rfind(' ', 0, 15),
                           p.rfind('、', 0, 15), 12)
            if split_at <= 0 or split_at > 15:
                split_at = 15
            lines_out.append(p[:split_at])
            p = p[split_at:]
        if p:
            lines_out.append(p)
    return lines_out


def _parse_legacy(script_text: str) -> list:
    """解析旧格式（长文分镜脚本）"""
    lines = script_text.split("\n")
    content_start = _find_content_start(lines)
    lines = lines[content_start:]
    sections = _split_sections(lines)

    scenes = []
    for i, (header, body) in enumerate(sections[:10]):
        if _is_skip_section(header, body):
            continue
        if len(scenes) >= 8:
            break
        text = _extract_text_from_section(body)
        if not text:
            continue
        lines_out = _split_text_lines(text)
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
                    await asyncio.sleep(2 * attempt)
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


def generate_continuous_tts(
    scenes: list, slug: str, work_dir: Path, voice: str = "zh-CN-XiaoxiaoNeural"
) -> tuple[list[str], list[int]]:
    """Generate one narration track so scene boundaries do not reset the voice."""
    import asyncio
    import edge_tts

    texts = ["，".join(scene["lines"]) for scene in scenes]
    output = work_dir / f"{slug}_narration.mp3"

    async def _generate() -> None:
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate("\n\n".join(texts), voice=voice, rate="-4%")
                await communicate.save(str(output))
                return
            except Exception as exc:
                if attempt == 3:
                    raise RuntimeError(f"TTS generation failed after 3 attempts: {exc}") from exc
                await asyncio.sleep(attempt * 2)

    asyncio.run(_generate())
    try:
        from moviepy import AudioFileClip
        clip = AudioFileClip(str(output))
        total_frames = round(clip.duration * 30)
        clip.close()
    except ImportError:
        total_frames = max(30 * len(scenes), sum(len(text) for text in texts) * 9)
    return [output.name], allocate_audio_frames([len(text) for text in texts], total_frames)


def render_video(
    slug: str,
    scenes: list,
    audio_files: list,
    audio_frames: list,
    output_path: Path,
    assets: list[dict] | None = None,
    category: str = "tech",
    title: str = "",
) -> str:
    """调用 Remotion CLI 渲染视频"""
    total_frames = sum(audio_frames)

    props = {
        "slug": slug,
        "scenes": scenes,
        "audioFiles": audio_files,
        "audioFrames": audio_frames,
        "totalFrames": total_frames,
        "assets": assets or [],
        "category": category,
        "title": title,
    }

    props_json = json.dumps(props, ensure_ascii=False)

    executable = REMOTION_DIR / "node_modules" / ".bin" / (
        "remotion.cmd" if os.name == "nt" else "remotion"
    )
    if not executable.exists():
        raise RuntimeError("Remotion 依赖未安装，请先在 remotion-video 目录执行 npm ci")

    cmd = [
        str(executable), "render",
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
    if len(scenes) != 8:
        raise ValueError(f"视频脚本必须包含 8 个场景，当前解析到 {len(scenes)} 个")
    allowed_types = {"explode", "number", "text", "pop", "tag", "chain", "ending"}
    invalid_types = [scene["visualType"] for scene in scenes if scene["visualType"] not in allowed_types]
    if invalid_types:
        raise ValueError(f"不支持的视觉类型: {', '.join(invalid_types)}")

    _progress(0.1, f"已解析 {len(scenes)} 个场景")

    # 2. 创建临时工作目录
    output_dir = posts_base / category / slug
    storyboard = build_storyboard(parsed, _load_evidence_urls(output_dir))
    scenes = storyboard["scenes"]
    assets = [select_asset(scene, os.environ.get("PEXELS_API_KEY")) for scene in scenes]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_video_manifest(output_dir / "video_manifest.json", storyboard, assets)

    with tempfile.TemporaryDirectory(prefix=f"video_{slug}_") as tmp_dir:
        work_dir = Path(tmp_dir)

        # 3. 生成 TTS
        _progress(0.2, "正在生成配音 (1/8)...")
        from core.config import load_config
        voice = load_config().get("video", {}).get("audio_voice", "zh-CN-XiaoxiaoNeural")
        asset_key = f"{category}_{slug}"
        audio_files, audio_frames = generate_continuous_tts(scenes, asset_key, work_dir, voice=voice)
        _progress(0.4, "配音生成完成")

        # 4. 拷贝音频到 Remotion public/
        _progress(0.45, "准备渲染素材...")
        public_dir = REMOTION_DIR / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        for af in audio_files:
            shutil.copy2(work_dir / af, public_dir / af)
        staged_assets = _stage_stock_assets(assets, public_dir, asset_key)
        write_video_manifest(output_dir / "video_manifest.json", storyboard, assets)

        try:
            # 5. 渲染视频
            _progress(0.5, "Remotion 渲染中...")
            tmp_output = work_dir / f"{slug}.mp4"
            render_video(
                slug, scenes, audio_files, audio_frames,
                tmp_output,
                assets=assets,
                category=parsed["category"],
                title=parsed["title"],
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
            for filename in staged_assets:
                fpath = public_dir / filename
                if fpath.exists():
                    fpath.unlink()
