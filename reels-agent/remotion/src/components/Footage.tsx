import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import type {ClipProps} from '../schema';

type Props = {
  clips: ClipProps[];
  totalFrames: number;
  darken: number;
  gradient?: string;
};

const resolveSrc = (src: string) => {
  if (/^https?:\/\//.test(src) || src.startsWith('/')) return src;
  return staticFile(`footage/${src}`);
};

/**
 * Последовательность b-roll клипов на весь ролик.
 * Клипы без `seconds` делят оставшееся время поровну.
 */
export const Footage: React.FC<Props> = ({clips, totalFrames, darken, gradient}) => {
  const {fps} = useVideoConfig();

  const fixed = clips.reduce((acc, c) => acc + (c.seconds ? c.seconds * fps : 0), 0);
  const flexible = clips.filter((c) => !c.seconds).length;
  const flexFrames = flexible > 0 ? Math.max(1, Math.floor((totalFrames - fixed) / flexible)) : 0;

  let cursor = 0;
  const items = clips.map((clip, i) => {
    const frames = clip.seconds ? Math.round(clip.seconds * fps) : flexFrames;
    const from = cursor;
    cursor += frames;
    // последний клип добивает до конца, чтобы не было чёрного хвоста
    const dur = i === clips.length - 1 ? Math.max(frames, totalFrames - from) : frames;
    return {clip, from, dur};
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {items.map(({clip, from, dur}, i) => (
        <Sequence key={`${clip.src}-${i}`} from={from} durationInFrames={dur} premountFor={fps}>
          <OffthreadVideo
            src={resolveSrc(clip.src)}
            startFrom={Math.round((clip.startFrom ?? 0) * fps)}
            muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </Sequence>
      ))}
      <AbsoluteFill style={{backgroundColor: `rgba(0,0,0,${darken})`}} />
      {gradient ? <AbsoluteFill style={{background: gradient}} /> : null}
    </AbsoluteFill>
  );
};
