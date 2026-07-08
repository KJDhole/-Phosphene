# Remotion 视频生成功能 — 设计文档

> 版本：v1.0
> 日期：2026-07-08
> 状态：待实现

---

## 1. 概述

在现有的 AI 博客工厂流水线中，增加 Remotion 短视频生成能力。每篇文章生成后，可基于 `video_script.md` 自动渲染为 1920×1080 30fps 的 MP4 视频，遵循 STYLE_GUIDE.md 定义的 8 场景叙事结构和视觉规范。

### 1.1 目标

- 每个分类按自身调性生成不同风格的视频
- `video_script.md` 格式标准化，Python 可解析 → Remotion 可渲染
- Web UI 支持手动触发、进度查看、视频预览
- 预留 v2 配置调试接口（prompt 编辑、场景微调、流程配置）

---

## 2. video_script.md 格式规范

### 2.1 输出格式

AI 生成 `video_script.md` 时，必须输出以下结构化格式：

```markdown
# 视频脚本：{文章标题}

> 分类：{tech|finance|business|entertainment|literature|world|zhongyi}
> 风格：{分类对应的视觉描述}

## S0 | 💥 {场景名称} | {视觉类型} | {渐变色}
文案：xxx
       xxx

## S1 | 🔢 {场景名称} | {视觉类型} | {渐变色}
文案：xxx

...
```

### 2.2 8 场景叙事结构（固定顺序）

| # | 名称 | 作用 | 视觉类型 | 说明 |
|---|------|------|---------|------|
| S0 | 钩子 | 先声夺人 | `explode` | 爆炸开场，关键词放大出现 |
| S1 | 点名 | 数字+名称 | `number` | 关键数字对撞，让观众知道看到的是什么 |
| S2 | 解释 | 一句话说明功能 | `text` \| `pop` | 核心信息逐步弹出 |
| S3 | 类比 | 用熟悉概念理解 | `text` \| `pop` | 比喻对比，左右对照 |
| S4 | 金句 | 可传播短句 | `text` | 大标题居中，纯文字 |
| S5 | 展开 | 提升话题格局 | `pop` \| `tag` | 多个关键词标签云 |
| S6 | 升华 | 宏大图景 | `chain` | 链条式递进，生态感 |
| S7 | 收尾 | 品牌露出 | `ending` | 五彩渐变 + "正在发生" |

### 2.3 文案规范

- 每行文案 **≤15 个中文字符**（1920×1080 确保单行显示）
- 不写"画面建议"、"口播"等舞台指示
- 只写最终屏幕上显示的文字
- 复杂场景可拆为 2–3 行（换行用 `\n` 或另起一行）

### 2.4 视觉类型

| 类型 | 用途 | 动画效果 |
|------|------|---------|
| `explode` | 开场钩子 | 1.5x 放大 + 模糊消散 |
| `number` | 数字/数据 | 左右分屏 + 弹入 |
| `text` | 纯文字 | 上滑淡入 |
| `pop` | 关键词/标签 | 弹性弹入（一次过冲） |
| `chain` | 链条/生态 | 逐个滑入 + 箭头 |
| `tag` | 标签云 | 多标签逐个 pop |
| `ending` | 结尾 | 五彩渐变 + 慢淡入 |

---

## 3. 按分类的视觉系统

### 3.1 各分类配置

| 分类 | 调性 | 主色渐变 | 场景类型倾向 | 场景名称示例 |
|------|------|---------|-------------|-------------|
| 🔧 tech | 科技/硬核 | a1: `#818cf8→#c084fc` | explode, number, chain | 爆火 / 数据 / 技术生态 |
| 💰 finance | 专业/数据 | a2: `#f59e0b→#ef4444` | explode, number, pop | 数据爆发 / 涨跌 / 关键信号 |
| 🏢 business | 商业/简洁 | a3: `#3b82f6→#14b8a6` | text, pop, chain | 趋势 / 结构 / 商业版图 |
| 🎬 entertainment | 活泼/炫彩 | a4: `#ec4899→#8b5cf6` | pop, tag, text | 爆款 / 热搜 / 流行 |
| 📚 literature | 文艺/优雅 | a5: `#d97706→#b45309` | text, pop | 文字 / 意境 / 共鸣 |
| 🌐 world | 新闻/权威 | a6: `#1e40af→#3b82f6` | number, text, chain | 数据 / 格局 / 影响链 |
| 🌿 zhongyi | 传统/自然 | a7: `#059669→#10b981` | text, pop | 典籍 / 智慧 / 传承 |

### 3.2 AI Prompt 差异化

`generate_format("video_script", ...)` 的 prompt 中，根据 `category_display` 参数注入分类风格指令：

```python
STYLE_MAP = {
    "技术趋势": {
        "vibe": "科技感、紫蓝渐变、数字感",
        "scene_names": ["爆火", "数据", "原理", "比喻", "金句", "生态", "格局", "未来"],
    },
    "金融财经": {
        "vibe": "专业财经、金橙渐变、K线数据感",
        "scene_names": ["核爆", "数字", "机制", "类比", "金句", "连锁", "影响", "机会"],
    },
    # ... 每个分类映射
}
```

---

## 4. 系统架构

### 4.1 新增模块

```
core/video_generator.py          # 视频生成编排器
remotion-video/src/GenericVideo.tsx  # Remotion 通用组件
web/routes/video.py              # 视频 API
```

### 4.2 数据流

```
现有流水线结束
     │
     ▼ (可选触发)
┌─ core/video_generator.py ────────────────────────────┐
│                                                        │
│  ① parse_script(video_script.md) → SceneData[]        │
│     - 解析 S0|xxx|explode|a1 格式                      │
│     - 输出 JSON: {scenes: [...], style: "tech"}        │
│                                                        │
│  ② generate_tts(scenes, slug) → audio_files[]         │
│     - edge-tts 8 段 MP3                               │
│     - 测量帧数 round(duration × 30)                   │
│     - 写入 remotion-video/public/{slug}_audio_00~07   │
│                                                        │
│  ③ render_video(slug, scenes, audio_files) → MP4     │
│     - 构建 inputProps JSON                             │
│     - npx remotion render ... --props='{...}'          │
│     - 输出到临时目录                                   │
│                                                        │
│  ④ save_result(temp_mp4, category, slug) → Path       │
│     - 拷贝到 docs/posts/{cat}/{slug}/video.mp4         │
│     - 更新 index.md (添加 🎬 视频链接)                  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 4.3 Remotion 组件设计

**GenericVideo.tsx** — 通过 inputProps 接收场景数据，动态渲染：

```typescript
interface SceneData {
  id: number;
  name: string;        // 场景名称（仅用于调试）
  lines: string[];     // 文案行（每行 ≤15字）
  visualType: 'explode' | 'number' | 'text' | 'pop' | 'tag' | 'chain' | 'ending';
  gradient: string;    // 'a1' | 'a2' | ... | 'a7'
}

interface VideoProps {
  slug: string;
  category: string;
  title: string;
  scenes: SceneData[];
  audioFiles: string[];   // 8个文件名
  audioFrames: number[];  // 每段帧数
  totalFrames: number;
}
```

**Root.tsx** — 注册 GenericVideo composition，从 inputProps 读取数据。

### 4.4 色彩系统扩展

在 Composition.tsx / GenericVideo.tsx 中添加全部分类色系：

```typescript
const GRADIENTS: Record<string, string> = {
  a1: "linear-gradient(135deg, #818cf8, #c084fc)",   // 紫（tech）
  a2: "linear-gradient(135deg, #f59e0b, #ef4444)",   // 金橙（finance）
  a3: "linear-gradient(135deg, #3b82f6, #14b8a6)",   // 蓝青（business）
  a4: "linear-gradient(135deg, #ec4899, #8b5cf6)",   // 粉紫（entertainment）
  a5: "linear-gradient(135deg, #d97706, #b45309)",   // 暖棕（literature）
  a6: "linear-gradient(135deg, #1e40af, #3b82f6)",   // 深蓝（world）
  a7: "linear-gradient(135deg, #059669, #10b981)",   // 翠绿（zhongyi）
};
```

---

## 5. API 设计

### 5.1 新增端点

| 方法 | 路径 | 说明 | 预留 |
|------|------|------|------|
| `POST` | `/api/video/generate/{slug}` | 触发视频生成 | 本版本 |
| `GET` | `/api/video/status/{slug}` | 查询生成状态 | 本版本 |
| `GET` | `/api/video/{slug}` | 下载/播放已生成的视频 | 本版本 |
| `PUT` | `/api/video/{slug}/config` | 更新视频配置（prompt/场景） | ✅ 预留（下版本） |
| `PUT` | `/api/video/config` | 更新全局视频配置 | ✅ 预留（下版本） |

### 5.2 状态模型

```python
class VideoStatus(BaseModel):
    slug: str
    status: Literal["pending", "generating", "done", "failed"]
    progress: float  # 0-1
    video_url: Optional[str]
    error: Optional[str]
```

### 5.3 config.yaml 预留

```yaml
video:
  enabled: false               # 默认关闭，手动触发
  audio_voice: "zh-CN-XiaoxiaoNeural"
  prompt_template: ""          # ✅ 预留：可 UI 编辑的 prompt 模板
  # 下版本使用：
  # scene_editor: false        # 是否启用场景微调
  # workflow_presets: []       # 预设流程配置
```

---

## 6. 前端改动

### 6.1 VideoEditor 页面（本版本）

```
┌──────────────────────────────────────────┐
│ 🎬 视频生成                              │
│                                           │
│  ┌──────────────────────────────────┐    │
│  │  video_script.md 内容 (只读)      │    │
│  │  8 场景预览                       │    │
│  └──────────────────────────────────┘    │
│                                           │
│  [▶ 生成视频]  <- 触发按钮               │
│                                           │
│  进度条: ████████░░ 80%                  │
│  状态: 正在生成配音/正在渲染...           │
│                                           │
│  完成时: [▶ 播放视频]                     │
│                                           │
│  ─── 预留区 (下版本) ───                  │
│  📝 Prompt 编辑     🔧 场景微调          │
│  [下版本开放]        [下版本开放]          │
└──────────────────────────────────────────┘
```

### 6.2 API 客户端新增

```typescript
export async function generateVideo(slug: string, category?: string): Promise<void>
export async function getVideoStatus(slug: string): Promise<VideoStatus>
export function getVideoUrl(slug: string): string
```

---

## 7. 文件清单

### 新建文件

| # | 文件 | 说明 |
|---|------|------|
| 1 | `core/video_generator.py` | 视频生成编排器 (parse → tts → render → save) |
| 2 | `remotion-video/src/GenericVideo.tsx` | 通用组件，从 inputProps 读取场景 |
| 3 | `web/routes/video.py` | 视频 API 路由 |

### 修改文件

| # | 文件 | 改动 |
|---|------|------|
| 4 | `core/ai_client.py` | 重写 `video_script` 提示词，按分类差异化 |
| 5 | `remotion-video/src/Root.tsx` | 注册 GenericVideo composition |
| 6 | `remotion-video/src/index.ts` | 确保 GenericVideo 被导入 |
| 7 | `remotion-video/src/Composition.tsx` | 保留为参考，新增 GenericVideo.tsx |
| 8 | `web/models.py` | 添加 VideoStatus 模型 |
| 9 | `web/routes/__init__.py` | import video 路由 |
| 10 | `config.yaml` | 添加 video 配置段 |
| 11 | `core/output.py` | index.md 添加 🎬 视频链接 |
| 12 | `frontend/src/pages/VideoEditor.tsx` | 从占位符改为完整页面 |
| 13 | `frontend/src/api/client.ts` | 添加视频 API |
| 14 | `main.py` | 添加 --generate-video CLI 参数 |

---

## 8. 预留接口清单（下版本 v2）

以下位置已预留，当前版本只需确保数据模型和路由注册：

| 位置 | 预留内容 | 用途 |
|------|---------|------|
| `config.yaml` → `video.prompt_template` | 空字符串字段 | UI 可编辑的 prompt 模板 |
| `web/routes/video.py` | `PUT /api/video/{slug}/config` 路由已注册（返回 501） | 更新单篇文章视频配置 |
| `web/routes/video.py` | `PUT /api/video/config` 路由已注册（返回 501） | 更新全局视频配置 |
| `frontend/src/pages/VideoEditor.tsx` | 页面底部灰色占位区 | Prompt 编辑、场景微调面板 |
| `web/models.py` | `VideoConfig` 模型已定义 | 存储视频生成参数 |

---

## 9. 边界情况与错误处理

| 场景 | 处理 |
|------|------|
| video_script.md 不存在 | 返回 404 错误 |
| video_script.md 格式无法解析 | 返回格式错误信息，建议重新生成 |
| edge-tts 失败 | 重试 2 次，失败则返回 TTS 错误 |
| Remotion 渲染失败 | 捕获 stderr，返回渲染错误日志 |
| 临时文件残留 | 每次渲染后清理临时目录 |
| 并发生成请求 | 同一 slug 只允许一个生成任务 |
| 磁盘空间不足 | 渲染前检查可用空间 |
| Remotion 未安装 | 启动时检查 node_modules，缺失则提示安装 |
