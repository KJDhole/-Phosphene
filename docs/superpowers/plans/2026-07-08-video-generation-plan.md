# Remotion 视频生成 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 ai-blog-factory 流水线中集成 Remotion 短视频生成，从标准化 video_script.md 渲染为 1920×1080 30fps MP4。

**Architecture:** Python 后端解析 video_script.md → edge-tts 生成 8 段配音 → Remotion CLI 渲染 → MP4 保存到文章目录。Remotion 组件通过 inputProps 接收动态场景数据。

**Tech Stack:** Python 3.10+, Remotion 4.0.486 (React/TypeScript), edge-tts, FastAPI, Ant Design

## Global Constraints
- Working directory: `D:/AI自动化/ai-blog-factory`
- Python 3.10+, Windows (Git Bash)
- Remotion 4.0.486 + React 19 + TypeScript 5.9
- 不修改 `categories/` 下的现有分类代码
- `video_script.md` 格式必须机器可解析

---

## File Structure

### 新建文件
| 文件 | 职责 |
|------|------|
| `core/video_generator.py` | 视频生成编排器：解析脚本 → TTS → 调用 Remotion → 保存结果 |
| `remotion-video/src/GenericVideo.tsx` | Remotion 通用组件，从 inputProps 读取场景动态渲染 |
| `web/routes/video.py` | 视频生成 API（触发/状态/下载/预留配置） |

### 修改文件
| 文件 | 改动 |
|------|------|
| `core/ai_client.py:103-111` | 重写 video_script 提示词，按分类差异化 |
| `remotion-video/src/Root.tsx` | 注册 GenericVideo composition |
| `remotion-video/src/index.ts` | 确保 import GenericVideo（通过 Root） |
| `web/models.py` | 添加 VideoStatus, VideoConfig 模型 |
| `web/routes/__init__.py` | import video 路由 |
| `config.yaml` | 添加 video 配置段 |
| `core/output.py` | index.md 添加 🎬 视频链接 |
| `frontend/src/pages/VideoEditor.tsx` | 从占位符改为完整功能 |
| `frontend/src/api/client.ts` | 添加视频 API 函数 |
| `main.py` | 添加 --generate-video CLI 参数 |

---

## Task 1: 优化 video_script AI 提示词

**Files:**
- Modify: `core/ai_client.py:103-111`（`generate_format` 方法中的 `"video_script"` 分支）

**Interfaces:**
- Consumes: `AIClient.generate_format(fmt, blog, category_display)` — 原有方法签名不变
- Produces: 按分类风格的结构化 `video_script.md`，Python 可解析

**详细说明：**
需要在 `generate_format` 方法中重写 `"video_script"` 分支的 system 和 user prompt。在 system prompt 中根据 `category_display` 参数选择合适的分类风格配置。需要定义 `STYLE_MAP` 字典在每个分类的 system prompt 中注入对应的视觉风格指令。

**`STYLE_MAP` 定义（放在 `generate_format` 方法上方或模块顶部）：**

```python
CATEGORY_STYLES = {
    "技术趋势": {
        "vibe": "科技感、紫蓝渐变、数字爆炸",
        "scene_names": ["爆火", "数据", "原理", "比喻", "金句", "生态", "格局", "未来"],
        "gradient": "a1",
    },
    "金融财经": {
        "vibe": "专业财经、金橙渐变、K线数据",
        "scene_names": ["核爆", "数字", "机制", "类比", "金句", "连锁", "影响", "机会"],
        "gradient": "a2",
    },
    "商业": {
        "vibe": "商业简洁、蓝青渐变、趋势结构",
        "scene_names": ["趋势", "数据", "结构", "类比", "金句", "版图", "格局", "展望"],
        "gradient": "a3",
    },
    "娱乐文化": {
        "vibe": "活泼炫彩、粉紫渐变、流行感",
        "scene_names": ["爆款", "热搜", "解读", "类比", "金句", "潮流", "趋势", "下期"],
        "gradient": "a4",
    },
    "文学艺术": {
        "vibe": "文艺优雅、暖棕渐变、文字意境",
        "scene_names": ["灵感", "作品", "解读", "类比", "金句", "群像", "意义", "回响"],
        "gradient": "a5",
    },
    "国际新闻": {
        "vibe": "新闻权威、深蓝渐变、数据格局",
        "scene_names": ["重磅", "数字", "背景", "类比", "金句", "连锁", "影响", "展望"],
        "gradient": "a6",
    },
    "中医中药": {
        "vibe": "传统自然、翠绿渐变、典雅智慧",
        "scene_names": ["典籍", "方剂", "机理", "类比", "金句", "传承", "价值", "结语"],
        "gradient": "a7",
    },
}
```

- [ ] **Step 1: 修改 `ai_client.py` — 添加 `CATEGORY_STYLES` 和重写 `video_script` prompt**

在 `core/ai_client.py` 中，定位 `generate_format` 方法（约 line 79-128）。在方法内部 `prompts` 字典中找到 `"video_script"` 分支（line 103-111），替换为以下代码：

```python
"video_script": (
    # System prompt: 根据分类注入风格
    self._video_script_system(category_display),
    # User prompt: 结构化输出要求
    self._video_script_user(blog, category_display),
),
```

然后在 `AIClient` 类中添加两个辅助方法：

```python
CATEGORY_STYLES = {
    "技术趋势": {"vibe":"科技感、紫蓝渐变、数字爆炸", "gradient":"a1"},
    "金融财经": {"vibe":"专业财经、金橙渐变、K线数据", "gradient":"a2"},
    "商业": {"vibe":"商业简洁、蓝青渐变、趋势结构", "gradient":"a3"},
    "娱乐文化": {"vibe":"活泼炫彩、粉紫渐变、流行感", "gradient":"a4"},
    "文学艺术": {"vibe":"文艺优雅、暖棕渐变、文字意境", "gradient":"a5"},
    "国际新闻": {"vibe":"新闻权威、深蓝渐变、数据格局", "gradient":"a6"},
    "中医中药": {"vibe":"传统自然、翠绿渐变、典雅智慧", "gradient":"a7"},
}

def _video_script_system(self, category_display: str) -> str:
    style = self.CATEGORY_STYLES.get(category_display, self.CATEGORY_STYLES["技术趋势"])
    return f"""你是短视频内容策划专家，擅长制作高质量的 8 场景短视频。

当前分类：{category_display}
视频风格：{style['vibe']}
渐变色：{style['gradient']}

你的输出必须严格按照以下格式，每场景一行，用 | 分隔字段。"""

def _video_script_user(self, blog: str, category_display: str) -> str:
    style = self.CATEGORY_STYLES.get(category_display, self.CATEGORY_STYLES["技术趋势"])
    gradient = style["gradient"]
    return f"""将以下关于「{category_display}」的文章改写为「8 场景短视频脚本」，格式如下：

## S0 | 场景名称 | 视觉类型 | {gradient}
文案：第一行
       第二行（可选）

## S1 | 场景名称 | 视觉类型 | {gradient}
文案：第一行
...

【叙事顺序】（固定，不可改变）：
S0 钩子 — S1 点名 — S2 解释 — S3 类比 — S4 金句 — S5 展开 — S6 升华 — S7 收尾

【视觉类型】（从以下选择）：
- explode：爆炸开场，放大+模糊消散
- number：数字/数据，左右分屏对撞
- text：纯文字上滑淡入
- pop：关键词弹性弹入
- tag：多标签逐个弹出
- chain：链条式递进
- ending：五彩渐变结尾

【规范】
1. 每行文案 ≤15 个中文字符
2. 不写"画面建议""口播"等舞台指示，只写最终屏幕显示的文字
3. 复杂场景可拆 2-3 行（每行单独显示）
4. 视觉类型根据场景内容选择最合适的

风格提示：{style['vibe']}

文章：
{blog[:3000]}"""
```

- [ ] **Step 2: 验证 Python 语法**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "from core.ai_client import AIClient; print('OK - import success')"
```

Expected: `OK - import success`

---

## Task 2: 创建 GenericVideo Remotion 组件

**Files:**
- Create: `remotion-video/src/GenericVideo.tsx`
- Modify: `remotion-video/src/Root.tsx`
- Modify: `remotion-video/src/index.ts`

**Interfaces:**
- Produces: 从 inputProps 接收动态场景数据的通用 Remotion composition

- [ ] **Step 1: 创建 `GenericVideo.tsx`**

```typescript
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
  staticFile,
  Sequence,
  Easing,
} from "remotion";

/* ── 7 套分类渐变色 ── */
const GRADIENTS: Record<string, string> = {
  a1: "linear-gradient(135deg, #818cf8, #c084fc)",   // 紫（tech）
  a2: "linear-gradient(135deg, #f59e0b, #ef4444)",   // 金橙（finance）
  a3: "linear-gradient(135deg, #3b82f6, #14b8a6)",   // 蓝青（business）
  a4: "linear-gradient(135deg, #ec4899, #8b5cf6)",   // 粉紫（entertainment）
  a5: "linear-gradient(135deg, #d97706, #b45309)",   // 暖棕（literature）
  a6: "linear-gradient(135deg, #1e40af, #3b82f6)",   // 深蓝（world）
  a7: "linear-gradient(135deg, #059669, #10b981)",   // 翠绿（zhongyi）
};

/* ── InputProps 类型 ── */
export interface SceneData {
  id: number;
  name: string;
  lines: string[];
  visualType: "explode" | "number" | "text" | "pop" | "tag" | "chain" | "ending";
  gradient: string;
}

export interface VideoProps {
  slug: string;
  category: string;
  title: string;
  scenes: SceneData[];
  audioFiles: string[];
  audioFrames: number[];
  totalFrames: number;
}

/* ── 缓动工具 ── */
const easeOut = Easing.out(Easing.ease);
const easeBack = Easing.out(Easing.back(0.6));

/* ── 样式工具 ── */
const center: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: 80,
};

const ts = (
  size: number,
  color = "#ffffff",
  extra: React.CSSProperties = {}
): React.CSSProperties => ({
  fontFamily: "'Inter', sans-serif",
  fontWeight: 700,
  fontSize: size,
  color,
  textAlign: "center",
  lineHeight: 1.3,
  letterSpacing: "-0.02em",
  ...extra,
});

const gt = (g: string): React.CSSProperties => ({
  background: g,
  backgroundClip: "text",
  WebkitBackgroundClip: "text",
  WebkitTextFillColor: "transparent",
});

/* ── 基础动画函数 ── */
const fadeOut = (f: number, dur: number) => ({
  opacity: interpolate(f, [dur - 8, dur], [1, 0], {
    extrapolateRight: "clamp",
  }),
});

const smoothIn = (f: number, delay = 0, duration = 20) => ({
  opacity: interpolate(f, [delay, delay + duration * 0.5], [0, 1], {
    extrapolateRight: "clamp",
    easing: easeOut,
  }),
  transform: `translateY(${interpolate(
    f,
    [delay, delay + duration],
    [24, 0],
    { extrapolateRight: "clamp", easing: easeOut }
  )}px)`,
});

const popIn = (f: number, delay = 0) => ({
  opacity: interpolate(f, [delay, delay + 10], [0, 1], {
    extrapolateRight: "clamp",
  }),
  transform: `scale(${interpolate(f, [delay, delay + 18], [1.3, 1], {
    extrapolateRight: "clamp",
    easing: easeBack,
  })})`,
});

const explodeIn = (f: number, delay = 0) => ({
  opacity: interpolate(f, [delay, delay + 15], [0, 1], {
    extrapolateRight: "clamp",
    easing: easeOut,
  }),
  transform: `scale(${interpolate(f, [delay, delay + 15], [1.5, 1], {
    extrapolateRight: "clamp",
    easing: easeOut,
  })})`,
  filter: `blur(${interpolate(f, [delay, delay + 15], [8, 0], {
    extrapolateRight: "clamp",
  })}px)`,
});

/* ── 场景渲染器 ── */
const renderScene = (
  scene: SceneData,
  f: number,
  dur: number
): React.CSSProperties[] => {
  const base = fadeOut(f, dur);
  const delayPerLine = 8;
  switch (scene.visualType) {
    case "explode":
      return scene.lines.map((_, i) => ({
        ...base,
        ...explodeIn(f, i * delayPerLine),
      }));
    case "number":
      return scene.lines.map((_, i) => ({
        ...base,
        ...popIn(f, i * delayPerLine),
      }));
    case "pop":
      return scene.lines.map((_, i) => ({
        ...base,
        ...popIn(f, i * delayPerLine),
      }));
    case "tag":
      return scene.lines.map((_, i) => ({
        ...base,
        ...popIn(f, i * 6),
      }));
    case "chain":
      return scene.lines.map((_, i) => ({
        ...base,
        ...smoothIn(f, i * 6, 12),
      }));
    case "ending":
      return scene.lines.map((_, i) => ({
        ...base,
        ...smoothIn(f, i * 10, 20),
      }));
    case "text":
    default:
      return scene.lines.map((_, i) => ({
        ...base,
        ...smoothIn(f, i * delayPerLine),
      }));
  }
};

/* ── 场景组件 ── */
const SceneRenderer = ({
  scene,
  f,
  dur,
}: {
  scene: SceneData;
  f: number;
  dur: number;
}) => {
  const styles = renderScene(scene, f, dur);
  const grad = GRADIENTS[scene.gradient] || GRADIENTS["a1"];

  return (
    <div style={{ ...center, ...fadeOut(f, dur) }}>
      {scene.lines.map((line, i) => {
        // 数字场景第一个元素用渐变色
        const isFirst = i === 0;
        const isGradient =
          scene.visualType === "number" && isFirst;
        return (
          <div
            key={i}
            style={{
              ...ts(isGradient ? 90 : 56, isGradient ? undefined : "rgba(255,255,255,0.85)"),
              ...(isGradient ? gt(grad) : {}),
              marginBottom: 8,
              ...styles[i],
            }}
          >
            {line}
          </div>
        );
      })}
    </div>
  );
};

/* ═══ 主组件 ═══ */
export const GenericVideo: React.FC<VideoProps> = ({
  slug,
  scenes,
  audioFiles,
  audioFrames,
}) => {
  const frame = useCurrentFrame();

  // 计算场景起始帧
  let acc = 0;
  const sceneStarts = audioFrames.map((fr) => {
    const start = acc;
    acc += fr;
    return start;
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0f", overflow: "hidden" }}>
      {/* 背景光晕 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(99,102,241,0.15) 0%, transparent 70%)," +
            "radial-gradient(ellipse 60% 50% at 30% 70%, rgba(168,85,247,0.10) 0%, transparent 60%)",
        }}
      />

      {scenes.map((scene, i) => (
        <Sequence
          key={scene.id}
          from={sceneStarts[i]}
          durationInFrames={audioFrames[i]}
        >
          <Audio src={staticFile(audioFiles[i])} />
          <SceneRenderer
            scene={scene}
            f={frame - sceneStarts[i]}
            dur={audioFrames[i]}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 修改 `Root.tsx`**

```typescript
import "./index.css";
import { Composition } from "remotion";
import { MyComposition } from "./Composition";
import { GenericVideo } from "./GenericVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Ponytail"
        component={MyComposition}
        durationInFrames={1386}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="GenericVideo"
        component={GenericVideo}
        durationInFrames={1}    // 会被 inputProps 覆盖
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
```

注意：`GenericVideo` 的 `durationInFrames` 会被 inputProps 中的 `totalFrames` 覆盖。Remotion 4.x 支持由 `calculateMetadata` 或 inputProps 动态设置时长。如果 inputProps 包含 `totalFrames`，渲染时会自动使用该值。

- [ ] **Step 3: 确保 `index.ts` 已导入 Root**

`remotion-video/src/index.ts` 应该已经包含 `import { RemotionRoot } from "./Root";`，不需要修改。只需验证：

```bash
cd D:/AI自动化/ai-blog-factory/remotion-video
npx tsc --noEmit
```

Expected: 无输出（零错误）

---

## Task 3: 创建 video_generator.py

**Files:**
- Create: `core/video_generator.py`

**Interfaces:**
- Consumes: `parse_script(video_script_path) → scenes, style, category`
- Consumes: `generate_tts(scenes, slug, work_dir) → audio_files, audio_frames`
- Consumes: `render_video(slug, scenes, audio_files, audio_frames, output_path) → str`
- Produces: `generate_video(category, slug) → Path`（对外的唯一入口）

- [ ] **Step 1: 创建 `core/video_generator.py`**

```python
"""
Remotion 视频生成编排器

工作流：
  1. parse_script() — 解析 video_script.md 为 JSON 场景数据
  2. generate_tts() — edge-tts 生成 8 段配音，测量帧数
  3. render_video() — 调用 Remotion CLI 渲染
  4. save_result() — 拷贝 MP4 到文章目录，更新 index.md
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
    audio_files = []
    audio_frames = []
    
    for i, scene in enumerate(scenes):
        text = "，".join(scene["lines"])
        output = work_dir / f"{slug}_audio_{i:02d}.mp3"
        
        # 调用 edge-tts
        import asyncio
        async def _gen():
            import edge_tts
            await edge_tts.Communicate(
                text, voice="zh-CN-XiaoxiaoNeural"
            ).save(str(output))
        
        asyncio.run(_gen())
        
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
    public_dir: Path,
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
    
    if len(scenes) != 8:
        raise ValueError(f"Expected 8 scenes, got {len(scenes)}")
    
    # 2. 创建临时工作目录
    with tempfile.TemporaryDirectory(prefix=f"video_{slug}_") as tmp_dir:
        work_dir = Path(tmp_dir)
        
        # 3. 生成 TTS
        audio_files, audio_frames = generate_tts(scenes, slug, work_dir)
        
        # 4. 拷贝音频到 Remotion public/
        public_dir = REMOTION_DIR / "public"
        for af in audio_files:
            shutil.copy2(work_dir / af, public_dir / af)
        
        try:
            # 5. 渲染视频
            tmp_output = work_dir / f"{slug}.mp4"
            render_video(
                slug, scenes, audio_files, audio_frames,
                public_dir, tmp_output,
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
```

- [ ] **Step 2: 验证 Python 语法**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "from core.video_generator import parse_script; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 测试 parse_script 解析**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "
from core.video_generator import parse_script
test = '''# 测试视频

> 分类：tech

## S0 | 爆火 | explode | a1
文案：GitHub 上突然
       炸了一个项目

## S1 | 数据 | number | a3
文案：18 天 76,264 颗星

## S7 | 未来 | ending | a1
文案：正在发生
'''
result = parse_script(test)
import json
print(json.dumps(result, ensure_ascii=False, indent=2))
print(f'Scenes count: {len(result[\"scenes\"])}')
"
```

Expected: 正确解析出 2 个场景（测试数据只有 S0 和 S7），title、category 正确。

---

## Task 4: 创建视频 API 路由

**Files:**
- Create: `web/routes/video.py`
- Modify: `web/models.py`（添加 VideoStatus, VideoConfig）
- Modify: `web/routes/__init__.py`（import video）
- Modify: `config.yaml`（添加 video 段）

- [ ] **Step 1: 添加 Pydantic 模型到 `web/models.py`**

在 `web/models.py` 末尾添加：

```python
from typing import Literal

class VideoStatus(BaseModel):
    slug: str
    status: Literal["pending", "generating", "done", "failed"] = "pending"
    progress: float = 0.0
    video_url: Optional[str] = None
    error: Optional[str] = None

class VideoConfig(BaseModel):
    """✅ 预留 — 下版本使用"""
    prompt_template: str = ""
    voice: str = "zh-CN-XiaoxiaoNeural"
    scene_overrides: dict = {}
```

- [ ] **Step 2: 创建 `web/routes/video.py`**

```python
"""视频生成 API — 触发/状态/下载/预留配置"""

import os
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from web.routes import router
from web.models import VideoStatus, VideoConfig
from main import ROOT, load_config

# 运行状态（进程内简单存储）
_generating: dict[str, VideoStatus] = {}

@router.get("/video/status/{slug}", response_model=VideoStatus)
def get_video_status(slug: str, category: Optional[str] = None):
    """查询视频生成状态"""
    # 如果已经生成完成，返回 done
    posts_dir = ROOT / "docs" / "posts"
    if category:
        video_path = posts_dir / category / slug / "video.mp4"
    else:
        # 在所有分类中搜索
        for cat_dir in posts_dir.iterdir():
            if cat_dir.is_dir():
                vp = cat_dir / slug / "video.mp4"
                if vp.exists():
                    video_path = vp
                    category = cat_dir.name
                    break
        else:
            video_path = None
    
    if slug in _generating:
        return _generating[slug]
    
    if video_path and video_path.exists():
        return VideoStatus(
            slug=slug,
            status="done",
            progress=1.0,
            video_url=f"/api/video/{slug}",
        )
    
    return VideoStatus(slug=slug, status="pending")


@router.get("/video/{slug}")
def get_video(slug: str, category: Optional[str] = None):
    """提供已生成的视频文件"""
    posts_dir = ROOT / "docs" / "posts"
    if category:
        video_path = posts_dir / category / slug / "video.mp4"
    else:
        for cat_dir in posts_dir.iterdir():
            if cat_dir.is_dir():
                vp = cat_dir / slug / "video.mp4"
                if vp.exists():
                    video_path = vp
                    break
        else:
            video_path = None
    
    if not video_path or not video_path.exists():
        raise HTTPException(404, "视频尚未生成")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"{slug}.mp4",
    )


@router.post("/video/generate/{slug}")
def generate_video(slug: str, category: str):
    """触发视频生成"""
    from core.video_generator import generate_video as _gen_video
    
    if slug in _generating and _generating[slug].status == "generating":
        raise HTTPException(400, "视频正在生成中")
    
    status = VideoStatus(slug=slug, status="generating")
    _generating[slug] = status
    
    try:
        posts_dir = ROOT / "docs" / "posts"
        result = _gen_video(category, slug, posts_dir)
        status.status = "done"
        status.progress = 1.0
        status.video_url = f"/api/video/{slug}"
    except Exception as e:
        status.status = "failed"
        status.error = str(e)
    
    return status


# ✅ 预留 — 下版本实现
@router.put("/video/{slug}/config")
def update_video_config(slug: str, config: VideoConfig):
    """更新单篇文章的视频配置（预留）"""
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.put("/video/config")
def update_global_video_config(config: VideoConfig):
    """更新全局视频配置（预留）"""
    raise HTTPException(501, "此功能将在 v2 版本中实现")


@router.get("/video/config")
def get_global_video_config():
    """获取全局视频配置（预留）"""
    cfg = load_config()
    video_cfg = cfg.get("video", {})
    return VideoConfig(
        prompt_template=video_cfg.get("prompt_template", ""),
        voice=video_cfg.get("audio_voice", "zh-CN-XiaoxiaoNeural"),
    )
```

- [ ] **Step 3: 修改 `web/routes/__init__.py`**

在最后添加：
```python
from . import video
```

- [ ] **Step 4: 修改 `config.yaml`**

末尾添加：
```yaml
# ---- 视频生成 ----
video:
  enabled: false                 # 默认关闭，手动触发
  audio_voice: "zh-CN-XiaoxiaoNeural"
  prompt_template: ""            # ✅ 预留：可 UI 编辑的 prompt 模板
```

- [ ] **Step 5: 验证路由导入**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "from web.routes.video import *; from web.models import VideoStatus; print('OK')"
```

Expected: `OK`

---

## Task 5: 更新前端

**Files:**
- Modify: `frontend/src/pages/VideoEditor.tsx` — 从占位符改为完整功能
- Modify: `frontend/src/api/client.ts` — 添加视频 API 函数

- [ ] **Step 1: 添加视频 API 到 `frontend/src/api/client.ts`**

末尾添加：
```typescript
export interface VideoStatusData {
  slug: string;
  status: 'pending' | 'generating' | 'done' | 'failed';
  progress: number;
  video_url: string | null;
  error: string | null;
}

export async function generateVideo(slug: string, category: string): Promise<VideoStatusData> {
  const res = await api.post<VideoStatusData>(`/video/generate/${slug}`, null, {
    params: { category },
  });
  return res.data;
}

export async function getVideoStatus(slug: string, category?: string): Promise<VideoStatusData> {
  const res = await api.get<VideoStatusData>(`/video/status/${slug}`, {
    params: category ? { category } : {},
  });
  return res.data;
}

export function getVideoUrl(slug: string, category?: string): string {
  const params = category ? `?category=${category}` : '';
  return `/api/video/${slug}${params}`;
}
```

- [ ] **Step 2: 重写 `frontend/src/pages/VideoEditor.tsx`**

```tsx
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  Button,
  Progress,
  Typography,
  Alert,
  Spin,
  Space,
  Divider,
} from 'antd';
import {
  PlayCircleOutlined,
  VideoCameraOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchArticleDetail, generateVideo, getVideoStatus, getVideoUrl } from '../api/client';

const { Title, Text, Paragraph } = Typography;

export default function VideoEditor() {
  const { id: slug } = useParams<{ id: string }>();
  const category = new URLSearchParams(window.location.search).get('category') || undefined;

  const [generating, setGenerating] = useState(false);
  const [polling, setPolling] = useState<ReturnType<typeof setInterval> | null>(null);

  // 获取文章详情
  const { data: article, isLoading: articleLoading } = useQuery({
    queryKey: ['article', slug, category],
    queryFn: () => fetchArticleDetail(slug!, category),
    enabled: !!slug,
  });

  // 获取视频状态
  const [videoStatus, setVideoStatus] = useState<any>(null);

  const doGenerate = async () => {
    if (!slug) return;
    setGenerating(true);
    try {
      const status = await generateVideo(slug, category || 'tech');
      setVideoStatus(status);
      // 开始轮询
      const timer = setInterval(async () => {
        try {
          const s = await getVideoStatus(slug, category);
          setVideoStatus(s);
          if (s.status === 'done' || s.status === 'failed') {
            clearInterval(timer);
            setPolling(null);
            setGenerating(false);
          }
        } catch { /* ignore */ }
      }, 2000);
      setPolling(timer);
    } catch (e: any) {
      setVideoStatus({ status: 'failed', error: e.message });
      setGenerating(false);
    }
  };

  useEffect(() => {
    return () => {
      if (polling) clearInterval(polling);
    };
  }, [polling]);

  const videoScript = article?.formats?.['video_script'] || '';

  return (
    <div>
      <Title level={4} style={{ fontWeight: 600 }}>
        🎬 视频生成
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginTop: 0 }}>视频脚本预览</Title>
        {articleLoading ? (
          <Spin />
        ) : videoScript ? (
          <pre style={{
            background: '#f8f7fc',
            padding: 16,
            borderRadius: 8,
            fontSize: 14,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            maxHeight: 400,
            overflow: 'auto',
          }}>
            {videoScript}
          </pre>
        ) : (
          <Text type="secondary">暂无视频脚本，请先生成文章</Text>
        )}
      </Card>

      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Button
            type="primary"
            icon={<VideoCameraOutlined />}
            size="large"
            onClick={doGenerate}
            loading={generating}
            disabled={!videoScript}
            style={{ borderRadius: 8, height: 44, paddingInline: 32 }}
          >
            {generating ? '生成中...' : '▶ 生成视频'}
          </Button>

          {videoStatus?.status === 'generating' && (
            <div>
              <Text>正在生成视频...</Text>
              <Progress
                percent={Math.round((videoStatus.progress || 0) * 100)}
                status="active"
                strokeColor="#7C3AED"
              />
            </div>
          )}

          {videoStatus?.status === 'done' && slug && (
            <div>
              <Alert
                type="success"
                message="视频生成完成！"
                showIcon
                style={{ borderRadius: 8, marginBottom: 12 }}
              />
              <video
                controls
                style={{
                  width: '100%',
                  maxHeight: 400,
                  borderRadius: 8,
                  background: '#000',
                }}
              >
                <source src={getVideoUrl(slug, category)} type="video/mp4" />
              </video>
            </div>
          )}

          {videoStatus?.status === 'failed' && (
            <Alert
              type="error"
              message="生成失败"
              description={videoStatus.error || '未知错误'}
              showIcon
              style={{ borderRadius: 8 }}
            />
          )}
        </Space>
      </Card>

      {/* ✅ 预留 — v2 配置编辑区 */}
      <Divider />
      <Card
        title="⚙️ 高级配置（下版本开放）"
        style={{ opacity: 0.5 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            📝 Prompt 编辑 — 可自定义视频脚本生成提示词
          </div>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            🔧 场景微调 — 可逐场景编辑文案、视觉类型、配色
          </div>
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: 16, textAlign: 'center', color: '#999' }}>
            🎚️ 流程配置 — 可设置默认配音、分辨率、帧率等参数
          </div>
        </Space>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: 验证前端编译**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: 无输出（零错误）

---

## Task 6: 集成到现有流水线

**Files:**
- Modify: `core/output.py`（index.md 添加 🎬 视频链接）
- Modify: `main.py`（添加 --generate-video CLI 参数）

- [ ] **Step 1: 修改 `core/output.py` 的 `update_index` 方法**

在 `entry_lines` 中添加视频链接行：

```python
# ≈ line 103-108
entry_lines = [
    f"- [**{title}**]({blog_link}) ({date_str})",
    f"  - 🐦 [推文串](posts/{self._rel_path('twitter.md')})"
    f" · 📧 [通讯](posts/{self._rel_path('newsletter.md')})"
    f" · 🎬 [脚本](posts/{self._rel_path('video_script.md')})"
    f" · 🌍 [English](posts/{self._rel_path('english.md')})",
    # 如果有视频，添加视频链接
    f"  - 🎥 [视频](posts/{self._rel_path('video.mp4')}) (如有)",
]
```

- [ ] **Step 2: 修改 `main.py` — 添加 `--generate-video` 命令**

在主函数的 argparse 中添加：

```python
# 在 parser 中添加
parser.add_argument("--generate-video", nargs=2, metavar=("CATEGORY", "SLUG"),
                    help="为指定文章生成 Remotion 视频")
```

在 `main()` 函数中添加处理：

```python
if args.generate_video:
    category, slug = args.generate_video
    from core.video_generator import generate_video
    from pathlib import Path
    result = generate_video(category, slug, ROOT / "docs" / "posts")
    CONSOLE.print(f"[green]✅ 视频已生成: {result}[/]")
    return
```

- [ ] **Step 3: 验证整体导入**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "
from core.video_generator import parse_script, generate_tts, render_video, generate_video
from web.routes.video import *
from web.models import VideoStatus, VideoConfig
print('All imports OK')
"
```

Expected: `All imports OK`

---

## Task 7: 端到端验证

- [ ] **Step 1: 验证 Remotion 零错误**

```bash
cd D:/AI自动化/ai-blog-factory/remotion-video
npx tsc --noEmit
```

- [ ] **Step 2: 验证 Python 全模块导入**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "
import sys
sys.path.insert(0, '.')
from core.video_generator import parse_script
from core.ai_client import AIClient
print('All OK')
"
```

- [ ] **Step 3: 验证前端编译**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npx tsc --noEmit 2>&1 | head -5
```

- [ ] **Step 4: 验证 Web 服务启动**

```bash
cd D:/AI自动化/ai-blog-factory
python -c "from web.server import create_app; app = create_app(); print('Web server OK')"
```

---

## 执行建议

推荐使用 **subagent-driven-development** 按以下顺序分包执行：

```
Task 1 (AI prompt)  →  独立可测
       ↓
Task 2 (Remotion)   →  独立可测，tsc 验证
       ↓
Task 3 (generator)  →  依赖 Task 2 定义的数据格式
       ↓
Task 4 (API)        →  依赖 Task 3
       ↓
Task 5 (Frontend)   →  依赖 Task 4
       ↓
Task 6 (Integration) →  最终胶合
       ↓
Task 7 (验证)        →  端到端
```

Task 1 和 Task 2 可以并行执行，其余顺序依赖。
