import type {PresetName} from './schema';
import {fontFamilies} from './fonts';

export type Preset = {
  fontFamily: string;
  fontWeight: number;
  fontStyle?: 'normal' | 'italic';
  textTransform?: 'none' | 'uppercase';
  letterSpacing?: string;
  lineHeight: number;
  textColor: string;
  accentColor: string;
  /** Тень/обводка текста */
  textShadow?: string;
  WebkitTextStroke?: string;
  /** Если задано — текст рисуется на карточке этого цвета */
  cardColor?: string;
  cardTextColor?: string;
  /** Базовый размер для хука до 40 символов */
  baseFontSize: number;
  /** Средняя ширина символа в долях от кегля — для подбора размера по самой длинной строке */
  charWidth: number;
  subFontFamily: string;
  subFontWeight: number;
  /** Градиент поверх видео (поверх darken) */
  gradient?: string;
};

/**
 * Пресеты оформления. Названия шрифтов — те, что чаще всего встречаются
 * в текстовых рилсах с большими охватами: жирный гротеск с тенью,
 * чистый гротеск без обводки, курсивная антиква, плотный капс, моно, «заметки».
 */
export const presets: Record<PresetName, Preset> = {
  classic: {
    fontFamily: fontFamilies.montserrat,
    fontWeight: 800,
    lineHeight: 1.15,
    textColor: '#FFFFFF',
    accentColor: '#FFD60A',
    textShadow: '0 2px 4px rgba(0,0,0,.55), 0 8px 24px rgba(0,0,0,.35)',
    WebkitTextStroke: '1.5px rgba(0,0,0,.35)',
    baseFontSize: 76,
    charWidth: 0.64,
    subFontFamily: fontFamilies.montserrat,
    subFontWeight: 600,
  },
  clean: {
    fontFamily: fontFamilies.inter,
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '-0.01em',
    textColor: '#FFFFFF',
    accentColor: '#9BE7FF',
    textShadow: '0 1px 2px rgba(0,0,0,.4)',
    baseFontSize: 64,
    charWidth: 0.56,
    subFontFamily: fontFamilies.inter,
    subFontWeight: 400,
    gradient:
      'linear-gradient(180deg, rgba(0,0,0,.35) 0%, rgba(0,0,0,0) 35%, rgba(0,0,0,0) 60%, rgba(0,0,0,.45) 100%)',
  },
  editorial: {
    fontFamily: fontFamilies.playfair,
    fontWeight: 500,
    fontStyle: 'italic',
    lineHeight: 1.18,
    textColor: '#FFFFFF',
    accentColor: '#F5C26B',
    textShadow: '0 2px 6px rgba(0,0,0,.5)',
    baseFontSize: 74,
    charWidth: 0.5,
    subFontFamily: fontFamilies.inter,
    subFontWeight: 400,
    gradient:
      'linear-gradient(180deg, rgba(0,0,0,.25) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0) 65%, rgba(0,0,0,.4) 100%)',
  },
  caps: {
    fontFamily: fontFamilies.oswald,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.01em',
    lineHeight: 1.02,
    textColor: '#FFFFFF',
    accentColor: '#FF3B30',
    textShadow: '0 3px 0 rgba(0,0,0,.45), 0 10px 30px rgba(0,0,0,.35)',
    baseFontSize: 96,
    charWidth: 0.46,
    subFontFamily: fontFamilies.inter,
    subFontWeight: 500,
  },
  mono: {
    fontFamily: fontFamilies.mono,
    fontWeight: 400,
    lineHeight: 1.35,
    textColor: '#F2F2F2',
    accentColor: '#7CFF8A',
    textShadow: '0 1px 2px rgba(0,0,0,.6)',
    baseFontSize: 54,
    charWidth: 0.6,
    subFontFamily: fontFamilies.mono,
    subFontWeight: 400,
    gradient: 'linear-gradient(180deg, rgba(0,0,0,.25), rgba(0,0,0,.45))',
  },
  notes: {
    fontFamily: fontFamilies.inter,
    fontWeight: 500,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
    textColor: '#111111',
    accentColor: '#C9871A',
    cardColor: 'rgba(255,255,255,.96)',
    cardTextColor: '#111111',
    baseFontSize: 56,
    charWidth: 0.55,
    subFontFamily: fontFamilies.inter,
    subFontWeight: 400,
  },
};
