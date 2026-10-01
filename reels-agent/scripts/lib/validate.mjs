/**
 * Проверка batch.json без запуска Remotion.
 * Возвращает нормализованный список рилсов (defaults подставлены).
 */
import fs from 'node:fs';
import path from 'node:path';

const PRESETS = ['classic', 'clean', 'editorial', 'caps', 'mono', 'notes'];
const POSITIONS = ['top', 'center', 'bottom'];
const ANIMATIONS = ['none', 'fade', 'pop', 'typewriter', 'lines'];

const REEL_DEFAULTS = {
  position: 'center',
  preset: 'classic',
  animation: 'fade',
  durationInSeconds: 8,
  darken: 0.25,
  endCard: null,
};

export function validateBatch(batch, {remotionDir} = {}) {
  const errors = [];
  const warnings = [];

  if (!batch || typeof batch !== 'object') return {ok: false, errors: ['batch.json: не объект'], warnings, reels: []};
  if (!batch.name) errors.push('batch.name обязателен');
  if (!Array.isArray(batch.reels) || batch.reels.length === 0) {
    errors.push('batch.reels: нужен непустой массив');
    return {ok: false, errors, warnings, reels: []};
  }

  const defaults = {...REEL_DEFAULTS, ...(batch.defaults ?? {})};
  const ids = new Set();
  const hooks = new Set();
  const footageDir = remotionDir ? path.join(remotionDir, 'public', 'footage') : null;

  const reels = batch.reels.map((r, i) => {
    const reel = {...defaults, ...r};
    const where = `reels[${i}]${r.id ? ` (${r.id})` : ''}`;

    if (!r.id || !/^[a-z0-9-]+$/.test(r.id)) errors.push(`${where}: id — только a-z, 0-9 и дефис`);
    if (ids.has(r.id)) errors.push(`${where}: дубликат id`);
    ids.add(r.id);

    if (!reel.hook || typeof reel.hook !== 'string') errors.push(`${where}: hook обязателен`);
    else {
      const plain = reel.hook.replace(/\*/g, '');
      if (plain.length > 220) errors.push(`${where}: hook длиннее 220 символов`);
      if (plain.length > 120) warnings.push(`${where}: hook длинный (${plain.length} зн.) — на телефоне будет мелко`);
      const words = plain.split(/\s+/).filter(Boolean).length;
      if (words > 16) warnings.push(`${where}: в хуке ${words} слов, лучше ≤ 12`);
      const key = plain.toLowerCase().replace(/\s+/g, ' ').trim();
      if (hooks.has(key)) warnings.push(`${where}: такой же хук уже есть в партии`);
      hooks.add(key);
      if ((reel.hook.match(/\*/g) || []).length % 2 !== 0) errors.push(`${where}: непарные звёздочки в hook`);
    }

    if (!PRESETS.includes(reel.preset)) errors.push(`${where}: preset должен быть одним из ${PRESETS.join(', ')}`);
    if (!POSITIONS.includes(reel.position)) errors.push(`${where}: position должен быть одним из ${POSITIONS.join(', ')}`);
    if (!ANIMATIONS.includes(reel.animation)) errors.push(`${where}: animation должен быть одним из ${ANIMATIONS.join(', ')}`);
    if (typeof reel.durationInSeconds !== 'number' || reel.durationInSeconds < 4 || reel.durationInSeconds > 60)
      errors.push(`${where}: durationInSeconds 4–60`);
    if (typeof reel.darken !== 'number' || reel.darken < 0 || reel.darken > 0.7) errors.push(`${where}: darken 0–0.7`);

    if (!Array.isArray(reel.clips) || reel.clips.length === 0) errors.push(`${where}: clips — непустой массив`);
    else {
      let fixed = 0;
      for (const c of reel.clips) {
        if (!c.src) errors.push(`${where}: clip без src`);
        if (c.seconds) fixed += c.seconds;
        if (footageDir && c.src && !/^https?:\/\//.test(c.src) && !c.src.startsWith('/')) {
          if (!fs.existsSync(path.join(footageDir, c.src))) errors.push(`${where}: нет файла remotion/public/footage/${c.src} (запустите scripts/prepare-footage.sh)`);
        }
      }
      if (fixed > reel.durationInSeconds) errors.push(`${where}: сумма clips.seconds больше durationInSeconds`);
    }

    if (reel.endCard) {
      if (!reel.endCard.text) errors.push(`${where}: endCard.text обязателен`);
      reel.endCard = {seconds: 2, ...reel.endCard};
      if (reel.endCard.seconds >= reel.durationInSeconds - 2) errors.push(`${where}: endCard.seconds слишком большой`);
    }

    if (reel.caption) {
      if (reel.caption.length > 2200) errors.push(`${where}: caption длиннее 2200 символов (лимит Instagram)`);
      const tags = (reel.caption.match(/#\S+/g) || []).length;
      if (tags > 8) warnings.push(`${where}: ${tags} хэштегов — достаточно 3–5`);
    } else {
      warnings.push(`${where}: нет caption — описание придётся писать руками`);
    }
    if (!reel.keyword) warnings.push(`${where}: нет keyword — проверьте, что в описании есть кодовое слово для бота`);

    return reel;
  });

  return {ok: errors.length === 0, errors, warnings, reels};
}
