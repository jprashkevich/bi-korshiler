/* Инфографика BIG Life: точка = человек, линия = связь, кольца процентов, дом с окнами.
   Почему canvas и чистые функции от времени: Reels рендерится покадрово (seek(t)), поэтому кадр
   должен однозначно зависеть только от t. Раскладки детерминированы (сид от текста сцены),
   и соседние сцены с той же фигурой плавно перестраивают её, а не рисуют заново.
   Числа берутся из пакета: сколько точек окрашено — ровно доля из источника. */
(function () {
  const GOLD = 137.50776 * Math.PI / 180;
  const ease = x => 1 - Math.pow(1 - Math.min(Math.max(x, 0), 1), 3);
  const lerp = (a, b, k) => a + (b - a) * k;

  function rng(seed) {                      // mulberry32: одинаковый результат на каждом кадре
    let a = seed >>> 0;
    return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function hash(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

  function palette(el) {
    const cs = getComputedStyle(el);
    const fg = cs.color;
    const v = n => cs.getPropertyValue(n).trim();
    // на цветном фоне акцент сливается с фоном: главная группа рисуется тёмно-синим, вторая — белым
    if (el.classList && (el.classList.contains('bg-accent') || el.classList.contains('bg-accent2')))
      return { fg, accent: v('--navy') || '#28348a', accent2: '#ffffff', white: fg, muted: fg };
    return { fg, accent: v('--accent'), accent2: v('--accent2'), white: fg, muted: fg };
  }
  function colorOf(pal, c) { return pal[c] || pal.fg; }

  // ---------- точки ----------
  const DOTS = 240;
  function dotPlan(spec) {
    const r = rng(hash(JSON.stringify(spec.groups || []) + (spec.unit || '')));
    const order = [...Array(DOTS).keys()];
    for (let i = DOTS - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
    const owner = new Array(DOTS).fill(-1);            // -1 — «остальные»
    let k = 0;
    (spec.groups || []).forEach((g, gi) => {
      const n = Math.round(Math.max(0, Math.min(100, g.value)) / 100 * DOTS);
      for (let m = 0; m < n && k < DOTS; m++, k++) owner[order[k]] = gi;
    });
    return owner;
  }
  function disc(n, cx, cy, R) {
    const pts = [];
    for (let i = 0; i < n; i++) { const rr = R * Math.sqrt((i + 0.5) / n), a = i * GOLD; pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]); }
    return pts;
  }
  function dotLayout(spec, W, H) {
    const owner = dotPlan(spec), R = Math.min(W, H) * 0.42;
    if (spec.mode !== 'split') {
      const pts = disc(DOTS, W / 2, H / 2, R);
      return { pos: pts, owner, rad: R * 0.82 / Math.sqrt(DOTS) * 1.05, labels: [] };
    }
    const groups = [...(spec.groups || []).keys(), -1].filter(g => owner.includes(g));
    const counts = groups.map(g => owner.filter(o => o === g).length);
    const scale = R * 0.9 / Math.sqrt(DOTS);
    const radii = counts.map(c => scale * Math.sqrt(c) * 1.1 + 6);
    const gap = 40, totalW = radii.reduce((s, r) => s + 2 * r, 0) + gap * (radii.length - 1);
    const k = Math.min(1, (W * 0.92) / totalW);
    let x = (W - totalW * k) / 2;
    const pos = new Array(DOTS), labels = [];
    groups.forEach((g, gi) => {
      const rr = radii[gi] * k, cx = x + rr, idx = owner.map((o, i) => o === g ? i : -1).filter(i => i >= 0);
      disc(idx.length, cx, H * 0.45, rr).forEach((p, m) => { pos[idx[m]] = p; });
      labels.push({ x: cx, y: H * 0.45 + rr + 54, g, n: idx.length });
      x += 2 * rr + gap * k;
    });
    return { pos, owner, rad: scale * 0.9 * k, labels };
  }
  function drawDots(ctx, spec, prev, W, H, pal, lt) {
    const L = dotLayout(spec, W, H);
    const P = prev && prev.kind === 'dots' ? dotLayout(prev, W, H) : null;
    const move = ease(lt / 0.8);
    const groups = spec.groups || [];
    for (let i = 0; i < DOTS; i++) {
      const appear = P ? 1 : ease((lt - (i / DOTS) * 0.9) / 0.25);
      if (appear <= 0) continue;
      let [x, y] = L.pos[i];
      if (P) { x = lerp(P.pos[i][0], x, move); y = lerp(P.pos[i][1], y, move); }
      else { x = lerp(W / 2, x, appear); y = lerp(H / 2, y, appear); }
      const o = L.owner[i], tint = ease((lt - (P ? 0 : 0.9)) / 0.5);
      const main = o === 0;
      let col = o >= 0 ? colorOf(pal, groups[o].color) : pal.muted;
      let alpha = o >= 0 ? lerp(0.35, 1, tint) : 0.35;
      if (o >= 0 && groups[o].color === 'muted') alpha = 0.35;
      if (spec.mode === 'highlight') alpha = main ? 1 : lerp(alpha, 0.14, ease(lt / 0.6));
      if (!P && tint < 1 && o >= 0) col = pal.fg;
      ctx.globalAlpha = alpha * appear;
      ctx.fillStyle = col;
      const r = L.rad * (main && spec.mode === 'highlight' ? 1.25 : 1) * (0.6 + 0.4 * appear);
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    if (spec.mode === 'split') L.labels.forEach(l => {
      const g = l.g >= 0 ? groups[l.g] : null, a = ease((lt - 0.6) / 0.4);
      ctx.globalAlpha = a; ctx.fillStyle = g ? colorOf(pal, g.color) : pal.fg; ctx.textAlign = 'center';
      ctx.font = '800 52px "TT Firs Neue", Montserrat, sans-serif';
      ctx.fillText(g ? fmtPct(g.value) : fmtPct(100 - groups.reduce((s, x) => s + x.value, 0)), l.x, l.y);
      ctx.font = '700 26px Montserrat, sans-serif'; ctx.fillStyle = pal.fg;
      ctx.fillText(g ? g.label : 'остальные', l.x, l.y + 36);
      ctx.globalAlpha = 1;
    });
    return L;
  }

  // ---------- сеть связей ----------
  const NODES = 42;
  function netLayout(spec, W, H) {
    const r = rng(hash('net' + JSON.stringify(spec.groups || [])));
    const pts = disc(NODES, W / 2, H / 2, Math.min(W, H) * 0.44).map(([x, y]) => [x + (r() - 0.5) * 26, y + (r() - 0.5) * 26]);
    const share = spec.groups && spec.groups[0] ? spec.groups[0].value / 100 : 0.2;
    const lonely = new Set();
    const ids = [...Array(NODES).keys()].slice(1).sort(() => r() - 0.5);
    ids.slice(0, Math.round(share * (NODES - 1))).forEach(i => lonely.add(i));
    const edges = [];
    for (let i = 0; i < NODES; i++) {
      if (lonely.has(i)) continue;
      const near = [...Array(NODES).keys()].filter(j => j !== i && !lonely.has(j))
        .sort((a, b) => Math.hypot(pts[a][0] - pts[i][0], pts[a][1] - pts[i][1]) - Math.hypot(pts[b][0] - pts[i][0], pts[b][1] - pts[i][1]));
      near.slice(0, i === 0 ? 6 : 2).forEach(j => { if (i < j || i === 0) edges.push([i, j]); });
    }
    return { pts, lonely, edges };
  }
  function drawNetwork(ctx, spec, prev, W, H, pal, lt) {
    const N = netLayout(spec, W, H), cont = prev && prev.kind === 'network';
    const grow = cont ? 1 : ease((lt - 0.5) / 1.2);
    ctx.lineWidth = 3.5;
    N.edges.forEach(([a, b], k) => {
      const p = cont ? 1 : ease((lt - 0.5 - k * 0.012) / 0.5);
      if (p <= 0) return;
      const [x1, y1] = N.pts[a], [x2, y2] = N.pts[b];
      ctx.globalAlpha = spec.mode === 'highlight' ? 0.35 : 0.8; ctx.strokeStyle = pal.fg;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(lerp(x1, x2, p), lerp(y1, y2, p)); ctx.stroke();
    });
    N.pts.forEach(([x, y], i) => {
      const a = cont ? 1 : ease((lt - i * 0.012) / 0.3);
      const lonely = N.lonely.has(i);
      const pulse = spec.mode === 'highlight' && lonely ? 1 + 0.18 * Math.sin(lt * 6) : 1;
      ctx.globalAlpha = a * (lonely && spec.mode !== 'highlight' ? 0.45 : 1);
      ctx.strokeStyle = lonely ? (spec.mode === 'highlight' ? pal.accent : pal.fg) : pal.fg;
      ctx.fillStyle = i === 0 ? pal.accent : 'transparent';
      ctx.lineWidth = i === 0 ? 10 : 4;
      const r = (i === 0 ? 40 : lonely ? 13 : 11) * pulse;
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
      if (i !== 0 && !lonely) { ctx.fillStyle = pal.fg; ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill(); }
    });
    ctx.globalAlpha = 1;
    return { pos: N.pts.filter((_, i) => N.lonely.has(i)) };
  }

  // ---------- кольца ----------
  function drawRings(ctx, spec, prev, W, H, pal, lt) {
    const groups = (spec.groups || []).slice(0, 3), cx = W / 2, cy = H / 2;
    const R0 = Math.min(W, H) * 0.44, gap = 64, width = 36;
    groups.forEach((g, i) => {
      const R = R0 - i * gap, sweep = ease((lt - 0.2 - i * 0.25) / 1.1) * g.value / 100;
      ctx.lineCap = 'round'; ctx.lineWidth = width;
      ctx.globalAlpha = 0.14; ctx.strokeStyle = pal.fg;
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1; ctx.strokeStyle = colorOf(pal, g.color === 'muted' ? 'white' : g.color);
      if (sweep > 0.001) { ctx.beginPath(); ctx.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + sweep * Math.PI * 2); ctx.stroke(); }
    });
    if (groups[0]) {
      const v = ease((lt - 0.2) / 1.1) * groups[0].value;
      ctx.fillStyle = pal.fg; ctx.textAlign = 'center';
      ctx.font = '800 120px "TT Firs Neue", Montserrat, sans-serif';
      ctx.fillText(fmtPct(v), cx, cy + 30);
      ctx.font = '700 28px Montserrat, sans-serif';
      ctx.fillText(groups[0].label, cx, cy + 80);
    }
    ctx.textAlign = 'left'; ctx.font = '700 26px Montserrat, sans-serif';
    groups.slice(1).forEach((g, i) => {
      ctx.globalAlpha = ease((lt - 1.2 - i * 0.2) / 0.4);
      ctx.fillStyle = colorOf(pal, g.color === 'muted' ? 'white' : g.color);
      ctx.fillText(`${fmtPct(g.value)} — ${g.label}`, 20, H - 20 - (groups.length - 2 - i) * 40);
    });
    ctx.globalAlpha = 1;
    return { pos: [] };
  }

  // ---------- дом с окнами ----------
  function drawHouse(ctx, spec, prev, W, H, pal, lt) {
    const cols = 6, rows = 9, bw = Math.min(W * 0.62, H * 0.55), cell = bw / cols, bh = cell * rows;
    const x0 = (W - bw) / 2, y0 = (H - bh) / 2 + 30;
    const r = rng(hash('house' + JSON.stringify(spec.groups || [])));
    const order = [...Array(cols * rows).keys()].sort(() => r() - 0.5);
    const owner = new Array(cols * rows).fill(-1);
    let k = 0;
    (spec.groups || []).forEach((g, gi) => { const n = Math.round(g.value / 100 * cols * rows); for (let m = 0; m < n && k < owner.length; m++, k++) owner[order[k]] = gi; });
    ctx.strokeStyle = pal.fg; ctx.lineWidth = 4; ctx.globalAlpha = ease(lt / 0.5);
    ctx.strokeRect(x0 - 18, y0 - 18, bw + 36, bh + 36);
    ctx.beginPath(); ctx.moveTo(x0 - 40, y0 - 18); ctx.lineTo(x0 + bw / 2, y0 - 18 - cell * 1.3); ctx.lineTo(x0 + bw + 40, y0 - 18); ctx.stroke();
    const pos = [];
    for (let i = 0; i < cols * rows; i++) {
      const cx = x0 + (i % cols) * cell, cy = y0 + Math.floor(i / cols) * cell, o = owner[i];
      const lit = o >= 0 ? ease((lt - 0.5 - order.indexOf(i) * 0.025) / 0.25) : 0;
      ctx.globalAlpha = 0.18 + 0.82 * lit;
      ctx.fillStyle = o >= 0 && lit > 0 ? colorOf(pal, spec.groups[o].color === 'muted' ? 'white' : spec.groups[o].color) : pal.fg;
      ctx.fillRect(cx + cell * 0.18, cy + cell * 0.18, cell * 0.64, cell * 0.64);
      if (o === 0) pos.push([cx + cell / 2, cy + cell / 2]);
    }
    ctx.globalAlpha = 1;
    return { pos };
  }

  function fmtPct(v) { const r = Math.round(v); return (Math.abs(v - r) < 0.05 ? r : v.toFixed(1).replace('.', ',')) + '%'; }

  function chrome(ctx, spec, W, H, pal, lt, L) {
    // выноски: тонкая линия от точки главной группы к подписи у края
    const pts = (L && L.pos ? (L.owner ? L.pos.filter((_, i) => L.owner[i] === 0) : L.pos) : []);
    (spec.callouts || []).slice(0, 2).forEach((text, i) => {
      const p = pts[Math.floor(pts.length * (i ? 0.85 : 0.15))];
      if (!p) return;
      const k = ease((lt - 1.4 - i * 0.35) / 0.5);
      if (k <= 0) return;
      const tx = i ? W - 10 : 10, ty = i ? 40 : 40;
      ctx.globalAlpha = k; ctx.strokeStyle = pal.fg; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(lerp(p[0], tx + (i ? -20 : 20), k), lerp(p[1], ty + 14, k)); ctx.stroke();
      ctx.beginPath(); ctx.arc(p[0], p[1], 7, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = pal.fg; ctx.textAlign = i ? 'right' : 'left'; ctx.font = '700 26px Montserrat, sans-serif';
      ctx.fillText(text, tx, ty);
      ctx.globalAlpha = 1;
    });
  }

  // Публичная функция: нарисовать фигуру spec на canvas в момент lt секунд от начала сцены.
  window.drawViz = function (canvas, spec, prev, lt) {
    if (!spec || spec.kind === 'none') return;
    const dpr = 1, W = canvas.clientWidth, H = canvas.clientHeight;
    if (canvas.width !== W * dpr) { canvas.width = W * dpr; canvas.height = H * dpr; }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const pal = palette(canvas.closest('.scene, section') || canvas);
    const pad = 70;  // поле под легенду и выноски
    ctx.save(); ctx.translate(0, pad);
    const innerH = H - pad * 2;
    let L = null;
    if (spec.kind === 'dots') L = drawDots(ctx, spec, prev, W, innerH, pal, lt);
    else if (spec.kind === 'network') L = drawNetwork(ctx, spec, prev, W, innerH, pal, lt);
    else if (spec.kind === 'rings') L = drawRings(ctx, spec, prev, W, innerH, pal, lt);
    else if (spec.kind === 'house') L = drawHouse(ctx, spec, prev, W, innerH, pal, lt);
    ctx.restore();
    ctx.save(); ctx.translate(0, pad);
    if (L && L.pos) chrome(ctx, spec, W, innerH, pal, lt, L);
    ctx.restore();
    ctx.save();
    if (spec.unit || spec.conditional) {
      ctx.font = '700 24px Montserrat, sans-serif'; ctx.fillStyle = pal.fg; ctx.globalAlpha = 0.75 * ease((lt - 0.8) / 0.4);
      ctx.textAlign = 'left'; if (spec.unit) { ctx.beginPath(); ctx.arc(14, H - 22, 8, 0, Math.PI * 2); ctx.fill(); ctx.fillText(spec.unit, 34, H - 13); }
      ctx.textAlign = 'right'; if (spec.conditional) ctx.fillText('условная схема', W - 4, H - 13);
    }
    ctx.restore();
  };
})();
