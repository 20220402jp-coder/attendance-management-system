import * as THREE from './vendor/three.module.js';

// Style 12 · Tiny Planet.
// A smooth, stylised planet: glossy ocean, continents with soft elevation, a thin cloud
// layer and an atmosphere glow. Its lit side follows local time; a small office, trees,
// a moon and a satellite give it life. On success it celebrates inside the dialog.
// Returns {show, hide, replay} like the kimono character so clock.js can drive it.
export function mountPlanet(home, modalHost, dialog) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const lowEnd = (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 2;
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, lowEnd ? 1.25 : 2));
  renderer.setClearColor(0, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  const canvas = renderer.domElement;
  canvas.setAttribute('aria-hidden', 'true');
  home.append(canvas);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 120);
  const world = new THREE.Group(); scene.add(world);
  const spin = new THREE.Group(); world.add(spin);          // planet + things on it
  spin.rotation.z = 0.36;                                    // axial tilt
  const planet = new THREE.Group(); spin.add(planet);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s3 = new THREE.Vector3();

  // ── deterministic smooth noise (same planet on every device) ──
  function hash(x, y, z) {
    let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(z, 1274126177);
    h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }
  function vnoise(x, y, z) {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
    const xf = x - xi, yf = y - yi, zf = z - zi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
    const l = (a, b, t) => a + (b - a) * t;
    return l(
      l(l(hash(xi, yi, zi), hash(xi + 1, yi, zi), u), l(hash(xi, yi + 1, zi), hash(xi + 1, yi + 1, zi), u), v),
      l(l(hash(xi, yi, zi + 1), hash(xi + 1, yi, zi + 1), u), l(hash(xi, yi + 1, zi + 1), hash(xi + 1, yi + 1, zi + 1), u), v), w);
  }
  function fbm(x, y, z, octaves) {
    let sum = 0, amp = 0.5, f = 1, norm = 0;
    for (let i = 0; i < octaves; i++) { sum += amp * vnoise(x * f + i * 17.1, y * f, z * f); norm += amp; amp *= 0.5; f *= 2.03; }
    return sum / norm;
  }
  const SEA = 0.5;
  // elevation 0..1 for a unit direction; domain-warped so continents have organic outlines
  function elevation(x, y, z) {
    const wx = fbm(x * 1.3 + 7, y * 1.3, z * 1.3, 3) - 0.5, wy = fbm(x * 1.3, y * 1.3 + 3, z * 1.3, 3) - 0.5;
    let e = fbm(x * 1.25 + wx * 1.1, y * 1.25 + wy * 1.1, z * 1.25, lowEnd ? 4 : 5);
    e = (e - 0.5) * 1.9 + 0.5;                               // more contrast: clear coasts
    return e;
  }
  function radiusFor(e) {
    if (e <= SEA) return 1 - Math.min(0.05, (SEA - e) * 0.12);
    const t = e - SEA;
    return 1 + t * 0.09 + Math.max(0, t - 0.22) * 0.25;      // gentle hills, a few soft peaks
  }
  const C = {
    deep: new THREE.Color('#123f7a'), shallow: new THREE.Color('#2fb5c9'), sand: new THREE.Color('#f2dda4'),
    grass: new THREE.Color('#93d26d'), forest: new THREE.Color('#3f9b5f'), high: new THREE.Color('#b59b7a'), snow: new THREE.Color('#ffffff'),
  };
  const tmp = new THREE.Color();
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  function colorFor(e, lat) {
    if (e <= SEA) tmp.copy(C.deep).lerp(C.shallow, smooth(SEA - 0.18, SEA, e));
    else {
      const t = e - SEA;
      tmp.copy(C.sand).lerp(C.grass, smooth(0.0, 0.035, t));
      tmp.lerp(C.forest, smooth(0.06, 0.16, t));
      tmp.lerp(C.high, smooth(0.2, 0.3, t));
      tmp.lerp(C.snow, smooth(0.32, 0.38, t));
    }
    return tmp.lerp(C.snow, smooth(0.82, 0.92, lat));        // soft polar caps
  }

  // ── terrain: indexed sphere, normals from the height field (no seams, no facets) ──
  const segW = lowEnd ? 128 : 200, segH = lowEnd ? 84 : 132;
  const geo = new THREE.SphereGeometry(1, segW, segH);
  const pos = geo.attributes.position, nrm = geo.attributes.normal;
  const colors = new Float32Array(pos.count * 3);
  const d = new THREE.Vector3(), t1 = new THREE.Vector3(), t2 = new THREE.Vector3(), p0 = new THREE.Vector3(), p1 = new THREE.Vector3(), p2 = new THREE.Vector3();
  const surface = (dir, out) => out.copy(dir).multiplyScalar(radiusFor(elevation(dir.x, dir.y, dir.z)));
  const eps = 0.004;
  for (let i = 0; i < pos.count; i++) {
    d.fromBufferAttribute(pos, i).normalize();
    const e = elevation(d.x, d.y, d.z);
    p0.copy(d).multiplyScalar(radiusFor(e));
    pos.setXYZ(i, p0.x, p0.y, p0.z);
    t1.set(0, 1, 0).cross(d); if (t1.lengthSq() < 1e-6) t1.set(1, 0, 0); t1.normalize();
    t2.copy(d).cross(t1).normalize();
    surface(p1.copy(d).addScaledVector(t1, eps).normalize(), p1);
    surface(p2.copy(d).addScaledVector(t2, eps).normalize(), p2);
    p1.sub(p0); p2.sub(p0);
    const n = p2.cross(p1).normalize();
    if (n.dot(d) < 0) n.negate();
    nrm.setXYZ(i, n.x, n.y, n.z);
    const c = colorFor(e, Math.abs(d.y));
    colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  planet.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0 })));

  // glossy, slightly see-through ocean so shallow water glows near the coasts
  const ocean = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), new THREE.MeshPhysicalMaterial({
    color: '#1f7fc4', transparent: true, opacity: 0.62, roughness: 0.18, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.15,
  }));
  planet.add(ocean);

  // atmosphere: soft outer halo + thin rim on the planet's edge
  const glowVert = 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }';
  const halo = new THREE.Mesh(new THREE.SphereGeometry(1.22, 64, 48), new THREE.ShaderMaterial({
    uniforms: { c: { value: new THREE.Color('#6ec8ff') } }, vertexShader: glowVert,
    fragmentShader: 'uniform vec3 c; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(max(-dot(vN, vV), 0.0), 2.6) * 1.35; gl_FragColor = vec4(c * f, f); }',
    side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  world.add(halo);
  const rim = new THREE.Mesh(new THREE.SphereGeometry(1.025, 96, 64), new THREE.ShaderMaterial({
    uniforms: { c: { value: new THREE.Color('#9fdcff') } }, vertexShader: glowVert,
    fragmentShader: 'uniform vec3 c; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0 - max(dot(vN, vV), 0.0), 3.2) * 0.9; gl_FragColor = vec4(c * f, f); }',
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  world.add(rim);

  // thin cloud layer from 3D noise (seamless), drifting slowly
  const cw = lowEnd ? 256 : 512, ch = cw / 2;
  const cloudCanvas = document.createElement('canvas'); cloudCanvas.width = cw; cloudCanvas.height = ch;
  const cctx = cloudCanvas.getContext('2d'), img = cctx.createImageData(cw, ch);
  for (let y = 0; y < ch; y++) {
    const lat = (0.5 - y / ch) * Math.PI, cl = Math.cos(lat), sl = Math.sin(lat);
    for (let x = 0; x < cw; x++) {
      const lon = (x / cw) * Math.PI * 2;
      const v = fbm(-cl * Math.cos(lon) * 2.4 + 40, sl * 2.4, cl * Math.sin(lon) * 2.4, 4);
      const a = smooth(0.52, 0.72, v) * 0.85;
      const k = (y * cw + x) * 4;
      img.data[k] = img.data[k + 1] = img.data[k + 2] = 255; img.data[k + 3] = a * 255;
    }
  }
  cctx.putImageData(img, 0, 0);
  const cloudTex = new THREE.CanvasTexture(cloudCanvas); cloudTex.colorSpace = THREE.SRGBColorSpace;
  const cloudShell = new THREE.Mesh(new THREE.SphereGeometry(1.06, 96, 64),
    new THREE.MeshStandardMaterial({ map: cloudTex, transparent: true, depthWrite: false, roughness: 1 }));
  spin.add(cloudShell);
  const clouds = [{ pivot: cloudShell, speed: 0.025 }];

  // ── things on the surface (deterministic placement) ──
  let seed = 20261018;
  const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const up = new THREE.Vector3(0, 1, 0);
  function findSpot(minT, maxT) {
    for (let tries = 0; tries < 400; tries++) {
      const dir = new THREE.Vector3(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1);
      if (dir.lengthSq() > 1 || dir.lengthSq() < 0.01) continue;
      dir.normalize();
      const e = elevation(dir.x, dir.y, dir.z), t = e - SEA;
      if (t > minT && t < maxT && Math.abs(dir.y) < 0.72) return { dir, r: radiusFor(e) };
    }
    return null;
  }
  const treeCount = lowEnd ? 45 : 80;
  const leaves = new THREE.InstancedMesh(new THREE.ConeGeometry(0.022, 0.065, 8), new THREE.MeshStandardMaterial({ roughness: 0.8 }), treeCount);
  const trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.005, 0.006, 0.022, 6), new THREE.MeshStandardMaterial({ color: '#7a5233' }), treeCount);
  const leafColors = ['#2f8a4c', '#3c9e57', '#4caf50', '#2b7a45'].map(c => new THREE.Color(c));
  let planted = 0;
  for (let i = 0; i < treeCount; i++) {
    const spot = findSpot(0.04, 0.2); if (!spot) break;
    q.setFromUnitVectors(up, spot.dir);
    const k = 0.75 + rnd() * 0.5; s3.setScalar(k);
    m4.compose(spot.dir.clone().multiplyScalar(spot.r + 0.04 * k), q, s3); leaves.setMatrixAt(i, m4);
    m4.compose(spot.dir.clone().multiplyScalar(spot.r + 0.008 * k), q, s3); trunks.setMatrixAt(i, m4);
    leaves.setColorAt(i, leafColors[i % leafColors.length]);
    planted++;
  }
  leaves.count = trunks.count = planted;
  planet.add(leaves, trunks);

  // small offices whose windows light up at night
  const windowMat = new THREE.MeshStandardMaterial({ color: '#fff4c2', emissive: '#ffcf5a', emissiveIntensity: 0 });
  const wallMat = new THREE.MeshStandardMaterial({ color: '#fbf7ef', roughness: 0.7 });
  const roofMat = new THREE.MeshStandardMaterial({ color: '#ef7d57', roughness: 0.6 });
  for (let i = 0; i < 3; i++) {
    const spot = findSpot(0.02, 0.08); if (!spot) break;
    const b = new THREE.Group(), tall = i === 0 ? 0.075 : 0.05;
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.05, tall, 0.05), wallMat); body.position.y = tall / 2; b.add(body);
    const roof = new THREE.Mesh(new THREE.ConeGeometry(0.044, 0.034, 4), roofMat); roof.position.y = tall + 0.017; roof.rotation.y = Math.PI / 4; b.add(roof);
    for (let f = 0; f < (i === 0 ? 3 : 2); f++) {
      const win = new THREE.Mesh(new THREE.PlaneGeometry(0.03, 0.01), windowMat);
      win.position.set(0, 0.014 + f * 0.02, 0.0255); b.add(win);
      const back = win.clone(); back.position.z = -0.0255; back.rotation.y = Math.PI; b.add(back);
    }
    b.position.copy(spot.dir).multiplyScalar(spot.r - 0.004);
    b.quaternion.setFromUnitVectors(up, spot.dir);
    planet.add(b);
  }

  // moon and satellite
  const moonPivot = new THREE.Group(); moonPivot.rotation.x = 0.35; world.add(moonPivot);
  const moon = new THREE.Mesh(new THREE.SphereGeometry(0.15, 48, 32), new THREE.MeshStandardMaterial({ color: '#e7e2da', roughness: 0.95 }));
  moon.position.set(2.15, 0, 0); moonPivot.add(moon);
  const satPivot = new THREE.Group(); satPivot.rotation.set(-0.6, 0, 0.4); world.add(satPivot);
  const sat = new THREE.Group();
  sat.add(new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.045, 0.065), new THREE.MeshStandardMaterial({ color: '#e7e9ee', metalness: 0.7, roughness: 0.3 })));
  const panelMat = new THREE.MeshStandardMaterial({ color: '#2d5bd7', metalness: 0.5, roughness: 0.35, emissive: '#0d1f55' });
  for (const side of [-1, 1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.004, 0.04), panelMat); p.position.x = side * 0.075; sat.add(p); }
  sat.position.set(0, 0, 1.5); satPivot.add(sat);

  // round, softly glowing stars
  const dot = document.createElement('canvas'); dot.width = dot.height = 32;
  const dctx = dot.getContext('2d'), dg = dctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  dg.addColorStop(0, '#ffffffff'); dg.addColorStop(0.35, '#ffffffaa'); dg.addColorStop(1, '#ffffff00');
  dctx.fillStyle = dg; dctx.fillRect(0, 0, 32, 32);
  const starPos = [];
  for (let i = 0; i < (lowEnd ? 260 : 520); i++) {
    const a = rnd() * Math.PI * 2, b = Math.acos(2 * rnd() - 1), r = 30 + rnd() * 20;
    starPos.push(r * Math.sin(b) * Math.cos(a), r * Math.sin(b) * Math.sin(a), r * Math.cos(b));
  }
  const starGeo = new THREE.BufferGeometry(); starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPos, 3));
  const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ map: new THREE.CanvasTexture(dot), color: '#ffffff', size: 0.34, transparent: true, opacity: 0.85, depthWrite: false, sizeAttenuation: true }));
  scene.add(stars);

  // lights: warm sun follows local time (noon faces you), cool rim light from behind
  const sun = new THREE.DirectionalLight('#fff0d8', 2.8); scene.add(sun);
  const rimLight = new THREE.DirectionalLight('#7fb8ff', 1.1); rimLight.position.set(-4, 2, -5); scene.add(rimLight);
  scene.add(new THREE.HemisphereLight('#cfe6ff', '#1c1438', 0.55));
  function daypart() {
    const now = new Date(), hours = now.getHours() + now.getMinutes() / 60;
    const theta = (hours - 12) / 24 * Math.PI * 2;
    sun.position.set(Math.sin(theta) * 6, 2.4, Math.cos(theta) * 6 + 1.5);
    const light = Math.max(0, Math.cos(theta));
    windowMat.emissiveIntensity = 1.8 * (1 - Math.min(1, light * 1.6));
    const part = hours < 5 || hours >= 19 ? 'night' : hours < 9 ? 'dawn' : hours < 16 ? 'day' : 'dusk';
    if (document.body.dataset.daypart !== part) {
      document.body.dataset.daypart = part;
      const label = document.getElementById('daypart');
      if (label) label.textContent = label.dataset[part] || '';
    }
  }
  daypart();
  setInterval(daypart, 60000);

  // ── celebration pieces ──
  const accent = new THREE.Color('#ffd166');
  const rings = [0, 1].map(i => {
    const m = new THREE.Mesh(new THREE.TorusGeometry(1, 0.012, 6, 96),
      new THREE.MeshBasicMaterial({ color: i ? '#7bdff2' : accent, transparent: true, opacity: 0, depthWrite: false }));
    m.rotation.x = Math.PI / 2 - 0.35 + i * 0.5; m.rotation.y = i * 0.4; world.add(m); return m;
  });
  const sparkCount = lowEnd ? 36 : 70;
  const sparks = new THREE.InstancedMesh(new THREE.OctahedronGeometry(0.035, 0), new THREE.MeshBasicMaterial({ color: '#ffffff' }), sparkCount);
  const sparkPalette = ['#ffd166', '#7bdff2', '#f7aef8', '#ffffff', '#9ef01a'].map(c => new THREE.Color(c));
  const sparkDirs = [];
  for (let i = 0; i < sparkCount; i++) {
    const d = new THREE.Vector3().randomDirection();
    sparkDirs.push({ d, speed: 1.2 + Math.random() * 1.4, spin: Math.random() * 6 });
    sparks.setColorAt(i, sparkPalette[i % sparkPalette.length]);
  }
  sparks.visible = false; world.add(sparks);
  let celebrateAt = -100;

  // ── layout: where the planet sits on screen ──
  let host = home;
  function layout() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    let cx = w / 2, cy = h / 2, R;
    if (host === modalHost) R = Math.min(w, h) * 0.2;
    else if (w >= 820) { const free = w - Math.min(420, w * 0.42); cx = free / 2; cy = h * 0.43; R = Math.min(free, h) * 0.2; }
    else { cy = Math.min(h * 0.24, 200); R = Math.min(w * 0.3, h * 0.17); }
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    camera.position.set(0, 0, (h / 2) / (tanHalf * R));
    camera.lookAt(0, 0, 0);
    if (cx !== w / 2 || cy !== h / 2) camera.setViewOffset(w, h, w / 2 - cx, h / 2 - cy, w, h); else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  const ro = new ResizeObserver(layout); ro.observe(home); ro.observe(modalHost); layout();

  // ── drag to spin (horizontal only, so vertical page scrolling still works on phones) ──
  let dragging = false, lastX = 0, velocity = 0, tiltX = 0, tiltY = 0;
  canvas.style.touchAction = 'pan-y';
  canvas.addEventListener('pointerdown', e => { if (host !== home) return; dragging = true; lastX = e.clientX; canvas.setPointerCapture?.(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (!dragging) return; velocity = (e.clientX - lastX) * 0.006; lastX = e.clientX; spin.rotation.y += velocity; });
  const endDrag = () => { dragging = false; };
  canvas.addEventListener('pointerup', endDrag); canvas.addEventListener('pointercancel', endDrag);
  addEventListener('pointermove', e => { if (host !== home || dragging) return; tiltY = (e.clientX / innerWidth - 0.5) * 0.25; tiltX = (e.clientY / innerHeight - 0.5) * 0.18; }, { passive: true });

  // ── render loop ──
  let last = performance.now();
  renderer.setAnimationLoop(ms => {
    if (document.hidden) { last = ms; return; }
    const dt = Math.min(0.05, (ms - last) / 1000); last = ms;
    const t = ms / 1000;
    if (!reduced) {
      if (!dragging) { velocity *= 0.95; spin.rotation.y += 0.06 * dt + velocity; }
      clouds.forEach(c => { c.pivot.rotation.y += c.speed * dt; });
      moonPivot.rotation.y += 0.12 * dt;
      const e = t - celebrateAt;
      satPivot.rotation.y += (e >= 0 && e < 1.6 ? 4.5 : 0.35) * dt;
      world.rotation.x += (tiltX - world.rotation.x) * 0.04;
      world.rotation.y += (tiltY - world.rotation.y) * 0.04;
      stars.rotation.y += 0.004 * dt;

      // celebration timeline
      if (e >= 0 && e < 2.4) {
        const bounce = e < 0.15 ? 1 - e * 0.8 : 1 + Math.sin((e - 0.15) * 9) * Math.exp(-(e - 0.15) * 3.2) * 0.12;
        planet.scale.setScalar(bounce);
        rings.forEach((r, i) => {
          const k = Math.max(0, e - i * 0.18) / 1.4;
          r.scale.setScalar(1.05 + k * 1.7);
          r.material.opacity = k > 0 && k < 1 ? (1 - k) * 0.9 : 0;
        });
        sparks.visible = true;
        for (let i = 0; i < sparkCount; i++) {
          const s = sparkDirs[i], dist = 1.0 + s.speed * (1 - Math.exp(-e * 2.2));
          const size = Math.max(0, 1 - e / 2.2);
          q.setFromEuler(new THREE.Euler(e * s.spin, e * s.spin * 0.7, 0));
          s3.setScalar(size);
          m4.compose(s.d.clone().multiplyScalar(dist), q, s3);
          sparks.setMatrixAt(i, m4);
        }
        sparks.instanceMatrix.needsUpdate = true;
      } else if (sparks.visible) {
        sparks.visible = false; planet.scale.setScalar(1); rings.forEach(r => { r.material.opacity = 0; });
      }
    }
    renderer.render(scene, camera);
  });

  home.dataset.ready = 'true';
  document.body.classList.add('has-3d');
  canvas.addEventListener('webglcontextlost', () => document.body.classList.remove('has-3d'));

  function moveTo(target) { host = target; target.append(canvas); layout(); }
  return {
    show() { dialog?.classList.add('has-3d'); moveTo(modalHost); celebrateAt = performance.now() / 1000 + 0.25; },
    hide() { moveTo(home); },
    replay() { celebrateAt = performance.now() / 1000; },
  };
}
