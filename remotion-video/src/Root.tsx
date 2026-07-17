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
        width={1080}
        height={1920}
      />
      <Composition
        id="GenericVideo"
        component={GenericVideo}
        durationInFrames={1}
        fps={30}
        width={1920}
        height={1080}
        calculateMetadata={({ props }) => {
          const totalFrames = (props.totalFrames as number) || 1;
          return {
            durationInFrames: totalFrames,
            fps: 30,
            width: 1080,
            height: 1920,
          };
        }}
      />
    </>
  );
};
