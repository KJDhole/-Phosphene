"""
AI 短视频自动剪辑器 — 高质量的免费方案

工作流:
  脚本解析 → Fish Audio 免费配音 → Pexels 免费 B-roll → moviepy 合成

安装:
  pip install moviepy requests pydub
  # Fish Audio 注册免费拿 API Key: https://fish.audio
"""

import os
import json
import re
import requests
import tempfile
from pathlib import Path
from moviepy import *
from typing import Optional

# ════════════════════════════════════════════════════════
# 配置（全部免费/低价）
# ════════════════════════════════════════════════════════

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")     # 免费注册: https://www.pexels.com/api/
FISH_AUDIO_KEY = os.getenv("FISH_AUDIO_KEY", "")      # 免费注册: https://fish.audio

# 默认参数
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 竖屏 9:16，抖音/B站/小红书通用
FPS = 30

# 字体检测（Windows 常见路径）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
    "C:/Windows/Fonts/msyh.ttf",
    "C:/Windows/Fonts/simhei.ttf",   # 黑体
    "C:/Windows/Fonts/simsun.ttc",   # 宋体
    "C:/Windows/Fonts/arial.ttf",    # Arial fallback
]
FONT_PATH = None
for _f in _FONT_CANDIDATES:
    if Path(_f).exists():
        FONT_PATH = _f
        break


# ════════════════════════════════════════════════════════
# 1. 脚本解析
# ════════════════════════════════════════════════════════

def parse_script(script_text: str) -> list[dict]:
    """
    把短视频脚本解析为片段列表
    每个片段: {text, duration, visual_hint}
    """
    segments = []
    lines = script_text.strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 跳过分镜标注
        if line.startswith("**") and line.endswith("**"):
            continue
        if line.startswith("【"):
            continue
        if line.startswith("#"):
            continue
        if "口播：" in line:
            text = line.split("口播：", 1)[1].strip()
        elif "画面：" in line:
            text = line.split("画面：", 1)[1].strip()
        else:
            text = line
        
        # 按句号分句，每句一个片段
        sentences = re.split(r'[。！？；]', text)
        for s in sentences:
            s = s.strip()
            if len(s) < 5:  # 太短跳过
                continue
            # 估计时长：中文约 4 字/秒
            duration = max(2.0, len(s) / 4)
            segments.append({
                "text": s,
                "duration": duration,
                "visual_hint": extract_visual_hint(line),
            })
    
    return segments


def extract_visual_hint(line: str) -> str:
    """从行里提取画面关键词"""
    keywords = {
        "GitHub": "code",
        "星": "stars",
        "AI": "artificial intelligence",
        "模型": "neural network",
        "开源": "open source",
        "路由器": "router",
        "浏览器": "browser",
        "代码": "programming code",
        "开发者": "programmer",
        "视频": "video production",
    }
    for cn, en in keywords.items():
        if cn in line:
            return en
    return "technology"


# ════════════════════════════════════════════════════════
# 2. TTS 配音
# ════════════════════════════════════════════════════════

def generate_voiceover(segments: list[dict], output_dir: str) -> list[dict]:
    """
    使用 Fish Audio 免费 TTS 生成配音
    备用方案: edge-tts (完全免费，音质稍差)
    """
    audio_dir = Path(output_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    for i, seg in enumerate(segments):
        audio_path = audio_dir / f"seg_{i:03d}.mp3"
        
        if FISH_AUDIO_KEY:
            # Fish Audio（免费，音质好，中文自然）
            _fish_tts(seg["text"], str(audio_path))
        else:
            # edge-tts 兜底（完全免费，稍机械）
            _edge_tts(seg["text"], str(audio_path))
        
        # 获取实际时长，覆盖估值
        from moviepy import AudioFileClip
        try:
            clip = AudioFileClip(str(audio_path))
            seg["duration"] = clip.duration
            clip.close()
        except:
            pass
        
        seg["audio_path"] = str(audio_path)
    
    return segments


def _edge_tts(text: str, output: str):
    """微软免费 TTS"""
    import edge_tts
    import asyncio
    asyncio.run(
        edge_tts.Communicate(
            text,
            voice="zh-CN-XiaoxiaoNeural"  # 中文女声
        ).save(output)
    )


def _fish_tts(text: str, output: str):
    """Fish Audio TTS (免费, 音质更好)"""
    if not FISH_AUDIO_KEY:
        return _edge_tts(text, output)
    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "text": text,
        "model": "speech-2.5",
        "voice": "Dongdong",  # 免费中文音色
        "format": "mp3",
    }
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    if resp.status_code == 200:
        with open(output, "wb") as f:
            f.write(resp.content)
    else:
        _edge_tts(text, output)


# ════════════════════════════════════════════════════════
# 3. B-roll 素材获取
# ════════════════════════════════════════════════════════

def fetch_broll(keyword: str, output_dir: str, count: int = 3) -> list[str]:
    """
    从 Pexels 免费图库获取 B-roll 画面
    免费 API: 每天 200 次请求
    """
    if not PEXELS_API_KEY:
        return []
    
    video_dir = Path(output_dir) / "broll"
    video_dir.mkdir(parents=True, exist_ok=True)
    
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page={count}&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        paths = []
        for video in data.get("videos", [])[:count]:
            for file in video.get("video_files", []):
                if file.get("quality") == "hd" and file.get("width", 0) <= 1920:
                    # 下载视频片段
                    vresp = requests.get(file["link"], timeout=30)
                    vpath = video_dir / f"{keyword}_{len(paths)}.mp4"
                    with open(vpath, "wb") as f:
                        f.write(vresp.content)
                    paths.append(str(vpath))
                    break
        return paths
    except:
        return []


# ════════════════════════════════════════════════════════
# 4. 视频合成
# ════════════════════════════════════════════════════════

def compose_video(segments: list[dict], output: str, work_dir: str):
    """把配音 + 画面 + 字幕合成最终视频"""
    clips = []
    
    for i, seg in enumerate(segments):
        # 背景画面
        if seg.get("broll_paths"):
            # 用 B-roll 作背景
            bg = VideoFileClip(seg["broll_paths"][0])
            bg = bg.resized((VIDEO_WIDTH, VIDEO_HEIGHT)).looped(duration=seg["duration"])
        else:
            # 渐变背景
            bg = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=_get_gradient_color(i),
                duration=seg["duration"],
            )
        
        # 配音
        audio = AudioFileClip(seg["audio_path"])
        
        # 字幕（分两行显示，适配手机观看）
        txt = _make_caption(seg["text"])
        
        # 合成
        clip = CompositeVideoClip([bg, txt], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        clip = clip.with_audio(audio).with_duration(seg["duration"])
        clips.append(clip)
    
    # 拼接
    final = concatenate_videoclips(clips, method="compose")
    
    # 添加背景音乐（可选）
    # bgm = AudioFileClip("bgm.mp3").with_duration(final.duration).with_effects([afx.MultiplyVolume(0.15)])
    # final = final.with_audio(CompositeAudioClip([final.audio, bgm]))
    
    # 输出
    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )
    final.close()
    
    return output


def _make_caption(text: str, max_chars: int = 15):
    """生成美观的字幕"""
    # 分行
    lines = []
    while len(text) > max_chars:
        # 在最后一个空格或标点处切分
        split = max_chars
        for i in range(max_chars, 0, -1):
            if text[i] in " ,，、 ":
                split = i
                break
        lines.append(text[:split].strip())
        text = text[split:].strip()
    if text:
        lines.append(text)
    
    display_text = "\n".join(lines)
    
    return TextClip(
        text=display_text,
        font=FONT_PATH,
        font_size=52,
        color="white",
        stroke_color="black",
        stroke_width=2,
        text_align="center",
        method="caption",
        size=(VIDEO_WIDTH - 100, None),
    ).with_position(("center", VIDEO_HEIGHT * 0.75))


def _get_gradient_color(index: int) -> tuple:
    """根据不同段落返回不同背景色 (RGB)"""
    colors = [(26, 26, 46), (22, 33, 62), (15, 52, 96), (83, 52, 131), (45, 52, 54), (99, 110, 114)]
    return colors[index % len(colors)]


# ════════════════════════════════════════════════════════
# 5. 一键入口
# ════════════════════════════════════════════════════════

def script_to_video(
    script_text: str,
    output: str = "output.mp4",
    work_dir: Optional[str] = None,
) -> str:
    """短视频脚本 → 完整视频"""
    if not work_dir:
        work_dir = tempfile.mkdtemp(prefix="ai_video_")
    
    print("📄 解析脚本...")
    segments = parse_script(script_text)
    print(f"   → {len(segments)} 个片段")
    
    print("🎙️ 生成配音...")
    segments = generate_voiceover(segments, work_dir)
    
    print("🖼️ 获取 B-roll 素材...")
    for seg in segments:
        seg["broll_paths"] = fetch_broll(seg["visual_hint"], work_dir)
    used_broll = sum(1 for s in segments if s.get("broll_paths"))
    print(f"   → {used_broll}/{len(segments)} 个片段有配图")
    
    print("🎬 合成视频...")
    result = compose_video(segments, output, work_dir)
    print(f"\n✅ 视频已生成: {result}")
    
    return result


if __name__ == "__main__":
    # 测试：用我们之前写的视频脚本
    test_script = """
    开头5秒钩子：
    76,264 颗星。18 天。一个让 AI agent 偷懒的项目。
    
    核心内容：
    不是 Copilot，不是 Cursor。这是 2026 年 7 月 GitHub 上最火的仓库。
    
    结尾：
    我是 AI 热点观察。点赞关注，下期见。
    """
    script_to_video(test_script, "demo.mp4")
