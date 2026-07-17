# Remotion 短视频模版 — 风格指南 & 复刻规范

> 目标：任何 AI 拿到这份文档，都能零基础复刻出 8/10 分的科技短视频（1920×1080, 30fps, 中文配音）
>
> **核心理念：** 钩子 → 主题 → 解释 → 类比 → 金句 → 展开 → 升华 → 收尾（共 8 场）
>
> **渲染引擎：Remotion**（React + TypeScript，逐帧精确控制）

---

## 一、项目结构

```
remotion-video/
├── src/
│   ├── Root.tsx              # 注册 composition（分辨率/帧数/时长）
│   ├── Composition.tsx       # 230+ 行，全部视频逻辑
│   └── index.css             # Inter 字体导入
├── public/
│   ├── audio_00.mp3 ~ 07.mp3 # 8 段配音
│   └── scenes/               # （可选）截图素材
├── package.json
└── tsconfig.json
```

### 1.1 Root.tsx 模板

```tsx
import { Composition } from "remotion";
import { MyComposition } from "./Composition";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="项目名"
      component={MyComposition}
      durationInFrames={总帧数}       // = 8段音频帧数之和
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
```

---

## 二、Composition.tsx 结构骨架

```
1. 定义 AS[] = 每段音频的 { file, frames }          ← 精确帧数
2. 根据 AS 计算 SCENE[] = { start, frames }         ← 累加起始帧
3. 定义颜色、缓动工具、样式工具                    ← 视觉系统
4. 定义 8 个场景组件：S0 ~ S7                      ← 每个接收 { f, dur }
5. 主组件 = AbsoluteFill(背景层) + Sequence × 8     ← 渲染入口
```

### 2.1 音频同步（核心！最容易出错的地方）

```tsx
// 1. 精确测量每段音频的帧数
const AS = [
  { file: "audio_00.mp3", frames: 87 },   // 2.90s × 30
  { file: "audio_01.mp3", frames: 171 },  // 5.71s × 30
  // ...共 8 段
];

// 2. 自动累加起始帧
const SCENE: { start: number; frames: number }[] = [];
let acc = 0;
for (const a of AS) {
  SCENE.push({ start: acc, frames: a.frames });
  acc += a.frames;
}

// 3. Audio 放进 Sequence 内部（不要用全局 startFrom！）
<Sequence from={s.start} durationInFrames={s.frames}>
  <Audio src={staticFile(AS[i].file)} />
  {场景组件}
</Sequence>
```

**测量音频帧数的方法：**
```bash
python -c "
from moviepy import AudioFileClip
for i in range(8):
    c = AudioFileClip(f'public/audio_{i:02d}.mp3')
    frames = round(c.duration * 30)
    print(f'audio_{i:02d}: {c.duration:.2f}s = {frames} frames')
    c.close()
"
```

---

## 三、动画规则（核心！防抖动）

### 3.1 ❌ 禁止：spring()

```tsx
// spring() 会产生物理过冲，肉眼可见文字抖动（damping 再高也没用）
spring({ frame: f, fps: 30, config: { damping: 12 } })  // ← 永远不要用
```

### 3.2 ✅ 必须用：interpolate() + Easing

```tsx
import { interpolate, Easing } from "remotion";
const easeOut = Easing.out(Easing.ease);         // 缓出（最常用）
const easeBack = Easing.out(Easing.back(0.6));   // 一次弹入（不回弹）

// 1. 上滑淡入（90% 的场景用这个）
const smoothIn = (f: number, delay = 0, duration = 20) => ({
  opacity: interpolate(f, [delay, delay + duration * 0.5], [0, 1],
    { extrapolateRight: "clamp", easing: easeOut }),
  transform: `translateY(${interpolate(f, [delay, delay + duration], [24, 0],
    { extrapolateRight: "clamp", easing: easeOut })}px)`,
});

// 2. 弹性弹入（关键词/标签用这个，一次过冲不抖）
const popIn = (f: number, delay = 0) => ({
  opacity: interpolate(f, [delay, delay + 10], [0, 1],
    { extrapolateRight: "clamp" }),
  transform: `scale(${interpolate(f, [delay, delay + 18], [1.3, 1],
    { extrapolateRight: "clamp", easing: easeBack })})`,
});

// 3. 爆炸开场（S0 专用）
const explode = (f: number, delay = 0) => ({
  opacity: interpolate(f, [delay, delay + 15], [0, 1],
    { extrapolateRight: "clamp", easing: easeOut }),
  transform: `scale(${interpolate(f, [delay, delay + 15], [1.5, 1],
    { extrapolateRight: "clamp", easing: easeOut })})`,
  filter: `blur(${interpolate(f, [delay, delay + 15], [8, 0],
    { extrapolateRight: "clamp" })}px)`,
});
```

**⚠️ 每条 interpolate 必须加 `extrapolateRight: "clamp"`**，否则动画结束后会反向延伸（数字滑入后又滑出）。

### 3.3 延时常数

```
一行内多个元素 → delay 依次 +0.15~0.25s
跨行元素       → delay 依次 +0.3~0.5s
druation 参数  → 上滑 20, 淡入 10, 爆炸 15, 弹入 18
```

### 3.4 场景过渡

每个场景最后 8 帧加淡出，防止硬切：

```tsx
const fadeOut = (f: number, dur: number) => ({
  opacity: interpolate(f, [dur - 8, dur], [1, 0], { extrapolateRight: "clamp" }),
});

// 用法：每个场景 style={{ ...center, ...fadeOut(f, dur) }}
```

---

## 四、叙事结构（8 场景模板）

```
S0  💥  钩子（爆炸开场）        2-3s     先声夺人
S1  🔢  点名（数字+名称）       5-6s     让观众知道看到的是啥
S2  🤔  解释（它在干什么）      5-6s     一句话说明功能
S3  🧓  类比（比喻理解）        7-8s     用熟悉的概念类比
S4  💬  金句（一句话记住）      3-4s     可传播的短句
S5  📋  展开（不是孤例）        6-7s     提升话题格局
S6  🔗  升华（生态/影响）       4-5s     宏大图景
S7  🏁  收尾（总结+品牌）       8-9s     品牌露出 + "正在发生"
```

### 脚本写作规则

```
每段 ≤15 字中文（保证 1920×1080 单行显示）
总时长 ≈ 46 秒（8 段 × 平均 5.8s）
```

---

## 五、视觉设计系统

### 5.1 字号层级（1920×1080）

| 级别 | 字号 | 颜色 | 用途 |
|------|------|------|------|
| title-xxl | 90px | #fff | 重磅结论/主标题 |
| title-xl | 72px | #fff | 一般标题 |
| title-lg | 56px | 85%白 | 次级标题/类比 |
| title-md | 42px | 65%白 | 列表/过渡 |
| title-sm | 34px | 50%白 | 辅助说明 |
| 英文引用 | 22px | 25%白 | 斜体 |

### 5.2 渐变色系统

```tsx
const C = {
  bg: "#0a0a0f",
  a1: "linear-gradient(135deg, #818cf8, #c084fc)",        // 紫（主强调）
  a2: "linear-gradient(135deg, #a855f7, #f472b6)",        // 粉紫（次强调）
  a3: "linear-gradient(135deg, #6366f1, #a855f7)",        // 蓝紫（数字）
  // 结尾五彩: "linear-gradient(135deg, #818cf8, #c084fc, #f472b6)"
};
const gt = (g: string) => ({ background: g, backgroundClip: "text", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" });
```

### 5.3 背景

```tsx
<div style={{
  position: "absolute", inset: 0,
  background:
    "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(99,102,241,0.15) 0%, transparent 70%)," +
    "radial-gradient(ellipse 60% 50% at 30% 70%, rgba(168,85,247,0.10) 0%, transparent 60%)",
}} />
```

---

## 六、TTS 配音规范

### 工具
```bash
pip install edge-tts moviepy
```

### 生成
```python
import asyncio, edge_tts
scenes = ["句子1", ..., "句子8"]  # 每句 ≤15 字
async def g():
    for i,t in enumerate(scenes):
        await edge_tts.Communicate(t, voice='zh-CN-XiaoxiaoNeural').save(f'public/audio_{i:02d}.mp3')
asyncio.run(g())

# 测量帧数
from moviepy import AudioFileClip
total = 0
for i in range(8):
    c = AudioFileClip(f'public/audio_{i:02d}.mp3')
    frames = round(c.duration * 30)
    total += c.duration
    print(f'audio_{i:02d}: {c.duration:.2f}s = {frames}f')
print(f'总: {total:.2f}s = {round(total*30)}f')
```

**换文案后必须重新测量帧数，更新 AS[] 和 Root.tsx 的 durationInFrames。**

---

## 七、渲染命令

```bash
cd remotion-video
npm run dev                  # Studio 预览调试
npx remotion render src/index.ts 项目名 output.mp4   # 出片
```

首次搭建：
```bash
npx create-video@latest --blank remotion-video --yes
cd remotion-video
npm i
```

---

## 八、质量检查清单（渲染前必查）

| # | 检查项 |
|---|--------|
| 1 | 每段音频帧数 = `round(实际时长 × 30)`，AS 数组已更新 |
| 2 | 总帧数 = 8段帧数之和，Root.tsx 的 `durationInFrames` 已同步 |
| 3 | `SCENE` 数组由 AS 自动累加计算 |
| 4 | 所有 `interpolate` 有 `extrapolateRight: "clamp"` |
| 5 | 没有 `spring()` 用于文字（已经全部清除） |
| 6 | 每个场景最后有 `fadeOut(f, dur)` （最后 8 帧淡出） |
| 7 | Audio 放在 Sequence **内部**，不是全局 `startFrom` |
| 8 | 字体用 Inter（`@import url("https://fonts.googleapis.com/...")` 在 index.css） |
| 9 | `npm run dev` 能打开 Studio，无报错 |
| 10 | `npx tsc --noEmit` 零错误 |

---

## 九、常见问题

| 症状 | 原因 | 修法 |
|------|------|------|
| 文字抖动 | `spring()` 回弹过冲 | 全换成 `interpolate` + `easeOut` |
| 音频对不上 | `startFrom` 全局帧 + Sequence 累计误差 | Audio 放进 Sequence 内部 |
| 结尾被截断 | `durationInFrames` < 音频帧数之和 | 用 moviepy 测每段实际长度 |
| 数字滑入后又滑出 | `interpolate` 缺 `clamp` | 加 `extrapolateRight: "clamp"` |
| 画面硬切 | 缺淡出 | 每场景最后 8 帧加 `fadeOut` |
| 编译报错 | 未使用的 import / 变量 | `npx tsc --noEmit` 定位 |

---

## 十、参考成品

| 项目 | 位置 |
|------|------|
| 成品视频 | `remotion-video/ponytail_remotion.mp4` |
| 源码 | `remotion-video/src/Composition.tsx`（参考实现） |
| 音频 | `remotion-video/public/audio_*.mp3` |
| 历史 (HyperFrames) | `hyperframes-video/`（不再维护） |
