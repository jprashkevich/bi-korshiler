#!/usr/bin/env node
/** Быстрая проверка batch.json: node scripts/validate-batch.mjs batches/<имя> */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateBatch} from './lib/validate.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const remotionDir = path.resolve(here, '..', 'remotion');
const dir = process.argv[2];
if (!dir) {
  console.error('Использование: node scripts/validate-batch.mjs batches/<имя>');
  process.exit(1);
}
const file = path.resolve(process.cwd(), dir, 'batch.json');
const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
const {ok, errors, warnings, reels} = validateBatch(raw, {remotionDir});
warnings.forEach((w) => console.warn('⚠️ ', w));
errors.forEach((e) => console.error('❌', e));
console.log(ok ? `✅ OK — ${reels.length} рилсов` : `❌ ${errors.length} ошибок`);
process.exit(ok ? 0 : 1);
