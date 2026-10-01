import React, {useEffect, useMemo, useState} from 'react';
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import type {Preset} from '../presets';
import type {ReelProps} from '../schema';
import {fontsReady} from '../fonts';

type Props = {
  hook: string;
  subtext?: string | null;
  position: ReelProps['position'];
  animation: ReelProps['animation'];
  preset: Preset;
  colors?: ReelProps['colors'];
  fontSize?: number | null;
};

/**
 * Безопасные зоны Instagram (1080x1920):
 * сверху ~220px занимает статус-бар и «Reels», снизу ~330px — описание и кнопки,
 * справа ~130px — колонка лайков. Текст держим внутри.
 */
const SAFE = {top: 230, bottom: 340, side: 72, right: 72};

/** Разбивает строку на сегменты: обычный текст и *акцент* */
const parseAccent = (line: string) =>
  line.split(/(\*[^*]+\*)/g).filter(Boolean).map((part) =>
    part.startsWith('*') && part.endsWith('*')
      ? {text: part.slice(1, -1), accent: true}
      : {text: part, accent: false},
  );

/**
 * Автоподбор размера: верхняя планка — по общей длине текста,
 * затем уменьшаем, пока самая длинная строка не влезет в ширину
 * (измеряем реальным шрифтом, чтобы не было «хвостов» из одного слова).
 */
const autoFontSize = (hook: string, preset: Preset, availableWidth: number) => {
  const plain = hook.replace(/\*/g, '');
  const len = plain.length;
  let size = preset.baseFontSize;
  if (len > 160) size = preset.baseFontSize * 0.52;
  else if (len > 110) size = preset.baseFontSize * 0.6;
  else if (len > 70) size = preset.baseFontSize * 0.7;
  else if (len > 40) size = preset.baseFontSize * 0.84;
  size = Math.round(size);

  const lines = plain.split('\n').map((l) => (preset.textTransform === 'uppercase' ? l.toUpperCase() : l));
  const widest = (fontSize: number) =>
    Math.max(
      ...lines.map(
        (l) =>
          measureText({
            text: l || ' ',
            fontFamily: preset.fontFamily,
            fontSize,
            fontWeight: String(preset.fontWeight),
            letterSpacing: preset.letterSpacing,
            validateFontIsLoaded: false,
          }).width,
      ),
    );
  while (size > 34 && widest(size) > availableWidth) size -= 2;
  return size;
};

export const HookText: React.FC<Props> = ({
  hook,
  subtext,
  position,
  animation,
  preset,
  colors,
  fontSize,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const textColor = colors?.text ?? (preset.cardColor ? preset.cardTextColor! : preset.textColor);
  const accentColor = colors?.accent ?? preset.accentColor;
  const cardColor = colors?.card ?? preset.cardColor;
  const availableWidth = 1080 - SAFE.side - SAFE.right - (cardColor ? 96 : 0);

  // Ждём шрифты, иначе измерение строк будет по запасному шрифту
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [handle] = useState(() => delayRender('Loading fonts for HookText'));
  useEffect(() => {
    fontsReady
      .then(() => {
        setFontsLoaded(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, [handle]);

  const size = useMemo(
    () => fontSize ?? (fontsLoaded ? autoFontSize(hook, preset, availableWidth) : preset.baseFontSize),
    [fontSize, fontsLoaded, hook, preset, availableWidth],
  );
  const lines = hook.split('\n');

  // --- анимация появления всего блока
  const appear = spring({frame, fps, config: {damping: 200, stiffness: 120, mass: 0.8}});
  const fade = interpolate(frame, [0, Math.round(fps * 0.4)], [0, 1], {extrapolateRight: 'clamp'});
  const blockOpacity = animation === 'none' ? 1 : animation === 'pop' ? appear : fade;
  const blockScale = animation === 'pop' ? interpolate(appear, [0, 1], [0.88, 1]) : 1;
  const blockShift = animation === 'fade' ? interpolate(fade, [0, 1], [18, 0]) : 0;

  // --- печатная машинка: сколько символов уже показано
  const totalChars = hook.replace(/\*/g, '').length;
  const typedChars =
    animation === 'typewriter'
      ? Math.min(totalChars, Math.floor(frame / Math.max(1, Math.round(fps / 22))))
      : totalChars;

  const justify =
    position === 'top' ? 'flex-start' : position === 'bottom' ? 'flex-end' : 'center';

  let charCursor = 0;

  return (
    <AbsoluteFill
      style={{
        justifyContent: justify,
        alignItems: 'center',
        paddingTop: SAFE.top,
        paddingBottom: SAFE.bottom,
        paddingLeft: SAFE.side,
        paddingRight: SAFE.right,
      }}
    >
      <div
        style={{
          opacity: blockOpacity,
          transform: `translateY(${blockShift}px) scale(${blockScale})`,
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 22,
        }}
      >
        <div
          style={{
            fontFamily: preset.fontFamily,
            fontWeight: preset.fontWeight,
            fontStyle: preset.fontStyle ?? 'normal',
            textTransform: preset.textTransform ?? 'none',
            letterSpacing: preset.letterSpacing,
            lineHeight: preset.lineHeight,
            fontSize: size,
            color: textColor,
            textAlign: 'center',
            textShadow: cardColor ? undefined : preset.textShadow,
            WebkitTextStroke: cardColor ? undefined : preset.WebkitTextStroke,
            background: cardColor,
            borderRadius: cardColor ? 28 : 0,
            padding: cardColor ? '44px 48px' : 0,
            boxShadow: cardColor ? '0 20px 60px rgba(0,0,0,.35)' : undefined,
            maxWidth: '100%',
            wordBreak: 'break-word',
          }}
        >
          {lines.map((line, li) => {
            // анимация построчно
            const lineDelay = animation === 'lines' ? li * Math.round(fps * 0.35) : 0;
            const lineOpacity =
              animation === 'lines'
                ? interpolate(frame, [lineDelay, lineDelay + Math.round(fps * 0.3)], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  })
                : 1;
            const segments = parseAccent(line);
            return (
              <div key={li} style={{opacity: lineOpacity}}>
                {segments.map((seg, si) => {
                  const start = charCursor;
                  charCursor += seg.text.length;
                  const visible = Math.max(0, Math.min(seg.text.length, typedChars - start));
                  const text = animation === 'typewriter' ? seg.text.slice(0, visible) : seg.text;
                  return (
                    <span key={si} style={{color: seg.accent ? accentColor : undefined}}>
                      {text}
                    </span>
                  );
                })}
                {animation === 'typewriter' && li === lines.length - 1 && typedChars < totalChars ? (
                  <span style={{opacity: Math.floor(frame / 8) % 2 ? 0 : 1}}>▍</span>
                ) : null}
                {line.length === 0 ? ' ' : null}
              </div>
            );
          })}
        </div>
        {subtext ? (
          <div
            style={{
              fontFamily: preset.subFontFamily,
              fontWeight: preset.subFontWeight,
              fontSize: Math.round(size * 0.46),
              lineHeight: 1.3,
              color: cardColor ? textColor : preset.textColor,
              opacity: 0.92,
              textAlign: 'center',
              textShadow: cardColor ? undefined : '0 1px 3px rgba(0,0,0,.6)',
              background: cardColor ? cardColor : undefined,
              borderRadius: cardColor ? 18 : 0,
              padding: cardColor ? '14px 24px' : 0,
              maxWidth: '92%',
            }}
          >
            {subtext}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
