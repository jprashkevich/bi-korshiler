/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — дизайн-система
   Шрифт: Gotham (Book/Medium/Bold/Black) — единственная гарнитура
   в наборе с полной поддержкой казахской кириллицы (Ә Ғ Қ Ң Ө Ұ Ү Һ І).
   TT Firs Neue НЕ используется: в файле нет казахских глифов.
   ═══════════════════════════════════════════════════════════ */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

const b64 = (p) => fs.readFileSync(path.join(ROOT, p)).toString('base64');

export const FONT_CSS = `
@font-face{font-family:'Gotham';src:url(data:font/ttf;base64,${b64('fonts/Gotham_Book.ttf')}) format('truetype');font-weight:400;font-style:normal}
@font-face{font-family:'Gotham';src:url(data:font/ttf;base64,${b64('fonts/Gotham_Medium.ttf')}) format('truetype');font-weight:500;font-style:normal}
@font-face{font-family:'Gotham';src:url(data:font/ttf;base64,${b64('fonts/Gotham_Bold.ttf')}) format('truetype');font-weight:700;font-style:normal}
@font-face{font-family:'Gotham';src:url(data:font/ttf;base64,${b64('fonts/Gotham_Black.ttf')}) format('truetype');font-weight:800;font-style:normal}
`;

export const LOGO_SVG = fs.readFileSync(path.join(ROOT, 'posters/assets/yourt-logo.svg'), 'utf8');

/* Оба набора QR инлайнятся вектором: на плакате код печатается 100+ мм,
   и растр пришлось бы растягивать с интерполяцией — края модулей плывут,
   часть декодеров перестаёт читать. В SVG модуль остаётся модулем.
   Бронирование: PNG переведены в SVG скриптом build/qr_png_to_svg.py.
   Отзывы: вектор от segno, viewBox он не проставляет — добавляем. */
export const qrBooking = (id) =>
  fs.readFileSync(path.join(ROOT, `posters/assets/qr/${id}.svg`), 'utf8');

export const qrSvg = (id) =>
  fs.readFileSync(path.join(ROOT, `posters/assets/qr-review/qr-${id}.svg`), 'utf8')
    .replace(/<\?xml[^>]*\?>\s*/, '')
    .replace(/<svg([^>]*?)width="(\d+)"\s+height="(\d+)"/,
             '<svg$1viewBox="0 0 $2 $3" width="100%" height="100%"')
    .replace(/stroke="#[0-9a-fA-F]{3,8}"/, 'stroke="currentColor"');

/* ─── Шаңырақ: вид юрты сверху — ключевой графический мотив ──
   id генерируется счётчиком: в сводном PDF на 13 страниц один и тот же
   макет повторяется, и одинаковые id у clipPath ломали бы отрисовку. */
let shId = 0;
export function shanyrak({ spokes = 20, stroke = 0.9 } = {}) {
  const id = `sh${++shId}`;
  const R_OUT = 49, R_MID = 46.2, R_HUB = 16, R_HUB_IN = 14.3;
  let uyq = '';
  for (let i = 0; i < spokes; i++) {
    const a = (i / spokes) * Math.PI * 2 - Math.PI / 2;
    const x1 = 50 + Math.cos(a) * R_HUB, y1 = 50 + Math.sin(a) * R_HUB;
    const x2 = 50 + Math.cos(a) * R_MID, y2 = 50 + Math.sin(a) * R_MID;
    /* лёгкий изгиб уыков — как в настоящем шаңырақ */
    const am = a + 0.055, rm = (R_HUB + R_MID) / 2;
    const cx = 50 + Math.cos(am) * rm, cy = 50 + Math.sin(am) * rm;
    uyq += `<path d="M${x1.toFixed(2)} ${y1.toFixed(2)} Q${cx.toFixed(2)} ${cy.toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}"/>`;
  }
  let lattice = '';
  for (const o of [-9, -4.5, 0, 4.5, 9]) {
    lattice += `<line x1="${50 - 14 + o}" y1="${50 - 14 - o}" x2="${50 + 14 + o}" y2="${50 + 14 - o}"/>`;
    lattice += `<line x1="${50 - 14 + o}" y1="${50 + 14 + o}" x2="${50 + 14 + o}" y2="${50 - 14 + o}"/>`;
  }
  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none"
    stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" aria-hidden="true">
    <defs><clipPath id="${id}-hub"><circle cx="50" cy="50" r="${R_HUB_IN}"/></clipPath></defs>
    <circle cx="50" cy="50" r="${R_OUT}"/>
    <circle cx="50" cy="50" r="${R_MID}"/>
    <g>${uyq}</g>
    <g clip-path="url(#${id}-hub)" stroke-width="${stroke * 0.85}">${lattice}</g>
    <circle cx="50" cy="50" r="${R_HUB}"/>
    <circle cx="50" cy="50" r="${R_HUB_IN}"/>
  </svg>`;
}

/* ─── Токены + базовые примитивы ─────────────────────────── */
export const BASE_CSS = `
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
@page{size:A4 portrait;margin:0}
html,body{width:210mm;height:297mm}
body{
  font-family:'Gotham',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
  text-rendering:geometricPrecision;
  color:var(--ink);background:var(--paper);
}
.sheet{
  position:relative;width:210mm;height:297mm;overflow:hidden;
  display:flex;flex-direction:column;
  page-break-after:always;break-after:page;
}
.sheet:last-child{page-break-after:auto;break-after:auto}
img{display:block;max-width:100%}
svg{display:block}

/* Логотип yourt. */
.logo{height:5.4mm;color:var(--ink)}
.logo svg{height:100%;width:auto}

/* Языковая метка */
.lang{
  font-size:6.6pt;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);
}
.qr{background:#fff}
`;

/* Общие переменные-палитры */
export const TOKENS = {
  ink:      '#16181C',
  inkSoft:  '#4A4D55',
  muted:    '#8A8D96',
  paper:    '#FFFFFF',
  sand:     '#F4EFE7',
  sandDeep: '#EAE2D6',
  clay:     '#BE5A34',
  navy:     '#1B2A6E',
};

export function page({ title, css, body, tokens = {} }) {
  const vars = Object.entries({ ...TOKENS, ...tokens })
    .map(([k, v]) => `--${k.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase())}:${v}`)
    .join(';');
  return `<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>${title}</title>
<style>${FONT_CSS}:root{${vars}}${BASE_CSS}${css}</style></head><body>${body}</body></html>`;
}
