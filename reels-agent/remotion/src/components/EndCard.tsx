import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Preset} from '../presets';

type Props = {
  text: string;
  sub?: string;
  preset: Preset;
  accent?: string;
};

/** Финальная карточка с призывом: «Напиши КОД в комментариях» */
export const EndCard: React.FC<Props> = ({text, sub, preset, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 18, stiffness: 140}});
  const opacity = interpolate(frame, [0, Math.round(fps * 0.25)], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 90px 0 90px',
        backgroundColor: 'rgba(0,0,0,.55)',
        opacity,
      }}
    >
      <div
        style={{
          transform: `scale(${interpolate(s, [0, 1], [0.92, 1])})`,
          background: 'rgba(255,255,255,.97)',
          color: '#111',
          borderRadius: 32,
          padding: '48px 52px',
          textAlign: 'center',
          maxWidth: '100%',
          boxShadow: '0 24px 70px rgba(0,0,0,.45)',
          marginBottom: 120,
        }}
      >
        <div
          style={{
            fontFamily: preset.fontFamily,
            fontWeight: Math.min(800, preset.fontWeight + 100),
            fontStyle: 'normal',
            textTransform: preset.textTransform ?? 'none',
            fontSize: 60,
            lineHeight: 1.15,
            color: accent ?? '#111',
          }}
        >
          {text}
        </div>
        {sub ? (
          <div
            style={{
              fontFamily: preset.subFontFamily,
              fontWeight: 500,
              fontSize: 32,
              lineHeight: 1.3,
              color: '#444',
              marginTop: 20,
            }}
          >
            {sub}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
