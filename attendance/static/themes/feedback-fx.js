// Shared success-dialog effects for every clock style.
// Pure canvas, no dependencies; any failure here must never affect attendance.
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const lowEnd = (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 2;

// Each style gets particles that match its own story.
const STYLES = {
  original: { colors: ['#39ff14', '#b6ff9e', '#ffffff'], shape: 'spark', mode: 'burst', count: 70 },
  classic:  { colors: ['#64f6ed', '#7b8ded', '#bffff7'], shape: 'spark', mode: 'burst', count: 80 },
  kimono:   { colors: ['#f4b6c2', '#fde2e4', '#e89aae', '#fff4de'], shape: 'petal', mode: 'fall', count: 46 },
  aurora:   { colors: ['#bef8e8', '#b4c8ff', '#ffffff', '#f3d6ff'], shape: 'star', mode: 'burst', count: 60 },
  forest:   { colors: ['#80a071', '#b6ca9a', '#689575', '#d9c27a'], shape: 'leaf', mode: 'fall', count: 40 },
  ocean:    { colors: ['#5ecfe9', '#a6e7f5', '#ffffff'], shape: 'bubble', mode: 'rise', count: 45 },
  sunrise:  { colors: ['#edab6c', '#f6d27a', '#df9851', '#fff1c9'], shape: 'circle', mode: 'burst', count: 60 },
  paper:    { colors: ['#b46850', '#d9b38c', '#7a3b2c'], shape: 'square', mode: 'burst', count: 34 },
  arcade:   { colors: ['#f6e879', '#f6d562', '#8875ad', '#ff7aa2', '#7ce0c3'], shape: 'pixel', mode: 'burst', count: 56 },
  candy:    { colors: ['#f7a6d0', '#b08bce', '#9fd8f5', '#ffe08a', '#a8e6b8'], shape: 'confetti', mode: 'burst', count: 110 },
  mono:     null, // the minimal style keeps its single drawn line
  planet:   { colors: ['#ffd166', '#7bdff2', '#f7aef8', '#ffffff'], shape: 'star', mode: 'burst', count: 70 },
};

let active = null;
const rand = (a, b) => a + Math.random() * (b - a);

export function burst(dialog, theme) {
  if (reduced || !dialog) return;
  const style = STYLES[theme];
  if (navigator.vibrate) { try { navigator.vibrate([20, 40, 20]); } catch { /* unsupported */ } }
  if (!style) return;
  if (active) active.stop();

  // Fixed inside the top-layer dialog so it appears above the backdrop and spans the screen.
  const canvas = document.createElement('canvas');
  canvas.className = 'feedback-confetti';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: '5' });
  dialog.append(canvas);
  // Dialogs clip overflow; let confetti spill over only when the whole dialog fits on screen.
  if (dialog.scrollHeight + 40 < innerHeight) dialog.style.overflow = 'visible';
  const ctx = canvas.getContext('2d');
  if (!ctx) { canvas.remove(); return; }
  const dpr = Math.min(devicePixelRatio || 1, lowEnd ? 1 : 1.5);
  const w = innerWidth, h = innerHeight;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const art = dialog.querySelector('#modal-scene') || dialog;
  const r = art.getBoundingClientRect();
  const ox = r.left + r.width / 2 || w / 2, oy = r.top + r.height / 2 || h / 2;
  const small = Math.min(w, h) < 600;
  const n = Math.round(style.count * (lowEnd ? 0.55 : small ? 0.75 : 1));
  const parts = [];
  for (let i = 0; i < n; i++) {
    const p = { c: style.colors[i % style.colors.length], rot: rand(0, 6.28), vr: rand(-0.2, 0.2), flip: rand(0, 6.28), vf: rand(0.06, 0.2), size: rand(4, 9), life: 0, delay: 0 };
    if (style.mode === 'burst') {
      const a = rand(0, Math.PI * 2), s = rand(3, small ? 10 : 14);
      Object.assign(p, { x: ox, y: oy, vx: Math.cos(a) * s, vy: Math.sin(a) * s - rand(1, 4), g: 0.22 });
    } else if (style.mode === 'fall') {
      Object.assign(p, { x: rand(0, w), y: rand(-h * 0.4, -10), vx: rand(-0.6, 0.6), vy: rand(1, 2.4), g: 0.01, sway: rand(0.6, 1.6), delay: rand(0, 25) });
    } else {
      Object.assign(p, { x: rand(w * 0.15, w * 0.85), y: h + rand(10, h * 0.3), vx: rand(-0.3, 0.3), vy: -rand(1.5, 3.5), g: -0.01, sway: rand(0.4, 1.2), size: rand(4, 14), delay: rand(0, 20) });
    }
    if (style.shape === 'pixel') p.rot = 0, p.vr = 0;
    parts.push(p);
  }

  let raf = 0, frame = 0;
  const start = performance.now(), duration = style.mode === 'burst' ? 2600 : 3600;
  function draw(p) {
    ctx.fillStyle = p.c; ctx.strokeStyle = p.c;
    const s = p.size;
    switch (style.shape) {
      case 'circle': ctx.beginPath(); ctx.arc(0, 0, s * 0.5, 0, 6.28); ctx.fill(); break;
      case 'bubble': ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(0, 0, s * 0.6, 0, 6.28); ctx.stroke(); ctx.globalAlpha *= 0.5; ctx.beginPath(); ctx.arc(-s * 0.2, -s * 0.2, s * 0.15, 0, 6.28); ctx.fill(); break;
      case 'star': {
        ctx.beginPath();
        for (let k = 0; k < 8; k++) { const rr = k % 2 ? s * 0.25 : s * 0.75, a = k * Math.PI / 4; ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
        ctx.closePath(); ctx.fill(); break;
      }
      case 'petal': ctx.scale(1, Math.cos(p.flip)); ctx.beginPath(); ctx.ellipse(0, 0, s * 0.45, s * 0.8, 0, 0, 6.28); ctx.fill(); break;
      case 'leaf': ctx.scale(1, Math.cos(p.flip)); ctx.beginPath(); ctx.moveTo(0, -s); ctx.quadraticCurveTo(s * 0.8, 0, 0, s); ctx.quadraticCurveTo(-s * 0.8, 0, 0, -s); ctx.fill(); break;
      case 'spark': ctx.fillRect(-s * 0.9, -1, s * 1.8, 2); break;
      case 'pixel': ctx.fillRect(-s / 2, -s / 2, s, s); break;
      case 'square': ctx.scale(1, Math.cos(p.flip)); ctx.fillRect(-s / 2, -s / 2, s, s); break;
      default: ctx.scale(1, Math.cos(p.flip)); ctx.fillRect(-s / 2, -s / 4, s, s / 2); // confetti strip
    }
  }
  function tick(t) {
    const elapsed = t - start;
    frame++;
    ctx.clearRect(0, 0, w, h);
    const fade = elapsed > duration - 700 ? Math.max(0, (duration - elapsed) / 700) : 1;
    for (const p of parts) {
      if (p.delay > 0) { p.delay--; continue; }
      p.life++;
      p.vx *= 0.985; p.vy = p.vy * 0.985 + p.g;
      p.x += p.vx + (p.sway ? Math.sin((frame + p.size * 10) * 0.04) * p.sway : 0);
      p.y += p.vy; p.rot += p.vr; p.flip += p.vf;
      if (p.y > h + 30 || p.y < -h) continue;
      ctx.save();
      ctx.globalAlpha = fade * Math.min(1, p.life / 6);
      ctx.translate(style.shape === 'pixel' ? Math.round(p.x / 3) * 3 : p.x, style.shape === 'pixel' ? Math.round(p.y / 3) * 3 : p.y);
      ctx.rotate(p.rot);
      draw(p);
      ctx.restore();
    }
    if (elapsed < duration && dialog.open) raf = requestAnimationFrame(tick); else stop();
  }
  function stop() { cancelAnimationFrame(raf); canvas.remove(); if (active === handle) active = null; }
  const handle = { stop };
  active = handle;
  // Start after the dialog's 3D entrance has settled.
  setTimeout(() => { if (active === handle) raf = requestAnimationFrame(tick); }, 560);
}
