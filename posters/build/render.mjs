/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — рендер

     node build/render.mjs preview <набор>          → PNG+PDF превью вариантов
     node build/render.mjs build   <набор> <вариант> → все плакаты набора

   Наборы: booking (расписание и бронирование) · review (отзывы и идеи)
   ═══════════════════════════════════════════════════════════ */

import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { page } from './design.mjs';
import { VARIANTS as BOOKING_VARIANTS } from './variants.mjs';
import { VARIANTS as REVIEW_VARIANTS } from './variants-review.mjs';
import { SPACES as BOOKING_SPACES } from './content.mjs';
import { SPACES as REVIEW_SPACES } from './content-review.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const TMP = path.join(HERE, '.tmp');

const SETS = {
  booking: {
    variants: BOOKING_VARIANTS, spaces: BOOKING_SPACES, demo: 'Flagman',
    dir: 'booking', file: (s) => `Yourt_${s.id}`,
  },
  review: {
    variants: REVIEW_VARIANTS, spaces: REVIEW_SPACES, demo: 'ast-flagman',
    dir: 'review', file: (s) => `Yourt_otzyv_${s.cityLat}_${s.name.replace(/\s+/g, '_')}`,
  },
};

const MM = 96 / 25.4;                    // 1мм в CSS-пикселях
const A4 = { width: Math.round(210 * MM), height: Math.round(297 * MM) };

const html = (variantFn, space) => {
  const v = variantFn(space);
  return page({ title: `Yourt · ${space.name} · ${v.name}`, css: v.css, body: v.body, tokens: v.tokens });
};

async function open(browser, file, scale) {
  const p = await browser.newPage({ viewport: A4, ...(scale ? { deviceScaleFactor: scale } : {}) });
  await p.goto('file://' + file);
  await p.emulateMedia({ media: 'print' });
  await p.evaluate(() => document.fonts.ready);
  return p;
}

async function shot(browser, file, out, scale = 2) {
  const p = await open(browser, file, scale);
  await p.screenshot({ path: out, clip: { x: 0, y: 0, ...A4 } });
  await p.close();
}

async function pdf(browser, file, out) {
  const p = await open(browser, file);
  await p.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
                margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  await p.close();
}

async function main() {
  const [mode, setKey = 'booking', variantKey] = process.argv.slice(2);
  const set = SETS[setKey];
  if (!set) throw new Error(`Нет набора «${setKey}». Доступно: ${Object.keys(SETS).join(', ')}`);

  fs.mkdirSync(TMP, { recursive: true });
  const browser = await chromium.launch();

  if (mode === 'preview') {
    const demo = set.spaces.find((s) => s.id === set.demo);
    const dir = path.join(OUT, set.dir, '_variants');
    fs.mkdirSync(dir, { recursive: true });
    for (const [key, fn] of Object.entries(set.variants)) {
      const f = path.join(TMP, `${setKey}-${key}.html`);
      fs.writeFileSync(f, html(fn, demo));
      await shot(browser, f, path.join(dir, `${key}.png`));
      await pdf(browser, f, path.join(dir, `${key}.pdf`));
      console.log('✓', key, fn(demo).name);
    }
  }

  if (mode === 'build') {
    const fn = set.variants[variantKey];
    if (!fn) throw new Error(`Нет варианта «${variantKey}». Доступно: ${Object.keys(set.variants).join(', ')}`);
    const base = path.join(OUT, set.dir);
    const dirPdf = path.join(base, 'pdf'), dirPng = path.join(base, 'png');
    fs.mkdirSync(dirPdf, { recursive: true });
    fs.mkdirSync(dirPng, { recursive: true });
    const all = [];
    for (const s of set.spaces) {
      const doc = html(fn, s);
      const f = path.join(TMP, `${setKey}-${variantKey}-${s.id}.html`);
      fs.writeFileSync(f, doc);
      await pdf(browser, f, path.join(dirPdf, `${set.file(s)}.pdf`));
      await shot(browser, f, path.join(dirPng, `${set.file(s)}.png`), 3.125); // 300 dpi
      all.push(doc.replace(/^[\s\S]*?<body>|<\/body>[\s\S]*$/g, ''));
      console.log('✓', s.name);
    }
    /* одним файлом на печать.
       html,body жёстко заданы в 297мм под одиночный лист: для многостраничного
       файла высоту отпускаем, иначе страницы со второй обрезаются. */
    const merged = html(fn, set.spaces[0])
      .replace(/<body>[\s\S]*<\/body>/, `<body>${all.join('')}</body>`)
      .replace('</style>', 'html,body{height:auto}</style>');
    const mf = path.join(TMP, `${setKey}-${variantKey}-all.html`);
    fs.writeFileSync(mf, merged);
    await pdf(browser, mf, path.join(base, `Yourt_${set.dir}_${variantKey}_ALL.pdf`));
    console.log(`✓ сводный PDF (${set.spaces.length} страниц)`);
  }

  await browser.close();
}

main();
