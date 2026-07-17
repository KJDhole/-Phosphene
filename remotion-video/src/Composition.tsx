import { AbsoluteFill, useCurrentFrame, interpolate, Audio, staticFile, Sequence, Easing } from "remotion";

/* ── 音频精确帧数 ── */
const AS = [
  { file: "audio_00.mp3", frames: 87 },
  { file: "audio_01.mp3", frames: 171 },
  { file: "audio_02.mp3", frames: 164 },
  { file: "audio_03.mp3", frames: 230 },
  { file: "audio_04.mp3", frames: 94 },
  { file: "audio_05.mp3", frames: 207 },
  { file: "audio_06.mp3", frames: 146 },
  { file: "audio_07.mp3", frames: 286 },
];

/* ── 场景起始帧（累加） ── */
const SCENE: { start: number; frames: number }[] = [];
let acc = 0;
for (const a of AS) { SCENE.push({ start: acc, frames: a.frames }); acc += a.frames; }

/* ── 颜色 ── */
const C = {
  bg: "#0a0a0f", white: "#ffffff", dim40: "rgba(255,255,255,0.4)",
  dim25: "rgba(255,255,255,0.25)", dim10: "rgba(255,255,255,0.10)",
  a1: "linear-gradient(135deg, #818cf8, #c084fc)",
  a2: "linear-gradient(135deg, #a855f7, #f472b6)",
  a3: "linear-gradient(135deg, #6366f1, #a855f7)",
};

/* ── 缓动工具 ── */
const easeOut = Easing.out(Easing.ease);
const easeBack = Easing.out(Easing.back(0.6));

/* ── 样式工具 ── */
const center: React.CSSProperties = {
  position: "absolute", inset: 0, display: "flex", flexDirection: "column",
  alignItems: "center", justifyContent: "center", padding: 80,
};

const ts = (size: number, color = C.white, extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: "'Inter', sans-serif", fontWeight: 700, fontSize: size, color, textAlign: "center",
  lineHeight: 1.3, letterSpacing: "-0.02em", ...extra,
});

const gt = (g: string): React.CSSProperties => ({
  background: g, backgroundClip: "text", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
});

/* ── 淡出（每个场景最后 8 帧） ── */
const fadeOut = (f: number, dur: number) => ({
  opacity: interpolate(f, [dur - 8, dur], [1, 0], { extrapolateRight: "clamp" }),
});

/* ── 平滑入场：上滑 + 弹性缓动（不抖动） ── */
const smoothIn = (f: number, delay = 0, duration = 20) => ({
  opacity: interpolate(f, [delay, delay + duration * 0.5], [0, 1], { extrapolateRight: "clamp", easing: easeOut }),
  transform: `translateY(${interpolate(f, [delay, delay + duration], [24, 0], { extrapolateRight: "clamp", easing: easeOut })}px)`,
});

/* ── 弹入（用 easing 实现一次过冲，不循环） ── */
const popIn = (f: number, delay = 0) => ({
  opacity: interpolate(f, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" }),
  transform: `scale(${interpolate(f, [delay, delay + 18], [1.3, 1], { extrapolateRight: "clamp", easing: easeBack })})`,
});

/* ═══ S0: 爆炸开场 ═══ */
const S0 = ({ f, dur }: { f: number; dur: number }) => {
  const b = (d: number) => ({
    opacity: interpolate(f, [d, d + 15], [0, 1], { extrapolateRight: "clamp", easing: easeOut }),
    transform: `scale(${interpolate(f, [d, d + 15], [1.5, 1], { extrapolateRight: "clamp", easing: easeOut })})`,
    filter: `blur(${interpolate(f, [d, d + 15], [8, 0], { extrapolateRight: "clamp" })}px)`,
  });
  return (
    <div style={{ ...center, ...fadeOut(f, dur) }}>
      <div style={{ ...ts(90), ...b(0) }}><span style={gt(C.a1)}>GitHub</span> 上突然</div>
      <div style={{ ...ts(90), ...b(8) }}>炸了一个项目</div>
    </div>
  );
};

/* ═══ S1: 数字对撞 ═══ */
const S1 = ({ f, dur }: { f: number; dur: number }) => (
  <div style={{ ...center, ...fadeOut(f, dur) }}>
    <div style={{ display: "flex", gap: 30, alignItems: "center" }}>
      <div style={{ textAlign: "center", ...smoothIn(f, 0, 18) }}>
        <div style={{ ...ts(90), ...gt(C.a2), lineHeight: 1 }}>18</div>
        <div style={{ fontSize: 26, color: C.dim40, marginTop: 2 }}>天</div>
      </div>
      <div style={{ ...ts(48), color: C.dim10, fontWeight: 200, ...smoothIn(f, 6, 12) }}>·</div>
      <div style={{ textAlign: "center", ...smoothIn(f, 0, 18) }}>
        <div style={{ ...ts(90), ...gt(C.a3), lineHeight: 1 }}>76,264</div>
        <div style={{ fontSize: 26, color: C.dim40, marginTop: 2 }}>⭐ 颗星</div>
      </div>
    </div>
    <div style={{ ...ts(56, C.dim40), marginTop: 24, ...popIn(f, 8) }}>它叫 <span style={gt(C.a1)}>Ponytail</span></div>
  </div>
);

/* ═══ S2: 三步解释 ═══ */
const S2 = ({ f, dur }: { f: number; dur: number }) => (
  <div style={{ ...center, ...fadeOut(f, dur) }}>
    <div style={{ ...ts(72), ...smoothIn(f, 0) }}>它让 AI 编程代理</div>
    <div style={{ marginTop: 10, display: "flex", gap: 20, alignItems: "center" }}>
      <span style={{ ...ts(72), ...gt(C.a1), ...popIn(f, 4) }}>先思考</span>
      <span style={{ ...ts(72), color: C.dim10, ...smoothIn(f, 12, 8) }}>·</span>
      <span style={{ ...ts(72), ...gt(C.a2), ...popIn(f, 14) }}>再判断</span>
      <span style={{ ...ts(72), color: C.dim10, ...smoothIn(f, 22, 8) }}>·</span>
      <span style={{ ...ts(72), ...popIn(f, 24) }}>最后才写代码</span>
    </div>
  </div>
);

/* ═══ S3: 80/20 ═══ */
const S3 = ({ f, dur }: { f: number; dur: number }) => (
  <div style={{ ...center, ...fadeOut(f, dur) }}>
    <div style={{ ...ts(56, C.dim40), ...smoothIn(f, 0) }}>
      像一个 <span style={gt(C.a1)}>老油条高级工程师</span>
    </div>
    <div style={{ display: "flex", gap: 40, marginTop: 24, alignItems: "center" }}>
      <div style={{ textAlign: "center", ...smoothIn(f, 10, 18) }}>
        <div style={{ ...ts(64), ...gt(C.a1), lineHeight: 1 }}>80%</div>
        <div style={{ fontSize: 28, color: C.dim40, marginTop: 4 }}>时间想清楚</div>
      </div>
      <div style={{ ...ts(40), color: C.dim10, fontWeight: 200, ...smoothIn(f, 22, 8) }}>→</div>
      <div style={{ textAlign: "center", ...smoothIn(f, 24, 18) }}>
        <div style={{ ...ts(64), ...gt(C.a2), lineHeight: 1 }}>20%</div>
        <div style={{ fontSize: 28, color: C.dim40, marginTop: 4 }}>时间写代码</div>
      </div>
    </div>
  </div>
);

/* ═══ S4: 金句 ═══ */
const S4 = ({ f, dur }: { f: number; dur: number }) => (
  <div style={{ ...center, ...fadeOut(f, dur) }}>
    <div style={{ ...ts(72), ...smoothIn(f, 0) }}>最好的代码</div>
    <div style={{ ...ts(72), ...smoothIn(f, 8) }}>
      是 <span style={gt(C.a2)}>你没写</span> 的代码
    </div>
    <div style={{ marginTop: 14, fontSize: 22, color: C.dim25, fontStyle: "italic", ...smoothIn(f, 18, 20) }}>
      "The best code is the code you never write."
    </div>
  </div>
);

/* ═══ S5: 生态 ═══ */
const S5 = ({ f, dur }: { f: number; dur: number }) => {
  const tags = ["improve", "openwiki", "omnigent", "DeepSpec", "token-diet"];
  const clrs = ["#818cf8", "#c084fc", "#a78bfa", "#f472b6", "#fb923c"];
  return (
    <div style={{ ...center, ...fadeOut(f, dur) }}>
      <div style={{ ...ts(42, C.dim40), ...smoothIn(f, 0, 12), marginBottom: 12 }}>而且 ...</div>
      <div style={{ ...ts(56), ...popIn(f, 8) }}><span style={gt(C.a1)}>不是孤例</span></div>
      <div style={{ marginTop: 20, display: "flex", gap: 18, flexWrap: "wrap", justifyContent: "center" }}>
        {tags.map((tag, i) => (
          <span key={tag} style={{ ...ts(36), color: clrs[i], ...popIn(f, 14 + i * 6) }}>{tag}</span>
        ))}
      </div>
      <div style={{ ...ts(34, C.dim40), marginTop: 20, ...smoothIn(f, 44, 16) }}>
        6 个项目 · 同一张 <span style={gt(C.a1)}>月榜</span>
      </div>
    </div>
  );
};

/* ═══ S6: 链条 ═══ */
const S6 = ({ f, dur }: { f: number; dur: number }) => {
  const chain = ["思考框架", "审计", "文档", "编排", "省钱工具"];
  return (
    <div style={{ ...center, ...fadeOut(f, dur) }}>
      <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
        {chain.map((item, i) => (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{
              ...ts(36, i === 0 ? undefined : i === 4 ? undefined : C.dim40),
              ...(i === 0 ? gt(C.a1) : i === 4 ? gt(C.a2) : {}),
              ...smoothIn(f, i * 6, 12),
            }}>{item}</span>
            {i < chain.length - 1 && (
              <span style={{ ...ts(24), color: C.dim10, ...smoothIn(f, 3 + i * 6, 8) }}>→</span>
            )}
          </span>
        ))}
      </div>
      <div style={{ ...ts(56), marginTop: 24, ...popIn(f, 36) }}>整个生态已经成型</div>
    </div>
  );
};

/* ═══ S7: 结尾 ═══ */
const S7 = ({ f, dur }: { f: number; dur: number }) => (
  <div style={{
    ...center,
    opacity: interpolate(f, [dur - 12, dur], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  }}>
    <div style={{ ...ts(64), ...smoothIn(f, 0) }}>AI <span style={gt(C.a1)}>编程代理</span></div>
    <div style={{ ...ts(48, C.dim40), ...smoothIn(f, 10) }}>正在变成</div>
    <div style={{ ...ts(80), marginTop: 6, ...popIn(f, 18) }}>
      <span style={gt("linear-gradient(135deg, #818cf8, #c084fc, #f472b6)")}>开发者的基础设施</span>
    </div>
    <div style={{ ...ts(34, C.dim25), marginTop: 18, ...smoothIn(f, 40) }}>2026 — 正在发生</div>
    <div style={{
      position: "absolute", bottom: 40, left: 0, right: 0, textAlign: "center",
      fontSize: 18, color: C.dim10, letterSpacing: "0.15em", ...smoothIn(f, 55),
    }}>
      AI 热点观察
    </div>
  </div>
);

/* ═══ 主组件 ═══ */
export const MyComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const scenes = [S0, S1, S2, S3, S4, S5, S6, S7];

  return (
    <AbsoluteFill style={{ backgroundColor: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(99,102,241,0.15) 0%, transparent 70%), radial-gradient(ellipse 60% 50% at 30% 70%, rgba(168,85,247,0.10) 0%, transparent 60%)",
      }} />

      {SCENE.map((s, i) => (
        <Sequence key={i} from={s.start} durationInFrames={s.frames}>
          <Audio src={staticFile(AS[i].file)} />
          {scenes[i]({ f: frame - s.start, dur: s.frames })}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
