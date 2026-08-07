/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — 4 варианта дизайна
   Каждый вариант = функция (space) -> { name, css, body, tokens }
   ═══════════════════════════════════════════════════════════ */

import { COPY, SITE, typo } from './content.mjs';
import { LOGO_SVG, qrDataUri, shanyrak, TOKENS } from './design.mjs';

const kz = COPY.kz, ru = COPY.ru;

const spaceLabel = (s) => (s.all ? 'Барлық Yourt · Все Yourt' : s.name);
const h1lines = (t) => t.split('\n').join('<br>');
const scanBoth = `${kz.scan} · ${ru.scan}`;

/* Общая шапка листа: логотип + название пространства */
const head = (s, cls = '') => `
  <header class="hd ${cls}">
    <span class="logo">${LOGO_SVG}</span>
    <span class="hd__space">${spaceLabel(s)}</span>
  </header>`;

/* ═══════════════════════════════════════════════════════════
   ВАРИАНТ 1 — «ШАҢЫРАҚ»
   Тёплая бумага, монохром. QR лежит ровно в «дымовом отверстии»
   шаңырақ — вход в пространство читается буквально.
   ═══════════════════════════════════════════════════════════ */
export const v1 = (s) => ({
  name: 'Шаңырақ',
  tokens: { paper: TOKENS.sand },
  css: `
  .sheet{padding:15mm 15mm 12mm;justify-content:space-between}
  .hd{display:flex;align-items:flex-end;justify-content:space-between;
      padding-bottom:3.6mm;border-bottom:.35mm solid rgba(22,24,28,.18)}
  .hd__space{font-size:12pt;font-weight:700;letter-spacing:-.012em}
  .h1{font-size:27pt;line-height:1.07;font-weight:800;letter-spacing:-.025em}
  .h1--ru{margin-top:4.5mm;color:var(--ink-soft);font-weight:700}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:10mm}
  .col .lang{display:block;margin-bottom:2.4mm}
  .col p{font-size:9pt;line-height:1.52}

  .medal{position:relative;align-self:center;width:162mm;height:162mm;
         display:flex;align-items:center;justify-content:center}
  .medal__bg{position:absolute;inset:0;color:var(--ink);opacity:.17}
  .card{position:relative;width:78mm;background:#fff;border-radius:4mm;
        padding:7mm 7mm 6mm;text-align:center;
        box-shadow:0 1.5mm 7mm rgba(22,24,28,.10)}
  .card .qr{width:56mm;height:56mm;margin:0 auto}
  .card b{display:block;margin-top:4.4mm;font-size:9.4pt;font-weight:800;
          line-height:1.28;letter-spacing:-.012em}
  .card b+b{margin-top:1.8mm;color:var(--ink-soft);font-weight:700}
  .card small{display:block;margin-top:3.4mm;font-size:6.9pt;line-height:1.4;
        font-weight:500;color:var(--muted)}

  .ft{display:flex;justify-content:space-between;align-items:center;
      padding-top:3.6mm;border-top:.35mm solid rgba(22,24,28,.18);
      font-size:8.2pt;font-weight:500;color:var(--ink-soft)}
  .ft b{font-weight:700;color:var(--ink)}`,
  body: `<div class="sheet">
    ${head(s)}
    <div>
      <h1 class="h1">${h1lines(kz.h1)}</h1>
      <h1 class="h1 h1--ru">${h1lines(ru.h1)}</h1>
    </div>
    <div class="cols">
      <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.lead + " " + kz.body)}</p></div>
      <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.lead + " " + ru.body)}</p></div>
    </div>
    <div class="medal">
      <div class="medal__bg">${shanyrak({ spokes: 24, stroke: .5, id: 'v1' })}</div>
      <div class="card">
        <img class="qr" src="${qrDataUri(s.id)}" alt="QR">
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <small>${scanBoth}</small>
      </div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   ВАРИАНТ 2 — «АҚ ПАРАҚ» (чистый лист)
   Швейцарская типографика: белое поле, волосяные линейки,
   крупный заголовок, QR — спокойный якорь внизу справа.
   ═══════════════════════════════════════════════════════════ */
export const v2 = (s) => ({
  name: 'Ақ парақ',
  css: `
  .sheet{padding:16mm;justify-content:space-between}
  .hd{display:flex;align-items:flex-end;justify-content:space-between;
      padding-bottom:4mm;border-bottom:.5mm solid var(--ink)}
  .hd__space{font-size:12.5pt;font-weight:800;letter-spacing:-.018em}
  .blk{display:grid;grid-template-columns:15mm 1fr;gap:6mm;
       padding-bottom:8mm;border-bottom:.25mm solid rgba(22,24,28,.22)}
  .blk h1{font-size:29pt;line-height:1.05;font-weight:800;letter-spacing:-.03em}
  .blk p{margin-top:5.5mm;max-width:126mm;font-size:9.6pt;line-height:1.55;color:var(--ink-soft)}
  .blk--ru h1{color:var(--ink)}

  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:7mm}
  .step__n{font-size:8pt;font-weight:800;letter-spacing:.12em;color:var(--muted)}
  .step__mark{width:9.5mm;height:9.5mm;margin:3mm 0 4mm;color:var(--ink)}
  .step b{display:block;font-size:10pt;font-weight:800;line-height:1.3;letter-spacing:-.012em}
  .step span{display:block;margin-top:1.6mm;font-size:9pt;font-weight:400;color:var(--ink-soft)}

  .act{display:flex;align-items:flex-end;justify-content:space-between;gap:10mm;
       padding-top:8mm;border-top:.5mm solid var(--ink)}
  .act__txt b{display:block;font-size:13.5pt;font-weight:800;line-height:1.22;letter-spacing:-.018em}
  .act__txt b+b{margin-top:2.8mm;color:var(--ink-soft)}
  .act__txt small{display:block;margin-top:5mm;font-size:7.6pt;line-height:1.45;
       font-weight:500;color:var(--muted)}
  .act__txt em{display:block;margin-top:4mm;font-style:normal;font-size:8.4pt;
       font-weight:700;color:var(--ink)}
  .act__qr{flex:none;text-align:center}
  .act__qr .qr{width:58mm;height:58mm;border:.35mm solid rgba(22,24,28,.2)}
  .act__qr figcaption{margin-top:2.8mm;font-size:6.8pt;font-weight:800;
       letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}`,
  body: `<div class="sheet">
    ${head(s)}
    <section class="blk">
      <span class="lang">${kz.lang}</span>
      <div><h1>${h1lines(kz.h1)}</h1><p>${typo(kz.lead + " " + kz.body)}</p></div>
    </section>
    <section class="blk blk--ru">
      <span class="lang">${ru.lang}</span>
      <div><h1>${h1lines(ru.h1)}</h1><p>${typo(ru.lead + " " + ru.body)}</p></div>
    </section>
    <div class="steps">
      ${[0, 1, 2].map((i) => `<div class="step">
        <div class="step__n">0${i + 1}</div>
        <div class="step__mark">${shanyrak({ spokes: 8, stroke: 2.6, id: 'v2s' + i })}</div>
        <b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div>`).join('')}
    </div>
    <div class="act">
      <div class="act__txt">
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <small>${kz.scan}<br>${ru.scan}</small>
        <em>${SITE}</em>
      </div>
      <figure class="act__qr">
        <img class="qr" src="${qrDataUri(s.id)}" alt="QR">
        <figcaption>${kz.thanks} · ${ru.thanks}</figcaption>
      </figure>
    </div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   ВАРИАНТ 3 — «КЕСТЕ» (расписание)
   Объясняет механику картинкой: полоса слотов, свободное окно
   подсвечено. Три шага. Тёплый акцент (глина).
   ═══════════════════════════════════════════════════════════ */
const SLOTS = [
  { t: '10:00', st: 'busy' }, { t: '11:00', st: 'busy' }, { t: '12:00', st: 'free' },
  { t: '13:00', st: 'busy' }, { t: '14:00', st: 'busy' }, { t: '15:00', st: 'free' },
  { t: '16:00', st: 'busy' }, { t: '17:00', st: 'free' },
];

export const v3 = (s) => ({
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
  .hero h1{font-size:23pt;line-height:1.07;font-weight:800;letter-spacing:-.025em}
  .hero h1+h1{margin-top:3.8mm;color:var(--ink-soft);font-weight:700}

  .cols{display:grid;grid-template-columns:1fr 1fr;gap:9mm}
  .col .lang{display:block;margin-bottom:2.2mm}
  .col p{font-size:8.6pt;line-height:1.5}

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
  .step{padding:5.5mm 5mm;border:.35mm solid rgba(22,24,28,.15);border-radius:4mm}
  .step__n{width:7mm;height:7mm;border-radius:50%;background:var(--accent);color:#fff;
        font-size:8.4pt;font-weight:800;display:flex;align-items:center;justify-content:center;
        margin-bottom:3.4mm}
  .step b{display:block;font-size:9pt;font-weight:800;line-height:1.3;letter-spacing:-.012em}
  .step span{display:block;margin-top:1.6mm;font-size:8.4pt;color:var(--ink-soft)}

  .act{display:flex;align-items:center;gap:9mm;padding:7mm 8mm;
       border-radius:5mm;background:var(--sand)}
  .act .qr{flex:none;width:50mm;height:50mm;border-radius:2mm}
  .act__txt b{display:block;font-size:12pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .act__txt b+b{margin-top:2.4mm;color:var(--ink-soft)}
  .act__txt p{margin-top:4mm;font-size:7.8pt;line-height:1.45;color:var(--muted);font-weight:500}
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

    <div class="cols">
      <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.lead + " " + kz.body)}</p></div>
      <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.lead + " " + ru.body)}</p></div>
    </div>

    <section class="strip">
      <div class="strip__ttl"><b>Броньдар кестесі</b><span>· Расписание броней</span></div>
      <div class="slots">${SLOTS.map((x) => `<div class="slot slot--${x.st}">${x.t}</div>`).join('')}</div>
      <div class="legend">
        <span><i style="background:var(--accent)"></i>Бос · Свободно</span>
        <span><i style="background:rgba(22,24,28,.12)"></i>Брондалған · Занято</span>
      </div>
    </section>

    <div class="steps">
      ${[0, 1, 2].map((i) => `<div class="step"><div class="step__n">${i + 1}</div>
        <b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div>`).join('')}
    </div>

    <div class="act">
      <img class="qr" src="${qrDataUri(s.id)}" alt="QR">
      <div class="act__txt">
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <p>${kz.scan}<br>${ru.scan}</p>
      </div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   ВАРИАНТ 4 — «БОЛД»
   Цветной блок на пол-листа, шаңырақ вывороткой, крупный QR.
   Максимальная заметность в коридоре.
   ═══════════════════════════════════════════════════════════ */
export const v4 = (s) => ({
  name: 'Болд',
  tokens: { accent: TOKENS.navy },
  css: `
  .sheet{padding:0}
  .top{position:relative;flex:none;height:134mm;background:var(--accent);color:#fff;
       padding:15mm 16mm 13mm;overflow:hidden;display:flex;flex-direction:column}
  .top__bg{position:absolute;right:-48mm;top:-34mm;width:158mm;height:158mm;opacity:.17;color:#fff}
  .top .hd{position:relative;display:flex;align-items:center;justify-content:space-between}
  .top .logo{color:#fff}
  .hd__space{font-size:11.5pt;font-weight:700;letter-spacing:-.012em;
       border:.4mm solid rgba(255,255,255,.5);border-radius:10mm;padding:1.7mm 4mm}
  .top .kick{position:relative;margin-top:auto;font-size:7.2pt;font-weight:800;
       letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.65)}
  .top h1{position:relative;margin-top:5mm;font-size:24.5pt;line-height:1.06;
       font-weight:800;letter-spacing:-.028em}
  .top h1+h1{margin-top:4.5mm;color:rgba(255,255,255,.72);font-weight:700}

  .bot{flex:1;padding:12mm 16mm 12mm;display:flex;flex-direction:column;
       justify-content:space-between}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:10mm}
  .col .lang{display:block;margin-bottom:2.4mm}
  .col p{font-size:8.8pt;line-height:1.52}
  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8mm}
  .step{display:flex;gap:3.4mm;align-items:flex-start}
  .step__n{flex:none;width:6.4mm;height:6.4mm;border-radius:50%;background:var(--accent);
       color:#fff;font-size:7.6pt;font-weight:800;
       display:flex;align-items:center;justify-content:center}
  .step b{display:block;font-size:9pt;font-weight:800;line-height:1.25;letter-spacing:-.012em}
  .step div span{display:block;margin-top:1.4mm;font-size:8.4pt;color:var(--ink-soft)}
  .act{display:flex;align-items:center;gap:10mm;padding-top:9mm;
       border-top:.35mm solid rgba(22,24,28,.16)}
  .act .qr{flex:none;width:56mm;height:56mm}
  .act__txt b{display:block;font-size:12.5pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .act__txt b+b{margin-top:2.6mm;color:var(--ink-soft)}
  .act__txt p{margin-top:4.4mm;font-size:8pt;line-height:1.45;color:var(--muted);font-weight:500}
  .ft{display:flex;justify-content:space-between;font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    <div class="top">
      <div class="top__bg">${shanyrak({ spokes: 24, stroke: .8, id: 'v4' })}</div>
      <div class="hd">
        <span class="logo">${LOGO_SVG}</span>
        <span class="hd__space">${spaceLabel(s)}</span>
      </div>
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    <div class="bot">
      <div class="cols">
        <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.lead + " " + kz.body)}</p></div>
        <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.lead + " " + ru.body)}</p></div>
      </div>
      <div class="steps">
        ${[0, 1, 2].map((i) => `<div class="step"><span class="step__n">${i + 1}</span>
          <div><b>${kz.steps[i]}</b><span>${ru.steps[i]}</span></div></div>`).join('')}
      </div>
      <div class="act">
        <img class="qr" src="${qrDataUri(s.id)}" alt="QR">
        <div class="act__txt">
          <b>${kz.cta}</b><b>${ru.cta}</b>
          <p>${kz.scan}<br>${ru.scan}</p>
        </div>
      </div>
      <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
    </div>
  </div>`,
});

export const VARIANTS = { v1, v2, v3, v4 };
