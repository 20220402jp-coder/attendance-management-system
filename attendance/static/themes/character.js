// Kimono girl — a layered vector illustration (no WebGL needed).
// Idle: breathing, blinking, hair and hair-ornament sway, eyes follow the pointer.
// Success: she smiles and bows. API matches the old 3D character: {show, hide, replay}.
const NS = 'http://www.w3.org/2000/svg';

function sakura(cx, cy, r, fill, center = '#f6c35b', rot = 0) {
  let petals = '';
  for (let i = 0; i < 5; i++) {
    const a = rot + i * 72;
    petals += `<path transform="rotate(${a} ${cx} ${cy})" d="M${cx} ${cy} C${cx - r * 0.55} ${cy - r * 0.45} ${cx - r * 0.42} ${cy - r * 1.05} ${cx - r * 0.12} ${cy - r * 1.02} L${cx} ${cy - r * 0.86} L${cx + r * 0.12} ${cy - r * 1.02} C${cx + r * 0.42} ${cy - r * 1.05} ${cx + r * 0.55} ${cy - r * 0.45} ${cx} ${cy}Z" fill="${fill}"/>`;
  }
  return `<g>${petals}<circle cx="${cx}" cy="${cy}" r="${r * 0.2}" fill="${center}"/></g>`;
}

function eye(cx, side) {
  // side: -1 left, 1 right (mirrors the outer lash flick)
  const o = side;
  const shape = `M${cx - 19 * o} 157 C${cx - 14 * o} 139 ${cx + 12 * o} 136 ${cx + 20 * o} 150 C${cx + 21 * o} 168 ${cx + 8 * o} 178 ${cx - 2 * o} 178 C${cx - 13 * o} 178 ${cx - 21 * o} 170 ${cx - 19 * o} 157Z`;
  return `
  <g class="km-eye">
    <clipPath id="km-clip-${side}"><path d="${shape}"/></clipPath>
    <path d="${shape}" fill="#fffdfb"/>
    <g clip-path="url(#km-clip-${side})">
      <g class="km-iris">
        <ellipse cx="${cx}" cy="161" rx="14.5" ry="18" fill="url(#km-iris)"/>
        <ellipse cx="${cx}" cy="163" rx="7.5" ry="10" fill="#3b2030" opacity=".9"/>
        <ellipse cx="${cx}" cy="171" rx="9" ry="4" fill="#ffc7c0" opacity=".55"/>
        <circle cx="${cx - 5 * o}" cy="153" r="5.2" fill="#fff"/>
        <circle cx="${cx + 5 * o}" cy="168" r="2.4" fill="#fff" opacity=".9"/>
      </g>
      <path d="M${cx - 22 * o} 150 C${cx - 10 * o} 143 ${cx + 10 * o} 143 ${cx + 22 * o} 151 L${cx + 22 * o} 140 L${cx - 22 * o} 140Z" fill="#c98d8f" opacity=".25"/>
    </g>
    <path d="M${cx - 21 * o} 156 C${cx - 15 * o} 137 ${cx + 13 * o} 134 ${cx + 22 * o} 149" fill="none" stroke="#3a2328" stroke-width="4.6" stroke-linecap="round"/>
    <path d="M${cx + 19 * o} 146 L${cx + 27 * o} 141 M${cx + 21 * o} 150 L${cx + 28 * o} 149" stroke="#3a2328" stroke-width="2.4" stroke-linecap="round"/>
    <path d="M${cx - 9 * o} 179 C${cx - 3 * o} 181 ${cx + 6 * o} 180 ${cx + 11 * o} 176" fill="none" stroke="#b67a77" stroke-width="1.6" stroke-linecap="round" opacity=".7"/>
  </g>
  <path class="km-eye-happy" d="M${cx - 16} 162 Q${cx} 146 ${cx + 16} 162" fill="none" stroke="#3a2328" stroke-width="4.2" stroke-linecap="round"/>`;
}

function buildSVG() {
  const kimonoFlowers = [sakura(12, 12, 7, '#fff7f5'), sakura(34, 33, 5, '#ffe1ea', '#f6c35b', 20)].join('');
  return `
<svg class="km-girl" viewBox="0 0 360 540" xmlns="${NS}" role="img" aria-hidden="true">
  <defs>
    <linearGradient id="km-hair" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#6b4239"/><stop offset=".55" stop-color="#4c2d2c"/><stop offset="1" stop-color="#3a2226"/>
    </linearGradient>
    <linearGradient id="km-hair-light" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8a5a4c"/><stop offset="1" stop-color="#5a3633"/>
    </linearGradient>
    <linearGradient id="km-iris" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#4d2638"/><stop offset=".5" stop-color="#9c4f5f"/><stop offset="1" stop-color="#f2a5a0"/>
    </linearGradient>
    <radialGradient id="km-skin" cx=".5" cy=".42" r=".62">
      <stop offset="0" stop-color="#fff3ec"/><stop offset="1" stop-color="#ffe0d4"/>
    </radialGradient>
    <pattern id="km-kimono" width="44" height="44" patternUnits="userSpaceOnUse">
      <rect width="44" height="44" fill="#f4a9bb"/>
      <path d="M0 44 Q11 36 22 44 T44 44" fill="none" stroke="#f9c6d3" stroke-width="1.4" opacity=".7"/>
      ${kimonoFlowers}
    </pattern>
    <pattern id="km-obi" width="16" height="16" patternUnits="userSpaceOnUse">
      <rect width="16" height="16" fill="#f3d18c"/>
      <path d="M0 8 L8 0 L16 8 L8 16Z" fill="none" stroke="#e2b765" stroke-width="1.2"/>
    </pattern>
    <linearGradient id="km-shade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7a2f4c" stop-opacity=".28"/><stop offset=".25" stop-color="#7a2f4c" stop-opacity="0"/>
      <stop offset=".75" stop-color="#7a2f4c" stop-opacity="0"/><stop offset="1" stop-color="#7a2f4c" stop-opacity=".3"/>
    </linearGradient>
    <linearGradient id="km-hem" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#b5577a" stop-opacity="0"/><stop offset="1" stop-color="#9b4067" stop-opacity=".75"/>
    </linearGradient>
    <filter id="km-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
  </defs>

  <ellipse cx="180" cy="516" rx="92" ry="11" fill="#b4728a" opacity=".18"/>

  <!-- back hair -->
  <g class="km-headpart"><g class="km-hairback">
    <path d="M96 150 C86 70 138 36 180 36 C224 36 276 70 264 150 C272 230 290 318 276 398 C262 388 250 376 242 352 C236 372 226 384 212 392 L148 392 C134 384 124 372 118 352 C110 376 98 388 84 398 C70 318 88 230 96 150Z" fill="url(#km-hair)"/>
    <path d="M118 352 C112 300 110 250 116 200 M242 352 C248 300 250 250 244 200" stroke="#2f1b1f" stroke-width="2" opacity=".35" fill="none"/>
  </g></g>

  <!-- body -->
  <g class="km-body">
    <!-- long furisode sleeves -->
    <path d="M124 262 C98 276 84 322 82 384 C80 428 94 458 122 466 L146 458 L142 300Z" fill="url(#km-kimono)"/>
    <path d="M236 262 C262 276 276 322 278 384 C280 428 266 458 238 466 L214 458 L218 300Z" fill="url(#km-kimono)"/>
    <path d="M82 384 C80 428 94 458 122 466 L146 458 L144 420 C120 430 98 418 82 384Z" fill="url(#km-hem)"/>
    <path d="M278 384 C280 428 266 458 238 466 L214 458 L216 420 C240 430 262 418 278 384Z" fill="url(#km-hem)"/>
    <!-- robe -->
    <path d="M122 262 C138 246 160 240 180 240 C200 240 222 246 238 262 L254 506 L106 506Z" fill="url(#km-kimono)"/>
    <path d="M122 262 C138 246 160 240 180 240 C200 240 222 246 238 262 L254 506 L106 506Z" fill="url(#km-shade)"/>
    <path d="M110 440 L250 440 L254 506 L106 506Z" fill="url(#km-hem)"/>
    <path d="M206 250 L150 506" stroke="#d9748f" stroke-width="2.2" opacity=".55"/>
    <!-- collar: white under-kimono + crimson edge -->
    <path d="M158 243 L180 296 L202 243" fill="none" stroke="#fffaf6" stroke-width="11" stroke-linejoin="round"/>
    <path d="M150 248 L180 304 L210 248" fill="none" stroke="#c94f6d" stroke-width="7" stroke-linejoin="round"/>
    <!-- obi -->
    <path d="M118 312 Q180 304 242 312 L244 322 Q180 314 116 322Z" fill="#f19bb3"/>
    <path d="M116 320 Q180 312 244 320 L246 364 Q180 356 114 364Z" fill="url(#km-obi)"/>
    <path d="M116 320 Q180 312 244 320 L246 364 Q180 356 114 364Z" fill="url(#km-shade)"/>
    <path d="M115 342 Q180 334 245 342" stroke="#c94f6d" stroke-width="3.2" fill="none"/>
    <circle cx="180" cy="338" r="5.5" fill="#c94f6d"/>
    ${sakura(206, 336, 9, '#fff6f8', '#e7a93f', 10)}
    <!-- hands, politely together -->
    <path d="M150 382 C160 372 170 376 180 384 C190 376 200 372 210 382 L206 392 C196 386 188 390 180 396 C172 390 164 386 154 392Z" fill="#fff0f3" opacity=".9"/>
    <ellipse cx="172" cy="392" rx="12" ry="8.5" fill="url(#km-skin)"/>
    <ellipse cx="188" cy="394" rx="12" ry="8.5" fill="url(#km-skin)"/>
    <path d="M182 390 Q186 396 194 396" stroke="#e7b3a6" stroke-width="1.3" fill="none"/>
    <!-- feet -->
    <ellipse cx="164" cy="510" rx="13" ry="6" fill="#fffaf7"/><ellipse cx="196" cy="510" rx="13" ry="6" fill="#fffaf7"/>
    <path d="M156 512 Q164 504 172 512 M188 512 Q196 504 204 512" stroke="#c94f6d" stroke-width="2.6" fill="none" stroke-linecap="round"/>
  </g>

  <!-- neck -->
  <path d="M168 214 L192 214 L194 250 Q180 256 166 250Z" fill="#ffe1d6"/>
  <path d="M168 226 Q180 236 192 226 L192 216 L168 216Z" fill="#f4c6b8" opacity=".6"/>

  <!-- head -->
  <g class="km-headpart"><g class="km-head">
    <path d="M110 142 C110 92 140 70 180 70 C220 70 250 92 250 142 C250 188 222 224 180 228 C138 224 110 188 110 142Z" fill="url(#km-skin)"/>
    <ellipse cx="138" cy="186" rx="16" ry="8.5" fill="#ff98ac" opacity=".55" filter="url(#km-soft)"/>
    <ellipse cx="222" cy="186" rx="16" ry="8.5" fill="#ff98ac" opacity=".55" filter="url(#km-soft)"/>
    <path d="M132 186 l5 -5 M139 188 l5 -5 M216 188 l5 -5 M223 186 l5 -5" stroke="#f58aa0" stroke-width="1.4" stroke-linecap="round" opacity=".6"/>
    <path d="M138 128 Q152 121 166 127 M194 127 Q208 121 222 128" stroke="#7a4b45" stroke-width="2.4" fill="none" stroke-linecap="round" opacity=".75"/>
    <g class="km-eyes">${eye(151, -1)}${eye(209, 1)}</g>
    <path d="M179 181 Q181 184 183 182" stroke="#e0a092" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    <path class="km-mouth" d="M171 197 Q180 204 189 197" stroke="#c4626f" stroke-width="2.6" fill="none" stroke-linecap="round"/>
    <path class="km-mouth-happy" d="M169 194 Q180 212 191 194 Q180 199 169 194Z" fill="#d95b74"/>

    <!-- front hair: bangs and side locks -->
    <path d="M100 152 C94 82 138 54 182 54 C228 54 268 84 262 152 C254 130 247 117 236 108 C238 128 232 142 225 148 C220 127 211 113 199 104 C201 124 195 137 187 143 C183 122 175 108 165 101 C165 120 157 134 147 141 C145 122 137 111 125 107 C123 128 112 141 100 152Z" fill="url(#km-hair-light)"/>
    <path d="M100 152 C94 82 138 54 182 54 C228 54 268 84 262 152 C254 130 247 117 236 108 C238 128 232 142 225 148 C220 127 211 113 199 104 C201 124 195 137 187 143 C183 122 175 108 165 101 C165 120 157 134 147 141 C145 122 137 111 125 107 C123 128 112 141 100 152Z" fill="url(#km-hair)" opacity=".55"/>
    <g class="km-lock-l"><path d="M104 140 C94 196 98 250 114 292 C121 270 122 240 119 204 C118 178 114 156 109 141Z" fill="url(#km-hair)"/></g>
    <g class="km-lock-r"><path d="M256 140 C266 196 262 250 246 292 C239 270 238 240 241 204 C242 178 246 156 251 141Z" fill="url(#km-hair)"/></g>
    <path d="M126 84 C146 70 214 70 236 86" stroke="#fff" stroke-width="5" stroke-linecap="round" fill="none" opacity=".22" stroke-dasharray="26 10"/>

    <!-- kanzashi: sakura cluster with swaying beads -->
    <g class="km-kanzashi">
      <path d="M236 98 C244 100 250 108 252 116" stroke="#8fae8b" stroke-width="3" fill="none" stroke-linecap="round"/>
      ${sakura(246, 92, 13, '#ffd3df', '#f2b544', 8)}
      ${sakura(228, 80, 10, '#fff4f7', '#f2b544', 30)}
      ${sakura(262, 104, 8, '#f6a3ba', '#f2b544', 50)}
      <g class="km-beads">
        <path d="M250 112 L256 158 M258 110 L268 150 M244 112 L246 146" stroke="#e9b85a" stroke-width="1.3"/>
        <circle cx="256" cy="160" r="4" fill="#e7516f"/><circle cx="268" cy="152" r="3.4" fill="#fff4f7"/><circle cx="246" cy="148" r="3.4" fill="#f6a3ba"/>
        ${sakura(256, 168, 4.5, '#ffd3df')}
      </g>
    </g>
  </g></g>

  <!-- little hearts for the bow -->
  <g class="km-hearts">
    <path d="M286 120 c-6 -8 -18 -2 -12 8 l12 10 l12 -10 c6 -10 -6 -16 -12 -8z" fill="#f27d9b"/>
    <path d="M70 160 c-4 -6 -13 -1 -9 6 l9 7 l9 -7 c4 -7 -5 -12 -9 -6z" fill="#f7a8bd"/>
    <path d="M300 200 c-3 -4 -9 -1 -6 4 l6 5 l6 -5 c3 -5 -3 -8 -6 -4z" fill="#f9c3d1"/>
  </g>
</svg>`;
}

export function mountCharacter(home, modalHost, dialog) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wrap = document.createElement('div');
  wrap.className = 'km-wrap';
  wrap.innerHTML = buildSVG();
  const svg = wrap.firstElementChild;
  home.replaceChildren(wrap);

  const heads = svg.querySelectorAll('.km-headpart');
  const irises = svg.querySelectorAll('.km-iris');
  const body = svg.querySelector('.km-body');

  // eyes and head gently follow the pointer
  let tx = 0, ty = 0, cx = 0, cy = 0, raf = 0, bowing = false;
  function follow() {
    cx += (tx - cx) * 0.12; cy += (ty - cy) * 0.12;
    irises.forEach(i => i.setAttribute('transform', `translate(${(cx * 3.2).toFixed(2)} ${(cy * 2.6).toFixed(2)})`));
    if (!bowing) heads.forEach(h => h.setAttribute('transform', `translate(${(cx * 3).toFixed(2)} ${(cy * 1.5).toFixed(2)}) rotate(${(cx * 2.4).toFixed(2)})`));
    raf = Math.abs(tx - cx) + Math.abs(ty - cy) > 0.002 ? requestAnimationFrame(follow) : 0;
  }
  if (!reduced) {
    addEventListener('pointermove', e => {
      const r = svg.getBoundingClientRect();
      if (!r.width) return;
      const fx = r.left + r.width / 2, fy = r.top + r.height * 0.3;
      tx = Math.max(-1, Math.min(1, (e.clientX - fx) / (innerWidth * 0.45)));
      ty = Math.max(-1, Math.min(1, (e.clientY - fy) / (innerHeight * 0.45)));
      if (!raf) raf = requestAnimationFrame(follow);
    }, { passive: true });
  }

  // the bow: head dips, body leans, she smiles with closed eyes, hearts float up
  let animations = [];
  function bow() {
    svg.classList.add('happy');
    if (reduced) return;
    animations.forEach(a => a.cancel());
    bowing = true;
    const opts = { duration: 2600, easing: 'cubic-bezier(.45,0,.25,1)' };
    const headFrames = [
      { transform: 'translate(0px,0px) rotate(0deg)' },
      { transform: 'translate(0px,38px) rotate(0deg) scale(1,.94)', offset: 0.35 },
      { transform: 'translate(0px,38px) rotate(0deg) scale(1,.94)', offset: 0.62 },
      { transform: 'translate(0px,0px) rotate(0deg)' },
    ];
    animations = [
      ...[...heads].map(h => h.animate(headFrames, opts)),
      body.animate([{ transform: 'scale(1,1)' }, { transform: 'scale(1,.965)', offset: 0.35 }, { transform: 'scale(1,.965)', offset: 0.62 }, { transform: 'scale(1,1)' }], opts),
      svg.querySelector('.km-hearts').animate([
        { opacity: 0, transform: 'translateY(20px) scale(.6)' }, { opacity: 1, transform: 'translateY(0) scale(1)', offset: 0.3 },
        { opacity: 1, transform: 'translateY(-26px) scale(1.05)', offset: 0.75 }, { opacity: 0, transform: 'translateY(-50px) scale(1)' }],
      { duration: 2800, easing: 'ease-out' }),
    ];
    animations[0].finished.then(() => { bowing = false; if (!raf) raf = requestAnimationFrame(follow); }).catch(() => {});
  }

  function moveTo(host) { host.append(wrap); }
  return {
    show() { moveTo(modalHost); setTimeout(bow, 250); },
    hide() { svg.classList.remove('happy'); moveTo(home); },
    replay() { bow(); },
  };
}
