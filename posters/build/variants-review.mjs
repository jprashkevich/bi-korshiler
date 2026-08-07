/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — плакат «Отзывы и идеи», 4 варианта
   Бриф: QR крупный. Во всех вариантах он от 78 до 120 мм.
   ═══════════════════════════════════════════════════════════ */

import { COPY, SITE, SPACES } from './content-review.mjs';
import { typo } from './content.mjs';
import { LOGO_SVG, qrSvg, shanyrak, TOKENS } from './design.mjs';

const kz = COPY.kz, ru = COPY.ru;
const h1lines = (t) => t.split('\n').join('<br>');
export { SPACES };

const head = (s) => `
  <header class="hd">
    <span class="logo">${LOGO_SVG}</span>
    <span class="hd__space">${s.name}</span>
  </header>`;

/* ═══════════════════════════════════════════════════════════
   R1 — «ПАРА К КЕСТЕ»
   Прямой близнец плаката о бронировании: та же шапка, песочные
   карточки, глиняный акцент. На стене читаются одной серией.
   ═══════════════════════════════════════════════════════════ */
export const r1 = (s) => ({
  name: 'Пара к Кесте',
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
  .col p{font-size:9.4pt;line-height:1.52}

  .qrbox{padding:8mm;border-radius:6mm;background:var(--sand);text-align:center}
  .qrbox .qr{width:92mm;height:92mm;margin:0 auto;padding:6mm;
       background:#fff;border-radius:3mm;color:var(--ink)}
  .qrbox b{display:block;margin-top:6mm;font-size:12pt;font-weight:800;
       line-height:1.24;letter-spacing:-.018em}
  .qrbox b+b{margin-top:2.4mm;color:var(--ink-soft);font-weight:700}
  .qrbox small{display:block;margin-top:4mm;font-size:7.6pt;line-height:1.45;
       font-weight:500;color:var(--muted)}

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
      <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.body)}</p></div>
      <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.body)}</p></div>
    </div>
    <div class="qrbox">
      <div class="qr">${qrSvg(s.id)}</div>
      <b>${kz.cta}</b><b>${ru.cta}</b>
      <small>${kz.scan} · ${ru.scan}</small>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   R2 — «ҮЛКЕН QR»
   QR почти во весь лист: 120 мм, считывается через всю комнату.
   Текста ровно столько, чтобы понять, зачем сканировать.
   ═══════════════════════════════════════════════════════════ */
export const r2 = (s) => ({
  name: 'Үлкен QR',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:15mm 15mm 12mm;justify-content:space-between;text-align:center}
  .hd{display:flex;align-items:center;justify-content:space-between;text-align:left}
  .hd__space{font-size:11.5pt;font-weight:700;letter-spacing:-.012em}
  .kick{font-size:7.4pt;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
       color:var(--accent)}
  h1{margin-top:5mm;font-size:26pt;line-height:1.06;font-weight:800;letter-spacing:-.028em}
  h1+h1{margin-top:4mm;color:var(--ink-soft);font-weight:700}
  .qr{width:120mm;height:120mm;margin:0 auto;color:var(--ink)}
  .cta b{display:block;font-size:13pt;font-weight:800;line-height:1.24;letter-spacing:-.018em}
  .cta b+b{margin-top:2.6mm;color:var(--ink-soft);font-weight:700}
  .cta small{display:block;margin-top:4mm;font-size:7.8pt;line-height:1.45;
       font-weight:500;color:var(--muted)}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:9mm;text-align:left;
       padding-top:7mm;border-top:.35mm solid rgba(22,24,28,.15)}
  .col .lang{display:block;margin-bottom:2.2mm}
  .col p{font-size:8.4pt;line-height:1.5}
  .ft{display:flex;justify-content:space-between;font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    ${head(s)}
    <div>
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    <div class="qr">${qrSvg(s.id)}</div>
    <div class="cta">
      <b>${kz.cta}</b><b>${ru.cta}</b>
      <small>${kz.scan} · ${ru.scan}</small>
    </div>
    <div class="cols">
      <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.body)}</p></div>
      <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.body)}</p></div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   R3 — «ДИАЛОГ»
   QR лежит в реплике — метафора разговора, а не анкеты.
   Три темы подсказывают, о чём вообще писать.
   ═══════════════════════════════════════════════════════════ */
export const r3 = (s) => ({
  name: 'Диалог',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:14mm 14mm 11mm;justify-content:space-between}
  .hd{display:flex;align-items:center;justify-content:space-between}
  .hd__space{font-size:11.5pt;font-weight:700;background:var(--ink);color:#fff;
      padding:1.9mm 4mm;border-radius:10mm;letter-spacing:-.012em}
  .kick{font-size:7.4pt;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
      color:var(--accent)}
  h1{margin-top:4.5mm;font-size:23pt;line-height:1.07;font-weight:800;letter-spacing:-.025em}
  h1+h1{margin-top:3.8mm;color:var(--ink-soft);font-weight:700}

  .bubble{position:relative;align-self:center;width:118mm;padding:9mm 9mm 8mm;
      background:var(--sand);border-radius:8mm;text-align:center}
  .bubble::after{content:'';position:absolute;left:26mm;bottom:-6.5mm;
      width:0;height:0;border:6.6mm solid transparent;border-top-color:var(--sand);
      border-bottom:0;border-left-width:3mm}
  .bubble .qr{width:88mm;height:88mm;margin:0 auto;padding:6mm;
      background:#fff;border-radius:3mm;color:var(--ink)}
  .bubble b{display:block;margin-top:5.5mm;font-size:11.5pt;font-weight:800;
      line-height:1.24;letter-spacing:-.018em}
  .bubble b+b{margin-top:2.2mm;color:var(--ink-soft);font-weight:700}

  .topics{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}
  .topic{padding:4mm 4.5mm;border:.35mm solid var(--accent);border-radius:3mm;
      background:rgba(190,90,52,.05)}
  .topic b{display:block;font-size:8.4pt;font-weight:800;line-height:1.28;
      letter-spacing:-.012em;color:var(--accent)}
  .topic span{display:block;margin-top:1.4mm;font-size:8pt;color:var(--ink-soft)}

  .cols{display:grid;grid-template-columns:1fr 1fr;gap:9mm}
  .col .lang{display:block;margin-bottom:2.2mm}
  .col p{font-size:8.4pt;line-height:1.5}
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
    <div class="bubble">
      <div class="qr">${qrSvg(s.id)}</div>
      <b>${kz.cta}</b><b>${ru.cta}</b>
    </div>
    <div class="topics">
      ${[0, 1, 2].map((i) => `<div class="topic">
        <b>${kz.topics[i]}</b><span>${ru.topics[i]}</span></div>`).join('')}
    </div>
    <div class="cols">
      <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.body)}</p></div>
      <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.body)}</p></div>
    </div>
    <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
  </div>`,
});

/* ═══════════════════════════════════════════════════════════
   R4 — «БОЛД»
   Глиняное поле сверху, белая QR-карточка садится на границу.
   Дальнобойный вариант: коридор, лифтовый холл.
   ═══════════════════════════════════════════════════════════ */
export const r4 = (s) => ({
  name: 'Болд',
  tokens: { accent: TOKENS.clay },
  css: `
  .sheet{padding:0}
  .top{position:relative;flex:none;height:118mm;background:var(--accent);color:#fff;
       padding:15mm 16mm 26mm;overflow:hidden;display:flex;flex-direction:column}
  .top__bg{position:absolute;left:-52mm;bottom:-62mm;width:140mm;height:140mm;opacity:.18;color:#fff}
  .top .hd{position:relative;display:flex;align-items:center;justify-content:space-between}
  .top .logo{color:#fff}
  .hd__space{font-size:11.5pt;font-weight:700;letter-spacing:-.012em;
       border:.4mm solid rgba(255,255,255,.5);border-radius:10mm;padding:1.7mm 4mm}
  .top .kick{position:relative;margin-top:auto;font-size:7.4pt;font-weight:800;
       letter-spacing:.18em;text-transform:uppercase;color:rgba(255,255,255,.7)}
  .top h1{position:relative;margin-top:4.5mm;font-size:24pt;line-height:1.06;
       font-weight:800;letter-spacing:-.028em}
  .top h1+h1{margin-top:4mm;color:rgba(255,255,255,.74);font-weight:700}

  .bot{position:relative;z-index:1;flex:1;padding:0 16mm 12mm;
       display:flex;flex-direction:column;justify-content:space-between}
  .qrcard{margin-top:-20mm;align-self:center;width:112mm;padding:8mm 8mm 7mm;
       background:#fff;border-radius:6mm;text-align:center;
       box-shadow:0 2mm 9mm rgba(22,24,28,.14)}
  .qrcard .qr{width:88mm;height:88mm;margin:0 auto;color:var(--ink)}
  .qrcard b{display:block;margin-top:5mm;font-size:11.5pt;font-weight:800;
       line-height:1.24;letter-spacing:-.018em}
  .qrcard b+b{margin-top:2.2mm;color:var(--ink-soft);font-weight:700}
  .qrcard small{display:block;margin-top:3.6mm;font-size:7.4pt;line-height:1.4;
       font-weight:500;color:var(--muted)}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:9mm}
  .col .lang{display:block;margin-bottom:2.2mm}
  .col p{font-size:8.4pt;line-height:1.5}
  .ft{display:flex;justify-content:space-between;padding-top:3.4mm;
      border-top:.35mm solid rgba(22,24,28,.15);font-size:8pt;font-weight:500;color:var(--muted)}
  .ft b{color:var(--accent);font-weight:700}`,
  body: `<div class="sheet">
    <div class="top">
      <div class="top__bg">${shanyrak({ spokes: 24, stroke: .8 })}</div>
      <div class="hd">
        <span class="logo">${LOGO_SVG}</span>
        <span class="hd__space">${s.name}</span>
      </div>
      <div class="kick">${kz.kicker} · ${ru.kicker}</div>
      <h1>${h1lines(kz.h1)}</h1>
      <h1>${h1lines(ru.h1)}</h1>
    </div>
    <div class="bot">
      <div class="qrcard">
        <div class="qr">${qrSvg(s.id)}</div>
        <b>${kz.cta}</b><b>${ru.cta}</b>
        <small>${kz.scan} · ${ru.scan}</small>
      </div>
      <div class="cols">
        <div class="col"><span class="lang">${kz.lang}</span><p>${typo(kz.body)}</p></div>
        <div class="col"><span class="lang">${ru.lang}</span><p>${typo(ru.body)}</p></div>
      </div>
      <div class="ft"><span>${SITE}</span><span><b>${kz.thanks}</b> · ${ru.thanks}</span></div>
    </div>
  </div>`,
});

export const VARIANTS = { r1, r2, r3, r4 };
