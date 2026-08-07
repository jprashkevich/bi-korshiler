/* ═══════════════════════════════════════════════════════════
   YOURT · A4 POSTERS — рендер
     node build/render.mjs preview        → PNG превью 4 вариантов
     node build/render.mjs build <v1..v4> → 13 PDF + PNG выбранного варианта
   ═══════════════════════════════════════════════════════════ */

import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { page } from './design.mjs';
import { VARIANTS } from './variants.mjs';
import { SPACES } from './content.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const TMP = path.join(HERE, '.tmp');

const MM = 96 / 25.4;                    // 1мм в CSS-пикселях
const A4 = { width: Math.round(210 * MM), height: Math.round(297 * MM) };

const html = (variantFn, space) => {
  const v = variantFn(space);
  return page({ title: `Yourt · ${space.name} · ${v.name}`, css: v.css, body: v.body, tokens: v.tokens });
};

async function shot(browser, file, out, { scale = 2 } = {}) {
  const p = await browser.newPage({ viewport: A4, deviceScaleFactor: scale });
  await p.goto('file://' + file);
  await p.emulateMedia({ media: 'print' });
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: out, clip: { x: 0, y: 0, ...A4 } });
  await p.close();
}

async function pdf(browser, file, out) {
  const p = await browser.newPage({ viewport: A4 });
  await p.goto('file://' + file);
  await p.emulateMedia({ media: 'print' });
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
                margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  await p.close();
}

async function main() {
  const [mode, arg] = process.argv.slice(2);
  fs.mkdirSync(TMP, { recursive: true });
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();

  if (mode === 'preview') {
    const demo = SPACES.find((s) => s.id === 'Flagman');
    const dir = path.join(OUT, '_variants');
    fs.mkdirSync(dir, { recursive: true });
    for (const [key, fn] of Object.entries(VARIANTS)) {
      const f = path.join(TMP, `${key}.html`);
      fs.writeFileSync(f, html(fn, demo));
      await shot(browser, f, path.join(dir, `${key}.png`), { scale: Number(arg) || 2 });
      await pdf(browser, f, path.join(dir, `${key}.pdf`));
      console.log('✓', key, fn(demo).name);
    }
  }

  if (mode === 'build') {
    const key = arg || 'v1';
    const fn = VARIANTS[key];
    if (!fn) throw new Error(`Нет варианта «${key}». Доступно: ${Object.keys(VARIANTS).join(', ')}`);
    const dirPdf = path.join(OUT, 'pdf'), dirPng = path.join(OUT, 'png');
    fs.mkdirSync(dirPdf, { recursive: true });
    fs.mkdirSync(dirPng, { recursive: true });
    const all = [];
    for (const s of SPACES) {
      const f = path.join(TMP, `${key}-${s.id}.html`);
      fs.writeFileSync(f, html(fn, s));
      await pdf(browser, f, path.join(dirPdf, `Yourt_${s.id}.pdf`));
      await shot(browser, f, path.join(dirPng, `Yourt_${s.id}.png`), { scale: 3.125 }); // 300 dpi
      all.push(html(fn, s).replace(/^[\s\S]*?<body>|<\/body>[\s\S]*$/g, ''));
      console.log('✓', s.name);
    }
    /* одним файлом на печать — 13 страниц.
       html,body жёстко заданы в 297мм под одиночный лист: для многостраничного
       файла высоту отпускаем, иначе страницы со второй обрезаются. */
    const merged = html(fn, SPACES[0])
      .replace(/<body>[\s\S]*<\/body>/, `<body>${all.join('')}</body>`)
      .replace('</style>', 'html,body{height:auto}</style>');
    const mf = path.join(TMP, `${key}-all.html`);
    fs.writeFileSync(mf, merged);
    await pdf(browser, mf, path.join(OUT, `Yourt_posters_${key}_ALL.pdf`));
    console.log('✓ сводный PDF (13 страниц)');
  }

  await browser.close();
}

main();
