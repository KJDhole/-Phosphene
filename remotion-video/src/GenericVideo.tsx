import {
  AbsoluteFill,
  Audio,
  Easing,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";

export interface SceneData {
  id: number;
  name: string;
  lines: string[];
  visualType: "explode" | "number" | "text" | "pop" | "tag" | "chain" | "ending";
  gradient: string;
  layout?: "hook" | "fact_card" | "explain" | "analogy" | "quote" | "process" | "ending";
}

interface AssetData {
  kind: "stock_video" | "motion_graphic" | "infographic";
  file_name?: string;
}

export interface VideoProps {
  slug: string;
  title: string;
  category: string;
  scenes: SceneData[];
  audioFiles: string[];
  audioFrames: number[];
  assets: AssetData[];
}

const COLORS: Record<string, [string, string]> = {
  tech: ["#5B5CE2", "#00D4FF"],
  finance: ["#F59E0B", "#EF4444"],
  business: ["#0EA5E9", "#14B8A6"],
  literature: ["#C2410C", "#F59E0B"],
};

const sceneStarts = (frames: number[]) => {
  let cursor = 0;
  return frames.map((duration) => {
    const start = cursor;
    cursor += duration;
    return start;
  });
};

const SceneBackground: React.FC<{asset?: AssetData; colors: [string, string]}> = ({asset, colors}) => {
  if (asset?.kind === "stock_video" && asset.file_name) {
    return <OffthreadVideo src={staticFile(asset.file_name)} style={{width: "100%", height: "100%", objectFit: "cover", opacity: 0.54}} />;
  }
  return <AbsoluteFill style={{background: `radial-gradient(circle at 18% 20%, ${colors[0]}88, transparent 40%), radial-gradient(circle at 84% 76%, ${colors[1]}66, transparent 42%), #090B14`}} />;
};

const Kicker: React.FC<{scene: SceneData; index: number; colors: [string, string]}> = ({scene, index, colors}) => (
  <div style={{position: "absolute", top: 116, left: 76, right: 76, color: "#ffffffb8", fontSize: 28, letterSpacing: 3, fontWeight: 700}}>
    <span style={{color: colors[1]}}>{String(index + 1).padStart(2, "0")}</span> / {scene.name}
  </div>
);

const SceneText: React.FC<{scene: SceneData; frame: number; duration: number; colors: [string, string]}> = ({scene, frame, duration, colors}) => {
  const opacity = interpolate(frame, [0, 9, duration - 8, duration], [0, 1, 1, 0], {extrapolateRight: "clamp", easing: Easing.out(Easing.cubic)});
  const lift = interpolate(frame, [0, 16], [46, 0], {extrapolateRight: "clamp", easing: Easing.out(Easing.cubic)});
  const headline = scene.lines[0] || scene.name;
  const detail = scene.lines.slice(1);
  const layout = scene.layout || "explain";
  const fact = layout === "fact_card";
  const quote = layout === "quote";
  return <div style={{position: "absolute", left: 76, right: 76, bottom: layout === "ending" ? 270 : 250, opacity, transform: `translateY(${lift}px)`}}>
    {quote && <div style={{fontSize: 112, color: colors[1], lineHeight: 0.7}}>“</div>}
    <div style={{fontSize: fact ? 116 : quote ? 76 : 82, fontWeight: 800, color: "white", letterSpacing: -3, lineHeight: 1.16, textShadow: "0 8px 28px rgba(0,0,0,.42)"}}>{headline}</div>
    {detail.map((line, index) => <div key={index} style={{marginTop: 22, fontSize: 42, fontWeight: 600, color: "#F3F4F6", lineHeight: 1.35}}>{line}</div>)}
    {layout === "process" && <div style={{display: "flex", gap: 14, marginTop: 42}}>{[0, 1, 2].map((step) => <div key={step} style={{width: 74, height: 10, borderRadius: 99, background: step === 1 ? colors[1] : "#ffffff55"}} />)}</div>}
  </div>;
};

const SceneRenderer: React.FC<{scene: SceneData; asset?: AssetData; frame: number; duration: number; index: number; colors: [string, string]}> = ({scene, asset, frame, duration, index, colors}) => (
  <AbsoluteFill style={{overflow: "hidden"}}>
    <SceneBackground asset={asset} colors={colors} />
    <AbsoluteFill style={{background: "linear-gradient(180deg, rgba(6,8,15,.18), rgba(6,8,15,.2) 45%, rgba(6,8,15,.9))"}} />
    <Kicker scene={scene} index={index} colors={colors} />
    <SceneText scene={scene} frame={frame} duration={duration} colors={colors} />
    <div style={{position: "absolute", left: 76, right: 76, bottom: 110, height: 5, background: "#ffffff2e", borderRadius: 9}}><div style={{height: "100%", borderRadius: 9, width: `${interpolate(frame, [0, duration], [0, 100], {extrapolateRight: "clamp"})}%`, background: colors[1]}} /></div>
  </AbsoluteFill>
);

export const GenericVideo: React.FC<Record<string, unknown>> = (rawProps) => {
  const props = rawProps as unknown as VideoProps;
  const frame = useCurrentFrame();
  const starts = sceneStarts(props.audioFrames);
  const colors = COLORS[props.category] || COLORS.tech;
  return <AbsoluteFill style={{background: "#090B14", overflow: "hidden"}}>
    {props.audioFiles[0] && <Audio src={staticFile(props.audioFiles[0])} />}
    {props.scenes.map((scene, index) => <Sequence key={scene.id} from={starts[index]} durationInFrames={props.audioFrames[index]}>
      <SceneRenderer scene={scene} asset={props.assets[index]} index={index} frame={frame - starts[index]} duration={props.audioFrames[index]} colors={colors} />
    </Sequence>)}
  </AbsoluteFill>;
};
