import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {Footage} from './components/Footage';
import {HookText} from './components/HookText';
import {EndCard} from './components/EndCard';
import {presets} from './presets';
import type {ReelProps} from './schema';

/**
 * Один «тихий» рилс: b-roll + текст-хук (+ финальная карточка).
 * Вся логика оформления — в presets.ts, размещения — в HookText.tsx.
 */
export const Reel: React.FC<ReelProps> = (props) => {
  const {fps, durationInFrames} = useVideoConfig();
  const preset = presets[props.preset];
  const endFrames = props.endCard ? Math.round(props.endCard.seconds * fps) : 0;
  const hookFrames = durationInFrames - endFrames;

  return (
    <AbsoluteFill>
      <Footage
        clips={props.clips}
        totalFrames={durationInFrames}
        darken={props.darken}
        gradient={preset.gradient}
      />
      <Sequence from={0} durationInFrames={hookFrames} layout="none">
        <HookText
          hook={props.hook}
          subtext={props.subtext}
          position={props.position}
          animation={props.animation}
          preset={preset}
          colors={props.colors}
          fontSize={props.fontSize ?? undefined}
        />
      </Sequence>
      {props.endCard ? (
        <Sequence from={hookFrames} durationInFrames={endFrames} layout="none">
          <EndCard
            text={props.endCard.text}
            sub={props.endCard.sub}
            preset={preset}
            accent={props.colors?.accent}
          />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
