/**
 * Шрифты подключаются из remotion/public/fonts — рендер не зависит от интернета.
 * Все семейства под лицензией SIL OFL и поддерживают кириллицу и латиницу.
 * Пересобрать набор: bash scripts/fetch-fonts.sh
 */
import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const fontFamilies = {
  montserrat: 'Montserrat',
  inter: 'Inter',
  playfair: 'Playfair Display',
  oswald: 'Oswald',
  mono: 'PT Mono',
} as const;

const files: Array<{family: string; file: string; weight: string; style?: 'normal' | 'italic'}> = [
  {family: fontFamilies.montserrat, file: 'Montserrat.ttf', weight: '100 900'},
  {family: fontFamilies.inter, file: 'Inter.ttf', weight: '100 900'},
  {family: fontFamilies.playfair, file: 'PlayfairDisplay-Italic.ttf', weight: '400 900', style: 'italic'},
  {family: fontFamilies.oswald, file: 'Oswald.ttf', weight: '200 700'},
  {family: fontFamilies.mono, file: 'PTMono-Regular.ttf', weight: '400'},
];

/** Запускается один раз при загрузке бандла (импорт из presets.ts). */
export const fontsReady = Promise.all(
  files.map((f) =>
    loadFont({
      family: f.family,
      url: staticFile(`fonts/${f.file}`),
      weight: f.weight,
      style: f.style ?? 'normal',
    }),
  ),
);
