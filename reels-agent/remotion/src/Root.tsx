import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';
import {reelSchema} from './schema';

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;

/** Значения для предпросмотра в Remotion Studio (`npm run studio`) */
export const defaultProps = reelSchema.parse({
  id: 'preview',
  hook: 'Никто не говорит об этом,\nпока ты *не заплатишь* за курс',
  subtext: 'сохрани, чтобы не потерять',
  position: 'center',
  preset: 'classic',
  animation: 'fade',
  clips: [{src: 'sample.mp4'}],
  durationInSeconds: 8,
  darken: 0.25,
  endCard: {text: 'Напиши «ГАЙД» в комментариях', sub: 'и бот пришлёт файл в директ', seconds: 2},
});

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Reel"
      component={Reel}
      width={WIDTH}
      height={HEIGHT}
      fps={FPS}
      durationInFrames={defaultProps.durationInSeconds * FPS}
      schema={reelSchema}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => {
        // Нормализуем входные props: подставляем дефолты схемы (startFrom, darken и т.д.)
        const parsed = reelSchema.parse(props);
        return {
          props: parsed,
          durationInFrames: Math.round(parsed.durationInSeconds * FPS),
        };
      }}
    />
  );
};
