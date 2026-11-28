/* Дата-арт глав Reels, формат 6. Решения владельца 28.11: элементы — предметы темы (значки), они
   складываются в силуэт темы; в главе обязательно сравнение двух групп, время и одна крупная цифра;
   нет цифр в источнике — нет главы. Стиль — по её референсам: кремовый фон, цвет рубрики и
   фиолетово-синий, постоянная жизнь (дыхание, прорисовка, наезд камеры).
   Кадр — чистая функция от времени: drawArt(canvas, ch, prev, lt, gt, seed). */
(function () {
  const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
  const ease = x => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
  const inout = x => { x = clamp(x, 0, 1); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const lerp = (a, b, k) => a + (b - a) * k;
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const DISPLAY = '"TT Firs Neue", Montserrat, sans-serif';

  function colors() {
    const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim();
    return { accent: v('--accent') || '#ff954c', accent2: v('--periwinkle') || '#556bb8', navy: v('--navy') || '#28348a',
             ink: v('--ink') || '#2b3350', muted: '#d6ccbb', cream: v('--cream') || '#f6efe4' };
  }

  // ---------- значки: простые формы, читаются и в 30 px ----------
  function icon(ctx, kind, x, y, s, fill, stroke) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s / 24, s / 24);
    ctx.fillStyle = fill; ctx.strokeStyle = stroke || fill; ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const C = (cx, cy, r) => { ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill(); };
    const R = (x0, y0, w, h, r) => { ctx.beginPath(); ctx.roundRect(x0, y0, w, h, r || 0); ctx.fill(); };
    switch (kind) {
      case 'eye':
        ctx.beginPath(); ctx.moveTo(-12, 0); ctx.quadraticCurveTo(0, -11, 12, 0); ctx.quadraticCurveTo(0, 11, -12, 0); ctx.fill();
        ctx.fillStyle = '#fff'; C(0, 0, 5); ctx.fillStyle = stroke || '#222'; C(0, 0, 2.6); break;
      case 'glasses':
        ctx.lineWidth = 3; ctx.strokeStyle = fill; ctx.beginPath(); ctx.arc(-6, 2, 5, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(6, 2, 5, 0, 7); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(-1, 1); ctx.quadraticCurveTo(0, -1, 1, 1); ctx.moveTo(-11, 0); ctx.lineTo(-12, -4); ctx.moveTo(11, 0); ctx.lineTo(12, -4); ctx.stroke(); break;
      case 'house':
        ctx.beginPath(); ctx.moveTo(-11, -1); ctx.lineTo(0, -11); ctx.lineTo(11, -1); ctx.closePath(); ctx.fill(); R(-8, -2, 16, 13);
        ctx.fillStyle = '#fff'; R(-2, 4, 4, 7); break;
      case 'window':
        R(-10, -11, 20, 22, 2); ctx.fillStyle = '#fff'; R(-7, -8, 6, 7); R(1, -8, 6, 7); R(-7, 1, 6, 7); R(1, 1, 6, 7); break;
      case 'door': R(-7, -11, 14, 22, 2); ctx.fillStyle = '#fff'; C(3.5, 1, 1.6); break;
      case 'heart':
        ctx.beginPath(); ctx.moveTo(0, 10); ctx.bezierCurveTo(-14, 0, -10, -12, 0, -5); ctx.bezierCurveTo(10, -12, 14, 0, 0, 10); ctx.fill(); break;
      case 'cup':
        R(-9, -5, 14, 14, 3); ctx.strokeStyle = fill; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(7, 2, 4, -1.3, 1.3); ctx.stroke();
        ctx.lineWidth = 1.8; ctx.beginPath(); ctx.moveTo(-4, -8); ctx.quadraticCurveTo(-6, -11, -3, -13); ctx.moveTo(1, -8); ctx.quadraticCurveTo(-1, -11, 2, -13); ctx.stroke(); break;
      case 'phone': R(-6, -11, 12, 22, 3); ctx.fillStyle = '#fff'; R(-4, -8, 8, 14, 1); break;
      case 'book':
        ctx.beginPath(); ctx.moveTo(0, -6); ctx.lineTo(-11, -9); ctx.lineTo(-11, 8); ctx.lineTo(0, 11); ctx.lineTo(11, 8); ctx.lineTo(11, -9); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.beginPath(); ctx.moveTo(0, -5); ctx.lineTo(0, 10); ctx.stroke(); break;
      case 'hand': R(-7, -2, 14, 13, 4); for (let k = 0; k < 4; k++) R(-7 + k * 3.7, -11 + (k % 3), 3.2, 11, 1.6); R(5, 0, 6, 3.5, 1.7); break;
      case 'tree': C(0, -5, 8); C(-5, -1, 5); C(5, -1, 5); R(-1.6, 2, 3.2, 10); break;
      case 'bench': R(-11, -4, 22, 3.5, 1); R(-11, 2, 22, 3.5, 1); R(-9, 5, 2.5, 7); R(6.5, 5, 2.5, 7); break;
      case 'pill': ctx.rotate(-0.6); R(-11, -5, 22, 10, 5); ctx.fillStyle = '#fff'; ctx.globalAlpha *= 0.5; R(0, -5, 11, 10, 5); break;
      case 'dog': C(-2, 1, 7); C(7, -5, 4.5); R(-9, 5, 3, 7, 1); R(3, 5, 3, 7, 1); C(9.5, -8.5, 2); break;
      case 'elder':
        C(0, -8, 4); R(-5, -3, 10, 10, 4); R(-4.5, 6, 3.4, 7, 1.5); R(1.1, 6, 3.4, 7, 1.5);
        ctx.strokeStyle = fill; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(8, -1); ctx.lineTo(9, 13); ctx.moveTo(8, -1); ctx.quadraticCurveTo(8, -4, 5.5, -3); ctx.stroke(); break;
      default:   // person
        C(0, -8, 4.3); ctx.beginPath(); ctx.moveTo(-7, 12); ctx.quadraticCurveTo(-7, -2, 0, -2); ctx.quadraticCurveTo(7, -2, 7, 12); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }

  // ---------- силуэты: в какую форму складываются значки ----------
  function inside(shape, u, v) {          // u, v в [-1, 1]
    if (shape === 'eye') return Math.abs(v) < 0.62 * (1 - u * u) && Math.abs(u) < 0.98;
    if (shape === 'house') return (v > -0.05 && Math.abs(u) < 0.72) || (v <= -0.05 && v > -0.95 && Math.abs(u) < 0.95 * (v + 0.95) / 0.9);
    if (shape === 'heart') { const x = u * 1.15, y = -v * 1.15 + 0.25; return Math.pow(x * x + y * y - 1, 3) - x * x * y * y * y <= 0; }
    if (shape === 'head') return (u * u) / 0.5 + ((v + 0.12) * (v + 0.12)) / 0.62 < 1 || (v > 0.45 && Math.abs(u) < 0.32 + (v - 0.45) * 1.6);
    return u * u + v * v < 1;
  }
  const layoutCache = {};
  function silhouettePts(shape, n, seed) {   // сетка со сдвигом внутри силуэта, ровно n точек
    const key = shape + n + '/' + seed; if (layoutCache[key]) return layoutCache[key];
    let step = 0.18, pts = [];
    for (let iter = 0; iter < 30; iter++) {
      pts = [];
      let row = 0;
      for (let v = -1; v <= 1; v += step * 0.87, row++) for (let u = -1 + (row % 2 ? step / 2 : 0); u <= 1; u += step)
        if (inside(shape, u, v)) pts.push([u, v]);
      if (pts.length >= n && pts.length < n * 1.15) break;
      step *= Math.sqrt(pts.length / n);
    }
    const r = rng(seed);
    while (pts.length > n) pts.splice(Math.floor(r() * pts.length), 1);
    layoutCache[key] = { pts, step }; return layoutCache[key];
  }
  function shuffled(n, seed) { const r = rng(seed), o = [...Array(n).keys()];
    for (let i = n - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [o[i], o[j]] = [o[j], o[i]]; } return o; }

  // ---------- общие части ----------
  function bigNumber(ctx, C, ch, W, lt, y) {   // одна крупная цифра главы с расшифровкой
    const q = ease(lt / 0.5); if (q <= 0) return;
    const raw = ch.big || '', mm = raw.match(/\d[\d\s ]*(?:[.,]\d+)?/);
    let txt = raw;
    if (mm) { const val = parseFloat(mm[0].replace(/[\s ]/g, '').replace(',', '.')), dec = (mm[0].split(/[.,]/)[1] || '').length;
      let v = (val * ease(lt / 0.9)).toFixed(dec).replace('.', ','); if (v.length > 4) v = v.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
      txt = raw.replace(mm[0], v); }
    ctx.save(); ctx.globalAlpha = q; ctx.textAlign = 'center';
    ctx.fillStyle = C.accent; ctx.font = `800 ${raw.length > 7 ? 120 : 150}px ${DISPLAY}`; ctx.fillText(txt, W / 2, y);
    ctx.fillStyle = C.ink; ctx.font = '700 38px Montserrat, sans-serif'; ctx.fillText(ch.big_caption || '', W / 2, y + 60);
    ctx.restore();
  }
  function label(ctx, C, text, x, y, color, a, size) {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.textAlign = 'center'; ctx.fillStyle = color || C.navy;
    ctx.font = `800 ${size || 40}px Montserrat, sans-serif`; ctx.fillText(text, x, y); ctx.restore();
  }
  function legend(ctx, C, ch, W, y) {
    if (!ch.unit) return;
    ctx.save(); ctx.fillStyle = C.ink; ctx.globalAlpha = 0.7; ctx.font = '600 28px Montserrat, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(ch.unit, W / 2, y); ctx.restore();
  }

  // ---------- compare: две группы рядом, доля с признаком загорается ----------
  function drawCompare(ctx, C, W, H, ch, prev, lt, gt, seed) {
    const groups = (ch.groups || []).slice(0, 2), N = 60, cy = H * 0.5;
    groups.forEach((g, gi) => {
      const two = groups.length > 1, cx = two ? (gi ? W * 0.75 : W * 0.25) : W / 2, R = two ? 210 : 300;
      const lay = silhouettePts(ch.silhouette || 'circle', N, seed), sz = R * lay.step * 0.9;
      const hot = new Set(shuffled(N, seed + 31).slice(0, Math.round(clamp(g.value, 0, 100) / 100 * N)));
      const lit = ease((lt - 1.0 - gi * 0.35) / 0.5);
      lay.pts.forEach(([u, v], i) => {
        const pop = prev ? 1 : ease((lt - 0.15 - i * 0.01 - gi * 0.25) / 0.3);
        if (pop <= 0) return;
        const x = cx + u * R + Math.sin(gt * 1.1 + i) * 1.5, y = cy + v * R + Math.cos(gt * 0.9 + i * 1.7) * 1.5;
        const isHot = hot.has(i) && lit > 0;
        ctx.globalAlpha = isHot ? 1 : lerp(1, 0.55, lit);
        icon(ctx, ch.icon, x, y, sz * pop * (isHot ? 1 + 0.08 * (1 + Math.sin(gt * 3 + i)) / 2 : 1),
             isHot ? (gi === 0 ? C.accent : C.accent2) : C.muted, isHot ? C.navy : '#fff');
      });
      ctx.globalAlpha = 1;
      label(ctx, C, g.label, cx, cy - R - 50, gi === 0 ? C.navy : C.accent2, ease((lt - 0.3 - gi * 0.25) / 0.4), 38);
      const q = ease((lt - 1.1 - gi * 0.35) / 0.8);      // доля под группой набегает
      label(ctx, C, Math.round(clamp(g.value, 0, 100) * q) + '%', cx, cy + R + 90, gi === 0 ? C.accent : C.accent2, q, 76);
    });
    if (groups.length > 1) label(ctx, C, 'vs', W / 2, cy + 20, C.ink, 0.5 * ease((lt - 0.6) / 0.4), 44);
    bigNumber(ctx, C, ch, W, lt - 1.8, H * 0.24);
  }

  // ---------- timeline: годы на оси, две линии расходятся ----------
  function drawTimeline(ctx, C, W, H, ch, prev, lt, gt) {
    const groups = (ch.groups || []).slice(0, 2), x0 = 130, x1 = W - 130, y0 = H * 0.66, y1 = H * 0.36;
    const years = ch.years && ch.years.length === 2 ? ch.years : null;
    const axq = ease(lt / 0.5);
    ctx.save(); ctx.strokeStyle = C.ink; ctx.fillStyle = C.ink; ctx.globalAlpha = 0.6; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(lerp(x0, x1, axq), y0); ctx.stroke();
    if (years) {
      ctx.globalAlpha = axq; ctx.font = '700 34px Montserrat, sans-serif'; ctx.textAlign = 'center';
      const span = Math.max(years[1] - years[0], 1), stepY = span > 12 ? 5 : (span > 6 ? 2 : 1);
      for (let yv = years[0]; yv <= years[1]; yv += stepY) { const x = lerp(x0, x1, (yv - years[0]) / span);
        ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y0 + 14); ctx.stroke(); ctx.fillText(String(yv), x, y0 + 56); }
    }
    ctx.restore();
    const vmax = Math.max(1, ...groups.map(g => Math.max(g.value, g.start || 0))) * 1.15;
    groups.forEach((g, gi) => {
      const draw = ease((lt - 0.5 - gi * 0.3) / 1.6), col = gi === 0 ? C.accent : C.accent2;
      const ya = lerp(y0, y1, (g.start || 0) / vmax), yb = lerp(y0, y1, g.value / vmax);
      const pts = []; for (let k = 0; k <= 40; k++) { const u = k / 40; pts.push([lerp(x0, x1, u), lerp(ya, yb, u) + Math.sin(u * 9 + gi) * 5 * Math.sin(u * 3.14)]); }
      const n = Math.max(2, Math.ceil(pts.length * draw));
      ctx.save();
      const gr = ctx.createLinearGradient(0, y1, 0, y0); gr.addColorStop(0, col); gr.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.globalAlpha = 0.2; ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(x0, y0);
      pts.slice(0, n).forEach(p => ctx.lineTo(p[0], p[1])); ctx.lineTo(pts[n - 1][0], y0); ctx.closePath(); ctx.fill();
      ctx.globalAlpha = 1; ctx.strokeStyle = col; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath(); pts.slice(0, n).forEach((p, k) => k ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.stroke(); ctx.restore();
      const end = pts[n - 1];
      icon(ctx, ch.icon, end[0], end[1], 62 * (0.92 + 0.08 * Math.sin(gt * 3 + gi)), col, '#fff');
      label(ctx, C, g.label, clamp(end[0] - 150, 220, W - 220), end[1] + (gi === 0 ? -56 : 80), col, ease((lt - 2.1 - gi * 0.3) / 0.4), 36);
    });
    bigNumber(ctx, C, ch, W, lt - 1.8, H * 0.21);
  }

  // ---------- scale: силуэт из сотен значков-участников, счётчик ----------
  function drawScale(ctx, C, W, H, ch, prev, lt, gt, seed) {
    const N = 150, lay = silhouettePts(ch.silhouette || 'circle', N, seed), R = 320, cx = W / 2, cy = H * 0.53;
    const g = (ch.groups || [])[0], sz = R * lay.step * 0.9;
    const hot = new Set(shuffled(N, seed + 5).slice(0, g ? Math.round(clamp(g.value, 0, 100) / 100 * N) : 0));
    const lit = ease((lt - 1.6) / 0.5);
    lay.pts.forEach(([u, v], i) => {
      const pop = prev ? 1 : ease((lt - Math.hypot(u, v) * 0.9) / 0.35);   // волна от центра
      if (pop <= 0) return;
      const isHot = hot.has(i) && lit > 0;
      ctx.globalAlpha = isHot ? 1 : lerp(1, 0.6, lit);
      icon(ctx, ch.icon, cx + u * R + Math.sin(gt + i) * 1.5, cy + v * R + Math.cos(gt * 0.8 + i) * 1.5, sz * pop,
           isHot ? C.accent : (i % 3 ? C.accent2 : C.navy), '#fff');
    });
    ctx.globalAlpha = 1;
    bigNumber(ctx, C, ch, W, lt - 0.5, H * 0.21);
    // доля с признаком — цветом и подписью под расшифровкой цифры
    if (g) label(ctx, C, `● ${g.label} — ${Math.round(clamp(g.value, 0, 100))}%`, cx, H * 0.21 + 120, C.accent, ease((lt - 1.8) / 0.4), 36);
  }

  window.drawArt = function (canvas, ch, prev, lt, gt, seed) {
    if (!ch) return;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (canvas.width !== W) { canvas.width = W; canvas.height = H; }
    const ctx = canvas.getContext('2d'), C = colors();
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, W, H);
    const same = prev && prev.chart === ch.chart && prev.icon === ch.icon ? prev : null;
    // камера медленно наезжает (10% за главу), фигура всё время живая
    const z = 1 + 0.1 * inout(lt / 5), fx = W / 2, fy = H * 0.5;
    ctx.translate(fx, fy); ctx.scale(z, z); ctx.translate(-fx, -fy);
    if (ch.chart === 'timeline') drawTimeline(ctx, C, W, H, ch, same, lt, gt);
    else if (ch.chart === 'scale') drawScale(ctx, C, W, H, ch, same, lt, gt, seed || 7);
    else drawCompare(ctx, C, W, H, ch, same, lt, gt, seed || 7);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    legend(ctx, C, ch, W, H * 0.31);
  };
  window.drawIcon = icon;
})();
