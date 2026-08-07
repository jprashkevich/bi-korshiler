/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — плакат «Отзывы и идеи» (KZ / RU)
   Тональность: дружелюбная и простая, как в плакате о бронировании.
   ═══════════════════════════════════════════════════════════ */

export const COPY = {
  kz: {
    lang:   'ҚАЗ',
    kicker: 'Пікірлер мен идеялар',
    h1:     'Yourt-ты бірге\nжақсартайық',
    body:   'Біз Yourt-ты әр апта сайын жақсартқымыз келеді! Пікірлеріңіз бен идеяларыңызды осы QR арқылы дәл қазір күтеміз!',
    cta:    'Пікір немесе идея қалдырыңыз',
    scan:   'Телефон камерасын QR-кодқа бағыттаңыз',
    topics: ['Не ұнады', 'Нені жақсартуға болады', 'Не істегіңіз келеді'],
    thanks: 'Рақмет, көрші!',
  },
  ru: {
    lang:   'РУС',
    kicker: 'Отзывы и идеи',
    h1:     'Делаем Yourt\nлучше вместе',
    body:   'Мы хотим делать Yourt лучше каждую неделю! И мы ждём ваших отзывов и идей по этому QR уже сейчас!',
    cta:    'Оставьте отзыв или идею',
    scan:   'Наведите камеру телефона на QR-код',
    topics: ['Что понравилось', 'Что улучшить', 'Что хочется провести'],
    thanks: 'Спасибо, сосед!',
  },
};

export const SITE = 'tunely.kz';

/* ─── 13 пространств. id = slug из имени файла QR (qr-<id>.svg),
   он же хвост ссылки tunely.kz/q/<id> ────────────────────────── */
export const SPACES = [
  { id: 'ala-egizbaeva',     name: 'Egizbaeva',             city: 'Алматы', cityLat: 'Almaty' },
  { id: 'ala-momyshuly',     name: 'Momyshuly',             city: 'Алматы', cityLat: 'Almaty' },
  { id: 'ast-arena-garden',  name: 'Arena Garden',          city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-aurora',        name: 'GreenLine Aurora',      city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-emotions',      name: 'Capital Park Emotions', city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-flagman',       name: 'Flagman',               city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-flora',         name: 'GreenLine Flora',       city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-grand-turan',   name: 'Grand Turan',           city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-nexpo-classic', name: 'Nexpo Classic',         city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-nexpo-trend',   name: 'Nexpo Trend',           city: 'Астана', cityLat: 'Astana' },
  { id: 'ast-qasteev',       name: 'Qasteev',               city: 'Астана', cityLat: 'Astana' },
  { id: 'atr-abulkhair',     name: 'Abulkhair',             city: 'Атырау', cityLat: 'Atyrau' },
  { id: 'atr-taimanov',      name: 'Taimanov',              city: 'Атырау', cityLat: 'Atyrau' },
];
