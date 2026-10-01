#!/usr/bin/env node
/**
 * Создаёт папку новой партии с заготовкой batch.json.
 *   node scripts/new-batch.mjs            → batches/YYYY-MM-DD-batch-NN
 *   node scripts/new-batch.mjs my-name    → batches/my-name
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const batchesDir = path.join(root, 'batches');
fs.mkdirSync(batchesDir, {recursive: true});

let name = process.argv[2];
if (!name) {
  const day = new Date().toISOString().slice(0, 10);
  const existing = fs.readdirSync(batchesDir).filter((d) => d.startsWith(`${day}-batch-`)).length;
  name = `${day}-batch-${String(existing + 1).padStart(2, '0')}`;
}
const dir = path.join(batchesDir, name);
if (fs.existsSync(dir)) {
  console.error(`Папка уже существует: ${dir}`);
  process.exit(1);
}
fs.mkdirSync(dir);

const footage = fs
  .readdirSync(path.join(root, 'remotion', 'public', 'footage'))
  .filter((f) => /\.(mp4|mov|webm)$/i.test(f));

const skeleton = {
  name,
  lang: 'ru',
  defaults: {
    preset: 'classic',
    position: 'center',
    animation: 'fade',
    durationInSeconds: 8,
    darken: 0.25,
    endCard: null,
  },
  reels: [
    {
      id: 'example-01',
      pattern: 'contrast',
      hook: 'Замените этот текст\nна *хук* из банка',
      subtext: 'и удалите subtext, если не нужен',
      clips: [{src: footage[0] ?? 'sample.mp4'}],
      keyword: 'ГАЙД',
      caption: 'Описание рилса.\n\nНапиши «ГАЙД» в комментариях — пришлю в директ.',
    },
  ],
};
fs.writeFileSync(path.join(dir, 'batch.json'), JSON.stringify(skeleton, null, 2) + '\n');
fs.writeFileSync(
  path.join(dir, 'NOTES.md'),
  `# ${name}\n\n- Гипотеза партии: \n- Паттерны хуков: \n- Футажи: ${footage.join(', ') || '(нет)'}\n- Что проверяем: \n`,
);
console.log(`Создано: ${path.relative(process.cwd(), dir)}`);
console.log(footage.length ? `Доступные футажи: ${footage.join(', ')}` : 'Футажей пока нет — положите видео в footage/raw и запустите scripts/prepare-footage.sh');
