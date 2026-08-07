/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — бронирование, обновлённые макеты

   Правки к первой версии: текст сокращён вдвое, QR увеличен
   сам код вырос с 42 мм до 66…103 мм, подписи «ҚАЗ / РУС» убраны.
   Языки теперь различаются цветом: казахский чернильный,
   русский приглушённый серый — метки не нужны.

   Ключи вариантов смысловые, не номерные: kest · xl · steps · shanyrak
   ═══════════════════════════════════════════════════════════ */

import { COPY, SITE, typo } from './content.mjs';
import { LOGO_SVG, qrBooking, shanyrak as shanyrakSvg, TOKENS } from './design.mjs';

const kz = COPY.kz, ru = COPY.ru;

const spaceLabel = (s) => (s.all ? 'Барлық Yourt · Все Yourt' : s.name);
const h1lines = (t) => t.split('\n').join('<br>');

const head = (s) => `
  <header class="hd">
    <span class="logo">${LOGO_SVG}</span>
    <span class="hd__space">${spaceLabel(s)}</span>
  </header>`;

/* Двуязычный абзац без подписей языка: казахский тёмный, русский серый */
const bilingual = `
  <div class="cols">
    <p class="kz">${typo(kz.text)}</p>
    <p class="ru">${typo(ru.text)}</p>
  </div>`;

const COLS_CSS = `
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:10mm}
  .cols p{font-size:9.4pt;line-height:1.5}
  .cols .kz{color:var(--ink);font-weight:500}
  .cols .ru{color:var(--ink-soft);font-weight:400}`;

/* ═══════════════════════════════════════════════════════════
   KEST — «КЕСТЕ»
   Тот же макет, что был утверждён, по новому брифу: текста вдвое
   меньше, код 70 мм вместо 42, языковых меток нет.
   ═══════════════════════════════════════════════════════════ */
export const kest = (s) => ({
  name: 'Кесте',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:14mm 14mm 11mm;justify-content:space-between}
  .hd{display:flex;align-items:center;justify-content:space-between}
  .hd__space{font-size:11.5pt;font-weight:700;background:var(--ink);color:#fff;
      padding:1.9mm 4mm;border-radius:10mm;letter-spacing:-.012em}

  .hero{padding:9mm 9mm 8.5mm;border-radius:6mm;background:var(--sand)}
  .hero .kick{font-size:7.2pt;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
      color:var(--accent);margin-bottom:4.5mm}
  .hero h1{font-size:22.5pt;line-height:1.07;font-weight:800;letter-spacing:-.025em}
  .hero h1+h1{margin-top:3.8mm;color:var(--ink-soft);font-weight:700}
  ${COLS_CSS}

  .strip__ttl{display:flex;gap:3mm;align-items:baseline;margin-bottom:3.4mm}
  .strip__ttl b{font-size:9.4pt;font-weight:800;letter-spacing:-.012em}
  .strip__ttl span{font-size:9pt;color:var(--ink-soft)}
  .slots{display:grid;grid-template-columns:repeat(8,1fr);gap:1.8mm}
  .slot{border-radius:2mm;padding:3.8mm 0 3.4mm;text-align:center;
        font-size:7.4pt;font-weight:700;letter-spacing:-.01em}
  .slot--busy{background:rgba(22,24,28,.08);color:var(--muted)}
  .slot--free{background:var(--accent);color:#fff}
  .legend{display:flex;gap:7mm;margin-top:3.2mm;font-size:7.4pt;font-weight:500;color:var(--ink-soft)}
  .legend i{display:inline-block;width:2.6mm;height:2.6mm;border-radius:.7mm;
        margin-right:1.8mm;vertical-align:-.2mm}

  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm}
  .step{display:flex;gap:3.4mm;align-items:flex-start}
  .step__n{flex:none;width:6.6mm;height:6.6mm;border-radius:50%;background:var(--accent);
        color:#fff;font-size:8pt;font-weight:800;
        display:flex;align-items:center;justify-content:center}
  .step b{display:block;font-size:9pt;font-weight:800;line-height:1.26;letter-spacing:-.012em}
  .step div span{display:block;margin-top:1.4mm;font-size:8.4pt;color:var(--ink-soft)}

  .act{display:flex;align-items:center;gap:9mm;padding:8mm;
       border-radius:6mm;background:var(--sand)}
  .act .qr{flex:none;width:70mm;height:70mm;border-radius:2mm;color:var(--ink);
       background:#fff;padding:0;box-shadow:0 0 0 8mm #fff}
  .act__txt b{display:block;font-size:11.5pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .act__txt b+b{margin-top:2.4mm;color:var(--ink-soft);font-weight:700}
  .act__txt p{margin-top:4mm;font-size:8pt;line-height:1.45;color:var(--muted);font-weight:500}
  .ft{display:flex;justify-content:space-between;padding-top:3.4mm;
      border-top:.35mm solid rgba(22,24,28,.15);font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    ${head(s)}
    <section class="hero">
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </section>
    ${bilingual}
    <section class="strip">
      <div class="strip__ttl"><b>Броньдар кестесі</b><span>· Расписание броней</span></div>
      <div class="slots">${SLOTS.map((x) => `<div class="slot slot--${x.st}">${x.t}</div>`).join('')}</div>
      <div class="legend">
        <span><i style="background:var(--accent)"></i>Бос · Свободно</span>
        <span><i style="background:rgba(22,24,28,.12)"></i>Брондалған · Занято</span>
      </div>
    </section>
    <div class="steps">
      ${[0, 1, 2].map((i) => `<div class="step"><span class="step__n">${i + 1}</span>
        <div><b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div></div>`).join('')}
    </div>
    <div class="act">
      <div class="qr">${qrBooking(s.id)}</div>
      <div class="act__txt">
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <p>${kz.scan}<br>${ru.scan}</p>
      </div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   XL — «ҮЛКЕН QR»
   Пара к выбранному плакату отзывов: та же композиция, QR 108 мм.
   На стене рядом две работы читаются одной серией.
   ═══════════════════════════════════════════════════════════ */
export const xl = (s) => ({
  name: 'Үлкен QR',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:15mm 15mm 12mm;justify-content:space-between;text-align:center}
  .hd{display:flex;align-items:center;justify-content:space-between;text-align:left}
  .hd__space{font-size:11.5pt;font-weight:700;letter-spacing:-.012em}
  .kick{font-size:7.4pt;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
       color:var(--accent)}
  h1{margin-top:5mm;font-size:24pt;line-height:1.06;font-weight:800;letter-spacing:-.028em}
  h1+h1{margin-top:3.6mm;color:var(--ink-soft);font-weight:700}
  .qr{width:103mm;height:103mm;margin:0 auto;color:var(--ink)}
  .cta b{display:block;font-size:13pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .cta b+b{margin-top:2.6mm;color:var(--ink-soft);font-weight:700}
  .cta small{display:block;margin-top:4mm;font-size:7.8pt;line-height:1.45;
       font-weight:500;color:var(--muted)}
  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm;text-align:left;
       padding-top:7mm;border-top:.35mm solid rgba(22,24,28,.15)}
  .step{display:flex;gap:3.4mm;align-items:flex-start}
  .step__n{flex:none;width:6.6mm;height:6.6mm;border-radius:50%;background:var(--accent);
       color:#fff;font-size:8pt;font-weight:800;
       display:flex;align-items:center;justify-content:center}
  .step b{display:block;font-size:9pt;font-weight:800;line-height:1.26;letter-spacing:-.012em}
  .step div span{display:block;margin-top:1.4mm;font-size:8.4pt;color:var(--ink-soft)}
  .ft{display:flex;justify-content:space-between;font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    ${head(s)}
    <div>
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    <div class="qr">${qrBooking(s.id)}</div>
    <div class="cta">
      <div><b>${kz.cta}</b><b>${ru.cta}</b></div>
      <small>${kz.scan}<br>${ru.scan}</small>
    </div>
    <div class="steps">
      ${[0, 1, 2].map((i) => `<div class="step"><span class="step__n">${i + 1}</span>
        <div><b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div></div>`).join('')}
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   STEPS — «ҮШ ҚАДАМ»
   Без полосы расписания: три шага столбцом справа, QR 92 мм слева.
   Самый лаконичный из четырёх.
   ═══════════════════════════════════════════════════════════ */
export const steps = (s) => ({
  name: 'Үш қадам',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:15mm 15mm 12mm;justify-content:space-between}
  .hd{display:flex;align-items:center;justify-content:space-between}
  .hd__space{font-size:11.5pt;font-weight:700;background:var(--ink);color:#fff;
      padding:1.9mm 4mm;border-radius:10mm;letter-spacing:-.012em}
  .kick{font-size:7.4pt;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
      color:var(--accent)}
  h1{margin-top:5mm;font-size:27pt;line-height:1.06;font-weight:800;letter-spacing:-.028em}
  h1+h1{margin-top:4.2mm;color:var(--ink-soft);font-weight:700}
  ${COLS_CSS}

  .main{display:flex;align-items:stretch;gap:10mm;padding:9mm;
       border-radius:6mm;background:var(--sand)}
  .main .qr{flex:none;width:78mm;height:78mm;background:#fff;color:var(--ink);
       border-radius:3mm;box-shadow:0 0 0 8mm #fff}
  .steps{flex:1;display:flex;flex-direction:column;justify-content:center;gap:9mm}
  .step{display:flex;gap:3.6mm;align-items:flex-start}
  .step__n{flex:none;width:7mm;height:7mm;border-radius:50%;background:var(--accent);
       color:#fff;font-size:8.4pt;font-weight:800;
       display:flex;align-items:center;justify-content:center}
  .step b{display:block;font-size:9.6pt;font-weight:800;line-height:1.26;letter-spacing:-.012em}
  .step div span{display:block;margin-top:1.4mm;font-size:8.8pt;color:var(--ink-soft)}
  .cta{display:grid;grid-template-columns:1fr auto;align-items:end;gap:10mm}
  .cta b{display:block;font-size:12pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .cta b+b{margin-top:2.2mm;color:var(--ink-soft);font-weight:700}
  .cta small{font-size:7.4pt;line-height:1.45;font-weight:500;color:var(--muted);text-align:right}
  .ft{display:flex;justify-content:space-between;padding-top:3.4mm;
      border-top:.35mm solid rgba(22,24,28,.15);font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    ${head(s)}
    <div>
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    ${bilingual}
    <div class="main">
      <div class="qr">${qrBooking(s.id)}</div>
      <div class="steps">
        ${[0, 1, 2].map((i) => `<div class="step"><span class="step__n">${i + 1}</span>
          <div><b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div></div>`).join('')}
      </div>
    </div>
    <div class="cta">
      <div><b>${kz.cta}</b><b>${ru.cta}</b></div>
      <small>${kz.scan}<br>${ru.scan}</small>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   SHANYRAK — «ШАҢЫРАҚ»
   Тёплая бумага, монохром. QR 68 мм лежит в «дымовом отверстии».
   ═══════════════════════════════════════════════════════════ */
export const shanyrak = (s) => ({
  name: 'Шаңырақ',
  tokens: { paper: TOKENS.sand, accent: TOKENS.clay },
  css: `
  .sheet{padding:15mm 15mm 12mm;justify-content:space-between}
  .hd{display:flex;align-items:flex-end;justify-content:space-between;
      padding-bottom:3.6mm;border-bottom:.35mm solid rgba(22,24,28,.18)}
  .hd__space{font-size:12pt;font-weight:700;letter-spacing:-.012em}
  h1{font-size:26pt;line-height:1.07;font-weight:800;letter-spacing:-.025em}
  h1+h1{margin-top:4.2mm;color:var(--ink-soft);font-weight:700}
  ${COLS_CSS}

  .medal{position:relative;align-self:center;width:168mm;height:168mm;
         display:flex;align-items:center;justify-content:center}
  .medal__bg{position:absolute;inset:0;color:var(--ink);opacity:.17}
  .card{position:relative;width:100mm;background:#fff;border-radius:4mm;
        padding:7mm 7mm 6mm;text-align:center;
        box-shadow:0 1.5mm 7mm rgba(22,24,28,.10)}
  .card .qr{width:66mm;height:66mm;margin:0 auto;color:var(--ink)}
  .card b{display:block;margin-top:5mm;font-size:10pt;font-weight:800;
          line-height:1.26;letter-spacing:-.012em}
  .card b+b{margin-top:1.8mm;color:var(--ink-soft);font-weight:700}
  .card small{display:block;margin-top:3.4mm;font-size:7pt;line-height:1.4;
        font-weight:500;color:var(--muted)}
  .ft{display:flex;justify-content:space-between;align-items:center;
      padding-top:3.6mm;border-top:.35mm solid rgba(22,24,28,.18);
      font-size:8.2pt;font-weight:500;color:var(--ink-soft)}
  .ft b{font-weight:700;color:var(--ink)}`,
  body: `<div class="sheet">
    ${head(s)}
    <div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    ${bilingual}
    <div class="medal">
      <div class="medal__bg">${shanyrakSvg({ spokes: 24, stroke: .5 })}</div>
      <div class="card">
        <div class="qr">${qrBooking(s.id)}</div>
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <small>${kz.scan} · ${ru.scan}</small>
      </div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* Демо-расписание для варианта «Кесте» */
const SLOTS = [
  { t: '10:00', st: 'busy' }, { t: '11:00', st: 'busy' }, { t: '12:00', st: 'free' },
  { t: '13:00', st: 'busy' }, { t: '14:00', st: 'busy' }, { t: '15:00', st: 'free' },
  { t: '16:00', st: 'busy' }, { t: '17:00', st: 'free' },
];

export const VARIANTS = { kest, xl, steps, shanyrak };
