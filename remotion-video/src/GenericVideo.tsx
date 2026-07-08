import {
  AbsoluteFill,
  useCurrentFrame,
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
export const GenericVideo: React.FC<Record<string, unknown>> = (props) => {
  const { scenes, audioFiles, audioFrames } = props as unknown as VideoProps;
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
