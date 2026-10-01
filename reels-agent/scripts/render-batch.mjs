#!/usr/bin/env node
/**
 * Рендер целой партии рилсов из batch.json.
 *
 *   node scripts/render-batch.mjs batches/2026-10-01-batch-01
 *   node scripts/render-batch.mjs batches/2026-10-01-batch-01 --only intro-01,intro-02
 *   node scripts/render-batch.mjs batches/2026-10-01-batch-01 --dry      # только проверка
 *   node scripts/render-batch.mjs batches/2026-10-01-batch-01 --stills   # png-превью вместо mp4
 *
 * Результат: <batch>/out/<id>.mp4 и <batch>/out/captions/<id>.txt
 */
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const agentRoot = path.resolve(here, '..');
const remotionDir = path.join(agentRoot, 'remotion');
const require = createRequire(path.join(remotionDir, 'package.json'));

const args = process.argv.slice(2);
const batchArg = args.find((a) => !a.startsWith('--'));
if (!batchArg) {
  console.error('Укажите папку партии: node scripts/render-batch.mjs batches/<имя>');
  process.exit(1);
}
const flag = (name) => args.includes(`--${name}`);
const opt = (name) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
};

const batchDir = path.resolve(process.cwd(), batchArg);
const batchFile = path.join(batchDir, 'batch.json');
if (!fs.existsSync(batchFile)) {
  console.error(`Не найден ${batchFile}`);
  process.exit(1);
}

// ---------- валидация
const {validateBatch} = await import('./lib/validate.mjs');
const raw = JSON.parse(fs.readFileSync(batchFile, 'utf8'));
const {ok, errors, warnings, reels} = validateBatch(raw, {remotionDir});
for (const w of warnings) console.warn(`⚠️  ${w}`);
if (!ok) {
  for (const e of errors) console.error(`❌ ${e}`);
  process.exit(1);
}
console.log(`✅ batch.json валиден: ${reels.length} рилсов`);

// ---------- описания в текстовые файлы (удобно копировать с телефона)
const outDir = path.join(batchDir, 'out');
const capDir = path.join(outDir, 'captions');
fs.mkdirSync(capDir, {recursive: true});
for (const r of reels) {
  if (r.caption) fs.writeFileSync(path.join(capDir, `${r.id}.txt`), r.caption.trim() + '\n');
}

if (flag('dry')) {
  console.log('--dry: рендер пропущен.');
  process.exit(0);
}

// ---------- рендер
const only = opt('only')?.split(',').map((s) => s.trim()).filter(Boolean);
const todo = only ? reels.filter((r) => only.includes(r.id)) : reels;
if (todo.length === 0) {
  console.error('Нечего рендерить (проверьте --only).');
  process.exit(1);
}

const {bundle} = require('@remotion/bundler');
const {renderMedia, renderStill, selectComposition} = require('@remotion/renderer');

console.log('📦 Сборка Remotion-бандла…');
const serveUrl = await bundle({
  entryPoint: path.join(remotionDir, 'src/index.ts'),
  publicDir: path.join(remotionDir, 'public'),
  onProgress: () => {},
});

const started = Date.now();
let done = 0;
for (const reel of todo) {
  const {caption, keyword, pattern, ...rest} = reel;
  // Явно обнуляем необязательные поля, чтобы defaultProps из Root.tsx не просачивались в рендер
  const inputProps = {subtext: null, endCard: null, colors: null, fontSize: null, ...rest};
  const composition = await selectComposition({serveUrl, id: 'Reel', inputProps});
  const t0 = Date.now();
  if (flag('stills')) {
    const output = path.join(outDir, `${reel.id}.png`);
    await renderStill({composition, serveUrl, output, inputProps, frame: Math.round(composition.fps * 1.5)});
    console.log(`🖼  ${reel.id}.png`);
  } else {
    const output = path.join(outDir, `${reel.id}.mp4`);
    let lastPct = -1;
    await renderMedia({
      composition,
      serveUrl,
      codec: 'h264',
      crf: 18,
      outputLocation: output,
      inputProps,
      concurrency: opt('concurrency') ? Number(opt('concurrency')) : undefined,
      onProgress: ({progress}) => {
        const pct = Math.floor(progress * 10) * 10;
        if (pct !== lastPct) {
          lastPct = pct;
          if (process.stdout.isTTY) process.stdout.write(`\r🎬 ${reel.id}  ${pct}%   `);
          else if (pct % 50 === 0) console.log(`🎬 ${reel.id}  ${pct}%`);
        }
      },
    });
    console.log(`${process.stdout.isTTY ? '\r' : ''}🎬 ${reel.id}.mp4  ✓  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  done++;
}

console.log(`\nГотово: ${done} файлов за ${((Date.now() - started) / 1000).toFixed(0)}s → ${path.relative(process.cwd(), outDir)}`);
console.log('Описания: ' + path.relative(process.cwd(), capDir));
