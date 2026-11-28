/* Дата-арт глав Reels, формат 6 (config/reels-motion.md, §7–8; референсы владельца 28.11:
   орбиты со связями, плотное облако точек, «одуванчик» с выносками, градиентные кольца).
   Почему отдельный движок, а не viz.js: там фигуры для карусели и карточек — 10–50 значков, статичные.
   Главе на весь экран нужны плотность (сотни элементов), градиенты, тонкие выноски и постоянная жизнь.
   Кадр — чистая функция от времени: drawArt(canvas, spec, prev, lt, gt), где lt — время от начала главы,
   gt — время ролика (дыхание, вращение). prev — состояние прошлой главы: новая глава продолжает его. */
(function () {
  const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
  const ease = x => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
  const inout = x => { x = clamp(x, 0, 1); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const lerp = (a, b, k) => a + (b - a) * k;
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const GOLD = 137.50776 * Math.PI / 180;

  function colors() {
    const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim();
    return { accent: v('--accent') || '#ff954c', accent2: v('--periwinkle') || '#556bb8', navy: v('--navy') || '#28348a',
             ink: v('--ink') || '#2b3350', muted: '#d9cfbf', cream: v('--cream') || '#f6efe4' };
  }
  function family(kind) {
    if (kind === 'network' || kind === 'dandelion') return 'orbit';
    if (kind === 'rings' || kind === 'peaks' || kind === 'donut') return 'arcs';
    return 'cloud';
  }
  const share = spec => clamp(((spec.groups || [])[0] || {}).value || 0, 0, 100);

  // ---------- выноска: тонкая линия от элемента к подписи, кружок на конце (как в референсах) ----------
  function callout(ctx, C, from, to, value, label, p) {
    if (p <= 0) return;
    const q = ease(p / 0.5);
    ctx.save();
    ctx.strokeStyle = C.ink; ctx.lineWidth = 2.5; ctx.globalAlpha = 0.85;
    const mx = lerp(from[0], to[0], 0.55), my = to[1];
    ctx.beginPath(); ctx.moveTo(from[0], from[1]);
    const seg1 = Math.hypot(mx - from[0], my - from[1]), seg2 = Math.abs(to[0] - mx), L = (seg1 + seg2) * q;
    if (L <= seg1) ctx.lineTo(lerp(from[0], mx, L / seg1), lerp(from[1], my, L / seg1));
    else { ctx.lineTo(mx, my); ctx.lineTo(lerp(mx, to[0], (L - seg1) / Math.max(seg2, 1)), my); }
    ctx.stroke();
    ctx.globalAlpha = 1; ctx.fillStyle = C.ink;
    ctx.beginPath(); ctx.arc(from[0], from[1], 6, 0, 7); ctx.fill();
    if (q >= 1) { ctx.beginPath(); ctx.arc(to[0], to[1], 9, 0, 7); ctx.fillStyle = C.cream; ctx.fill(); ctx.stroke(); }
    const t2 = ease((p - 0.35) / 0.4);
    if (t2 > 0) {
      const right = to[0] > 540, x = to[0] + (right ? -18 : 18);
      ctx.globalAlpha = t2; ctx.textAlign = right ? 'right' : 'left';
      ctx.fillStyle = C.accent; ctx.font = '800 104px "TT Firs Neue", Montserrat, sans-serif';
      ctx.fillText(value, x, to[1] - 22);
      ctx.fillStyle = C.ink; ctx.font = '700 34px Montserrat, sans-serif';
      wrap(ctx, label, x, to[1] + 48, 380, 40, right);
    }
    ctx.restore();
  }
  function wrap(ctx, text, x, y, maxW, lh, right) {
    const words = (text || '').split(' '); let line = '', yy = y;
    words.forEach(w => { const test = line ? line + ' ' + w : w;
      if (ctx.measureText(test).width > maxW && line) { ctx.fillText(line, x, yy); line = w; yy += lh; } else line = test; });
    if (line) ctx.fillText(line, x, yy);
  }
  function legend(ctx, C, spec, W, H) {
    const txt = [spec.unit, spec.conditional ? 'условная схема' : ''].filter(Boolean).join(' · ');
    if (!txt) return;
    ctx.save(); ctx.fillStyle = C.ink; ctx.globalAlpha = 0.7; ctx.font = '600 28px Montserrat, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(txt, W / 2, H - 70); ctx.restore();
  }
  function fmtValue(spec, k) {
    const v = share(spec); return Math.round(v * k) + '%';
  }

  // ---------- облако: сотни кружков разного размера, доля — цветом ----------
  const CLOUD_N = 230;
  function cloudPlan(seed) {
    const r = rng(seed), pts = [], order = [];
    for (let i = 0; i < CLOUD_N; i++) {
      const big = r() < 0.07;
      pts.push({ a: i * GOLD, d: Math.sqrt((i + 0.5) / CLOUD_N), s: big ? 1.7 + r() * 0.5 : 0.55 + r() * 0.75,
                 ph: r() * 6.28, from: r() * 6.28 });
      order.push(i);
    }
    for (let i = order.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
    return { pts, order };
  }
  function cloudOwner(plan, spec) {           // 0 — главная группа, 1 — вторая, -1 — остальные
    const own = new Array(CLOUD_N).fill(-1); let k = 0;
    (spec.groups || []).slice(0, 2).forEach((g, gi) => {
      const n = Math.round(clamp(g.value, 0, 100) / 100 * CLOUD_N);
      for (let m = 0; m < n && k < CLOUD_N; m++, k++) own[plan.order[k]] = gi;
    });
    return own;
  }
  function cloudPos(plan, own, spec, W, H) {
    const cx = W / 2, cy = H * 0.5, R = Math.min(W, H) * 0.38, base = R * Math.sqrt(Math.PI / CLOUD_N) * 0.46;
    if (spec.mode !== 'split') return plan.pts.map(p => [cx + R * p.d * Math.cos(p.a), cy + R * p.d * Math.sin(p.a), base * p.s]);
    // разлёт: каждая группа — своё облако, площадь по доле
    const groups = [0, 1, -1].filter(g => own.includes(g)), out = new Array(CLOUD_N);
    const counts = groups.map(g => own.filter(o => o === g).length), total = counts.reduce((a, b) => a + b, 0);
    let rrs = counts.map(c => Math.max(R * 0.95 * Math.sqrt(c / total), 60));
    const used = rrs.reduce((a, r) => a + 2 * r, 0) + 40 * (rrs.length - 1), k = Math.min(1, W * 0.9 / used);
    rrs = rrs.map(r => r * k);
    let x = (W - used * k) / 2;                  // облака по центру и целиком в кадре
    groups.forEach((g, gi) => {
      const rr = rrs[gi], gx = x + rr; x += 2 * rr + 40 * k;
      let m = 0;
      plan.pts.forEach((p, i) => { if (own[i] !== g) return;
        const d = Math.sqrt((m + 0.5) / counts[gi]), a = m * GOLD; m++;
        out[i] = [gx + rr * d * Math.cos(a), cy + (gi % 2 ? 60 : -30) + rr * d * Math.sin(a), base * p.s * 0.95 * Math.max(k, 0.8)]; });
    });
    return out;
  }
  function drawCloud(ctx, C, W, H, spec, prev, lt, gt, seed) {
    const plan = cloudPlan(seed), own = cloudOwner(plan, spec), pos = cloudPos(plan, own, spec, W, H);
    const pOwn = prev ? cloudOwner(plan, prev) : own, pPos = prev ? cloudPos(plan, pOwn, prev, W, H) : null;
    const mv = prev ? inout(lt / 0.8) : 1, hl = spec.mode === 'highlight' || spec.mode === 'split';
    const dim = hl ? ease(lt / 0.45) : 0, pdim = prev && (prev.mode === 'highlight' || prev.mode === 'split') ? 1 : 0;
    const dimNow = lerp(pdim, hl ? 1 : 0, prev ? ease(lt / 0.45) : dim);
    let target = null, tBest = -1;
    plan.pts.forEach((p, i) => {
      let [x, y, r] = pos[i];
      if (pPos) { x = lerp(pPos[i][0], x, mv); y = lerp(pPos[i][1], y, mv); }
      else {                                   // сборка: кружки слетаются с краёв, волной от центра
        const k = ease((lt - p.d * 0.7) / 0.6), fx = W / 2 + Math.cos(p.from) * 1300, fy = H / 2 + Math.sin(p.from) * 1300;
        x = lerp(fx, x, k); y = lerp(fy, y, k); r *= k;
      }
      x += Math.sin(gt * 0.9 + p.ph) * 3; y += Math.cos(gt * 0.7 + p.ph * 1.3) * 3;   // дыхание
      if (r <= 0.3) return;
      const g = own[i], main = g === 0;
      ctx.globalAlpha = g === -1 ? lerp(0.95, 0.35, dimNow) : (g === 1 ? lerp(1, 0.55, dimNow) : 1);
      if (g === -1) ctx.fillStyle = C.muted;
      else {
        const gr = ctx.createRadialGradient(x - r * 0.35, y - r * 0.35, r * 0.1, x, y, r);
        gr.addColorStop(0, main ? C.accent : C.accent2); gr.addColorStop(1, main ? C.accent2 : C.navy);
        ctx.fillStyle = gr;
      }
      ctx.beginPath(); ctx.arc(x, y, r * (main ? 1 + 0.12 * dimNow : 1), 0, 7); ctx.fill();
      if (main && x > W * 0.2 && x < W * 0.8 && y < H * 0.7 && r > tBest) { tBest = r; target = [x, y]; }
    });
    ctx.globalAlpha = 1;
    if (!target || !(spec.groups || []).length) return null;
    const p = hl ? lt - 0.5 : lt - 1.4;
    return { target, p, value: fmtValue(spec, ease(p / 0.8)), label: spec.groups[0].label };
  }

  // ---------- орбиты: двор в центре, соседи на кольцах, линии — связи ----------
  function drawOrbit(ctx, C, W, H, spec, prev, lt, gt, seed) {
    const r = rng(seed + 11), cx = W / 2, cy = H * 0.5, rings = [180, 280, 380], per = [9, 14, 19];
    const lonely = share(spec) / 100, pl = prev ? share(prev) / 100 : lonely, lk = prev ? ease(lt / 0.8) : 1;
    const lon = lerp(pl, lonely, lk), hl = spec.mode === 'highlight' || spec.mode === 'split';
    const dim = hl ? (prev && prev.mode === spec.mode ? 1 : ease(lt / 0.45)) : 0;
    const build = prev ? 1 : 1;
    // кольца: толстая полупрозрачная полоса и тонкие линии, прорисовываются по дуге
    rings.forEach((R, k) => {
      const q = prev ? 1 : ease((lt - k * 0.15) / 0.7);
      ctx.save(); ctx.strokeStyle = C.navy; ctx.globalAlpha = k === 1 ? 0.07 : 0.35; ctx.lineWidth = k === 1 ? 70 : 2;
      ctx.beginPath(); ctx.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + 6.2832 * q); ctx.stroke(); ctx.restore();
    });
    const nodes = [];
    rings.forEach((R, k) => { for (let j = 0; j < per[k]; j++) nodes.push({ R, k, a0: r() * 6.28, sh: r(), s: 0.7 + r() * 0.8, ph: r() * 6 }); });
    const order = nodes.map((_, i) => i).sort((a, b) => nodes[a].sh - nodes[b].sh);
    const nLonely = Math.round(lon * nodes.length), isLonely = new Array(nodes.length).fill(false);
    order.slice(0, nLonely).forEach(i => { isLonely[i] = true; });
    const speeds = [0.06, 0.035, -0.025];
    let target = null;
    nodes.forEach((n, i) => {
      const a = n.a0 + gt * speeds[n.k], out = isLonely[i] && spec.mode === 'split' ? 90 * ease(lt / 0.8) : 0;
      const x = cx + (n.R + out) * Math.cos(a), y = cy + (n.R + out) * Math.sin(a);
      const pop = prev ? 1 : ease((lt - 0.4 - i * 0.015) / 0.35);
      if (!isLonely[i]) {                     // связь с центром прорастает
        const g = prev ? 1 : ease((lt - 0.8 - i * 0.02) / 0.5);
        ctx.save(); ctx.strokeStyle = C.navy; ctx.globalAlpha = lerp(0.55, 0.2, dim); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(lerp(cx, x, g), lerp(cy, y, g)); ctx.stroke(); ctx.restore();
      }
      const rr = 15 * n.s * pop * (isLonely[i] ? 1 + 0.15 * dim * (1 + Math.sin(gt * 4 + n.ph)) / 2 : 1);
      if (rr <= 0.3) return;
      ctx.save();
      if (isLonely[i]) {
        ctx.globalAlpha = 1; ctx.lineWidth = 5; ctx.strokeStyle = C.accent; ctx.fillStyle = C.cream;
        ctx.beginPath(); ctx.arc(x, y, rr * 1.15, 0, 7); ctx.fill(); ctx.stroke();
        if (!target || y < target[1]) target = [x, y];
      } else {
        ctx.globalAlpha = lerp(1, 0.35, dim);
        const gr = ctx.createRadialGradient(x - rr * 0.3, y - rr * 0.3, 1, x, y, rr);
        gr.addColorStop(0, C.accent2); gr.addColorStop(1, C.navy); ctx.fillStyle = gr;
        if (i % 5 === 0) { ctx.fillRect(x - rr, y - rr, rr * 2, rr * 2); } else { ctx.beginPath(); ctx.arc(x, y, rr, 0, 7); ctx.fill(); }
      }
      ctx.restore();
    });
    // центр — двор
    const cpop = prev ? 1 : ease(lt / 0.4);
    ctx.save(); ctx.fillStyle = C.navy; ctx.beginPath(); ctx.arc(cx, cy, 52 * cpop, 0, 7); ctx.fill();
    ctx.strokeStyle = C.accent; ctx.lineWidth = 10; ctx.beginPath(); ctx.arc(cx, cy, 72 * cpop, 0, 7); ctx.stroke(); ctx.restore();
    if (!target || !(spec.groups || []).length) return null;
    const p = hl ? lt - 0.5 : lt - 1.5;
    return { target, p, value: fmtValue(spec, ease(p / 0.8)), label: spec.groups[0].label };
  }

  // ---------- дуги: доли толстыми градиентными дугами, линейка с делениями ----------
  function drawArcs(ctx, C, W, H, spec, prev, lt, gt) {
    const cx = W / 2, cy = H * 0.5, groups = (spec.groups || []).slice(0, 4), radii = [370, 292, 214, 136];
    const hl = spec.mode === 'highlight';
    const dim = hl ? (prev && prev.mode === 'highlight' ? 1 : ease(lt / 0.45)) : 0;
    // линейка с делениями медленно вращается
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(gt * 0.05); ctx.strokeStyle = C.ink; ctx.globalAlpha = 0.35; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(0, 0, 430, 0, 7); ctx.stroke();
    for (let k = 0; k < 72; k++) { const a = k / 72 * 6.2832, l = k % 6 ? 10 : 22;
      ctx.beginPath(); ctx.moveTo(430 * Math.cos(a), 430 * Math.sin(a)); ctx.lineTo((430 - l) * Math.cos(a), (430 - l) * Math.sin(a)); ctx.stroke(); }
    ctx.restore();
    let target = null;
    groups.forEach((g, k) => {
      const R = radii[k], pv = prev && prev.groups && prev.groups[k] ? clamp(prev.groups[k].value, 0, 100) : 0;
      const sweep = lerp(prev ? pv : 0, clamp(g.value, 0, 100), ease((lt - k * 0.2) / 1.0)) / 100 * 6.2832;
      ctx.save(); ctx.lineCap = 'round';
      ctx.strokeStyle = C.muted; ctx.globalAlpha = 0.45; ctx.lineWidth = 58;
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
      const grd = ctx.createConicGradient(-Math.PI / 2, cx, cy);
      grd.addColorStop(0, k === 0 ? C.accent : C.accent2); grd.addColorStop(1, k === 0 ? C.accent2 : C.navy);
      ctx.strokeStyle = grd; ctx.globalAlpha = k === 0 ? 1 : lerp(1, 0.3, dim); ctx.lineWidth = 58;
      if (sweep > 0.01) { ctx.beginPath(); ctx.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + sweep); ctx.stroke(); }
      ctx.restore();
      if (k === 0) { const a = -Math.PI / 2 + sweep; target = [cx + R * Math.cos(a), cy + R * Math.sin(a)]; }
      // частицы бегут по дуге — дуга живая
      ctx.save(); ctx.fillStyle = '#fff'; ctx.globalAlpha = 0.8;
      for (let m = 0; m < 3; m++) { const a = -Math.PI / 2 + ((gt * 0.25 + m / 3 + k * 0.13) % 1) * Math.max(sweep, 0.01);
        ctx.beginPath(); ctx.arc(cx + R * Math.cos(a), cy + R * Math.sin(a), 5, 0, 7); ctx.fill(); }
      ctx.restore();
    });
    if (!target || !groups.length) return null;
    const p = hl ? lt - 0.4 : lt - 1.2;
    return { target, p, value: fmtValue(spec, ease(p / 0.8)), label: groups[0].label };
  }

  window.drawArt = function (canvas, spec, prev, lt, gt, seed) {
    if (!spec || spec.kind === 'none') return;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (canvas.width !== W) { canvas.width = W; canvas.height = H; }
    const ctx = canvas.getContext('2d'), C = colors();
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, W, H);
    const fam = family(spec.kind), pfam = prev ? family(prev.kind) : null, same = prev && pfam === fam ? prev : null;
    // камера медленно наезжает на главное (10–20% за главу)
    const z = 1 + 0.12 * inout(lt / 5), fx = W / 2, fy = H * 0.5;
    ctx.translate(fx, fy); ctx.scale(z, z); ctx.translate(-fx, -fy);
    let L;
    if (fam === 'orbit') L = drawOrbit(ctx, C, W, H, spec, same, lt, gt, seed || 7);
    else if (fam === 'arcs') L = drawArcs(ctx, C, W, H, spec, same, lt, gt);
    else L = drawCloud(ctx, C, W, H, spec, same, lt, gt, seed || 7);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (L) {                                  // точка выноски — в координатах кадра после наезда камеры
      const tx = fx + (L.target[0] - fx) * z, ty = fy + (L.target[1] - fy) * z, right = tx < W / 2;
      callout(ctx, C, [tx, ty], [right ? W - 90 : 90, H * 0.2], L.value, L.label, L.p);
    }
    legend(ctx, C, spec, W, H * 0.86);
  };
})();
