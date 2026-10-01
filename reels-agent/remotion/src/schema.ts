import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

/**
 * Схема одного рилса. Это же — формат элементов массива `reels` в batch.json.
 * Агент заполняет эти поля, человек ничего руками не трогает.
 */

export const presetNames = [
  'classic', // Montserrat ExtraBold, белый с тенью — самый частый стиль в рилсах
  'clean', // Inter SemiBold, мягкий тёмный градиент, без обводки
  'editorial', // Playfair Display Italic — «журнальный» стиль
  'caps', // Oswald, капс, плотная вёрстка, акцентная строка
  'mono', // PT Mono, эффект печатной машинки
  'notes', // карточка как в «Заметках» iPhone, тёмный текст на белом
] as const;

export const positionNames = ['top', 'center', 'bottom'] as const;
export const animationNames = ['none', 'fade', 'pop', 'typewriter', 'lines'] as const;

export const clipSchema = z.object({
  /** Имя файла в remotion/public/footage, например "coffee-01.mp4" */
  src: z.string().min(1),
  /** Сколько секунд показывать этот клип. Если не задано — делится поровну. */
  seconds: z.number().positive().optional(),
  /** С какой секунды исходника начинать */
  startFrom: z.number().min(0).default(0),
});

export const endCardSchema = z.object({
  /** Крупная строка на финальной карточке, напр. «Напиши “ГАЙД” в комментах» */
  text: z.string().min(1),
  /** Мелкая строка, напр. «и бот пришлёт файл в директ» */
  sub: z.string().optional(),
  /** Длительность карточки в секундах */
  seconds: z.number().positive().default(2),
});

export const reelSchema = z.object({
  /** Уникальный id — имя выходного файла */
  id: z
    .string()
    .regex(/^[a-z0-9-]+$/, 'id: только латиница в нижнем регистре, цифры и дефис'),
  /**
   * Главный текст-хук. Переносы строк — через \n.
   * Акцентное слово выделяется звёздочками: «Это *не* про дисциплину»
   */
  hook: z.string().min(1).max(220),
  /** Необязательная мелкая строка под хуком */
  subtext: z.string().max(140).nullish(),
  position: z.enum(positionNames).default('center'),
  preset: z.enum(presetNames).default('classic'),
  animation: z.enum(animationNames).default('fade'),
  clips: z.array(clipSchema).min(1),
  durationInSeconds: z.number().min(4).max(60).default(8),
  /** Затемнение видео под текстом, 0–0.7 */
  darken: z.number().min(0).max(0.7).default(0.25),
  /** Финальная карточка с призывом. null — без неё */
  endCard: endCardSchema.nullable().default(null),
  /** Переопределение цветов пресета */
  colors: z
    .object({
      text: zColor().optional(),
      accent: zColor().optional(),
      card: zColor().optional(),
    })
    .nullish(),
  /** Принудительный размер шрифта хука (px). По умолчанию подбирается по длине */
  fontSize: z.number().min(28).max(140).nullish(),
});

export type ReelProps = z.infer<typeof reelSchema>;
export type ClipProps = z.infer<typeof clipSchema>;
export type PresetName = (typeof presetNames)[number];

/** Полный batch.json */
export const batchSchema = z.object({
  /** Имя партии, напр. "2026-10-01-batch-01" */
  name: z.string().min(1),
  /** Язык партии: ru | en | kk ... — используется только агентом */
  lang: z.string().default('ru'),
  /** Общие значения, которые подставляются в каждый рилс, если там не заданы */
  defaults: reelSchema.partial().omit({id: true, hook: true}).optional(),
  reels: z
    .array(
      reelSchema.partial({clips: true}).extend({
        /** Текст описания под рилс (для копирования при публикации) */
        caption: z.string().optional(),
        /** Кодовое слово для бота в комментариях/директе */
        keyword: z.string().optional(),
        /** Из какого паттерна банка взят хук — для аналитики */
        pattern: z.string().optional(),
      }),
    )
    .min(1),
});

export type BatchFile = z.infer<typeof batchSchema>;
