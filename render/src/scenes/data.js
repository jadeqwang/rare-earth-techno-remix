// Data scenes: SETI waterfall, the Wow! printout, a pulsing star, planetary transits.
import * as THREE from 'three';
import { C2D, font } from '../c2d.js';
import { INK, css, clamp, range, smooth, easeOutCubic, easeInOutCubic, hash2, hash1, lerp, pulse } from '../util.js';
import { drawGlyph } from '../type.js';
import { skyMaterial, setSky } from './sky.js';

let c2d = null;
const K = () => c2d;

// ------------------------------------------------------------------ WATERFALL
const wf = { cv: null, ctx: null, img: null, cols: 160, rows: 96 };
function waterfallImage(t, p) {
  if (!wf.cv) {
    wf.cv = document.createElement('canvas'); wf.cv.width = wf.cols; wf.cv.height = wf.rows;
    wf.ctx = wf.cv.getContext('2d'); wf.img = wf.ctx.createImageData(wf.cols, wf.rows);
  }
  const light = p.mode === 'light';
  const rowRate = 20; // rows per second (scroll)
  const top = Math.floor(t * rowRate);
  const d = wf.img.data;
  const sigStart = p.signalAt ?? 1e9;
  for (let r = 0; r < wf.rows; r++) {
    const row = top - r;                 // row index in time; r=0 is newest (top)
    const rt = row / rowRate;
    const on = rt >= sigStart;
    const sx = 80 + (rt - sigStart) * 1.1 + 3 * Math.sin(rt * 0.7); // drifting narrowband carrier
    for (let c = 0; c < wf.cols; c++) {
      let v = Math.pow(-Math.log(Math.max(1e-4, hash2(c * 1.37, row * 0.91))) * 0.3, 1.6);   // chi^2-ish noise, sparse bright specks
      v += 0.08 * Math.sin(c * 0.05 + row * 0.01);
      if (on) v += 2.6 * Math.exp(-Math.pow((c - sx) / 0.7, 2));
      v = clamp(v);
      const i = (r * wf.cols + c) * 4;
      if (light) {
        const k = v * v;
        d[i] = 255 * (0.02 + k * INK.yellow[0] * 0.9 + v * 0.05); d[i + 1] = 255 * (0.03 + k * 0.85 + v * INK.mint[1] * 0.35); d[i + 2] = 255 * (0.06 + v * INK.mint[2] * 0.35);
      } else {
        // paper -> klein
        const k = Math.pow(v, 0.8);
        d[i] = 255 * lerp(INK.paper[0], INK.klein[0] * 0.8, k); d[i + 1] = 255 * lerp(INK.paper[1], INK.klein[1] * 0.8, k); d[i + 2] = 255 * lerp(INK.paper[2], INK.klein[2] * 0.9, k);
        if (on && Math.abs(c - sx) < 1.2) { d[i] = 255 * INK.orange[0]; d[i + 1] = 255 * INK.orange[1]; d[i + 2] = 255 * INK.orange[2]; }
      }
      d[i + 3] = 255;
    }
  }
  wf.ctx.putImageData(wf.img, 0, 0);
  return wf.cv;
}

export const waterfall = {
  init(ctx) { if (!c2d) c2d = new C2D(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const light = p.mode === 'light';
    const c = K().begin(light ? '#05060c' : css(INK.paper));
    const img = waterfallImage(t, p);
    const X = 150, Y = 120, Wd = 1340, Ht = 820;
    const z = 1 + lt * 0.05;
    c.save();
    c.translate(960, 540); c.scale(z, z); c.translate(-960, -540);
    c.imageSmoothingEnabled = false;
    c.drawImage(img, X, Y, Wd, Ht);
    c.imageSmoothingEnabled = true;
    const fg = light ? css(INK.mint) : css(INK.ink);
    c.strokeStyle = fg; c.lineWidth = 3; c.strokeRect(X, Y, Wd, Ht);
    font(c, 'JetBrainsMono', 22, 600);
    c.fillStyle = fg;
    c.fillText('1420.39 MHz', X, Y + Ht + 36); c.fillText('1420.42 MHz', X + Wd - 150, Y + Ht + 36);
    c.fillText('WATERFALL  ·  Δt 33 ms  ·  RBW 2.8 Hz', X, Y - 22);
    // side panel: detection readout
    const on = t >= (p.signalAt ?? 1e9);
    const px = X + Wd + 40;
    font(c, 'JetBrainsMono', 24, 700);
    const lines = on ? ['CANDIDATE', 'NARROWBAND', `SNR  ${(18 + (t - p.signalAt) * 9).toFixed(1)}`, 'DRIFT  +0.38 Hz/s', 'NOT RFI', `Δ ${(t % 10).toFixed(2)}s`] : ['SEARCHING', '...', 'SNR  < 3', '', '', ''];
    lines.forEach((s, i) => { c.fillStyle = i === 0 && on ? (light ? css(INK.yellow) : css(INK.orange)) : fg; c.fillText(s, px, Y + 40 + i * 40); });
    if (on) {
      // bracket around the carrier
      const rowRate = 30;
      const sx = 80 + (t - p.signalAt) * 1.1;
      const bx = X + ((sx + 0.5) / 160) * Wd;
      const k = easeOutCubic(clamp((t - p.signalAt) / 0.25));
      c.strokeStyle = light ? css(INK.yellow) : css(INK.orange); c.lineWidth = 4;
      const w = lerp(300, 46, k);
      c.strokeRect(bx - w / 2, Y + 20, w, Ht * 0.45 * k + 20);
    }
    c.restore();
    K().end({ halftone: light ? 0 : 0.0 });
  },
};

// ------------------------------------------------------------------ WOW! printout
export const wow = {
  init(ctx) { if (!c2d) c2d = new C2D(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const c = K().begin('#1a1a22');
    // camera: push into the circled column with a slight rotation
    const z = 1.25 + lt * 0.5;
    c.save();
    c.translate(960, 540); c.rotate(-0.05 + lt * 0.02); c.scale(z, z); c.translate(-900, -520);
    // continuous-feed paper with tractor holes
    c.fillStyle = '#efeadc'; c.fillRect(420, -200, 1000, 1500);
    c.fillStyle = '#1a1a22';
    for (let y = -180; y < 1300; y += 38) { c.beginPath(); c.arc(450, y, 9, 0, 7); c.fill(); c.beginPath(); c.arc(1390, y, 9, 0, 7); c.fill(); }
    c.strokeStyle = 'rgba(0,0,0,0.12)'; c.setLineDash([6, 6]); c.beginPath(); c.moveTo(480, -200); c.lineTo(480, 1300); c.moveTo(1360, -200); c.lineTo(1360, 1300); c.stroke(); c.setLineDash([]);
    font(c, 'VT323', 44);
    const codes = ' 11 1 2  1 3 1  21  1 1';
    const col = ['6', 'E', 'Q', 'U', 'J', '5'];
    for (let r = 0; r < 26; r++) {
      let s = '';
      for (let k = 0; k < 22; k++) s += codes[Math.floor(hash2(r, k) * codes.length)];
      c.fillStyle = 'rgba(30,30,40,0.85)';
      c.fillText(s, 520, 60 + r * 40);
      const j = r - 10;
      if (j >= 0 && j < 6) { c.fillStyle = '#efeadc'; c.fillRect(520 + 13 * 20.2 - 2, 60 + r * 40 - 34, 24, 40); c.fillStyle = 'rgba(10,10,18,1)'; c.fillText(col[j], 520 + 13 * 20.2, 60 + r * 40); }
    }
    // red pen circle drawn on
    const k = clamp((t - (p.circleAt ?? shot.t0 + 0.05)) / 0.3);
    if (k > 0) {
      c.strokeStyle = 'rgba(220,30,40,0.95)'; c.lineWidth = 7; c.lineCap = 'round';
      c.beginPath();
      const cx = 792, cy = 548, rx = 52, ry = 140;
      for (let a = 0; a <= k * Math.PI * 2.15; a += 0.05) {
        const rr = 1 + 0.04 * Math.sin(a * 3);
        const x = cx + Math.cos(a - 1.2) * rx * rr, y = cy + Math.sin(a - 1.2) * ry * rr;
        if (a === 0) c.moveTo(x, y); else c.lineTo(x, y);
      }
      c.stroke();
      if (k > 0.8) { font(c, 'InstrumentSerifI', 110); c.fillStyle = 'rgba(220,30,40,0.95)'; c.fillText('Wow!', 880, 420); }
    }
    c.restore();
    K().end({ halftone: 0.35 });
  },
};

// ------------------------------------------------------------------ STAR (JWST-style spikes, pulsing)
let starMat = null;
export const star = {
  init(ctx) {
    starMat = ctx.engine.shader(/* glsl */`
      uniform vec2 res; uniform float S; uniform float time; uniform float kick; uniform float pulseA;
      void main(){
        vec2 px = vUv * res / S; vec2 d = px - vec2(960., 470.);
        float r = length(d);
        float core = exp(-r / (22. + 30. * kick));
        float halo = exp(-r / 180.) * .35;
        float sp = 0.;
        for (int i = 0; i < 3; i++) { float a = float(i) * 1.0472 + 1.5708; vec2 dir = vec2(cos(a), sin(a));
          float along = abs(dot(d, dir)); float across = abs(dot(d, vec2(-dir.y, dir.x)));
          sp += exp(-across / (1.6 + kick * 2.)) * exp(-along / (380. + 260. * kick)); }
        float hz = exp(-abs(d.y) / 1.2) * exp(-abs(d.x) / 260.) * .7;
        float ring = exp(-pow((r - 90. - kick * 60.) / 6., 2.)) * .25 * kick;
        vec3 col = vec3(1., .93, .8) * (core * 2. + sp * 1.2 + hz) + vec3(.6, .8, 1.) * (halo + ring);
        col *= .6 + pulseA * .8;
        col += vec3(.01, .012, .025);
        fragColor = vec4(col, 1.);
      }`, { res: { value: new THREE.Vector2(ctx.engine.W, ctx.engine.H) }, S: { value: ctx.engine.S }, time: { value: 0 }, kick: { value: 0 }, pulseA: { value: 1 } });
  },
  async draw(ctx, shot, t, lt) {
    const sm = skyMaterial(ctx.engine);
    setSky(sm.uniforms, { mode: 'light', band: 0.5, density: 1.4, twinkle: 1 }, ctx);
    ctx.engine.pass(sm, ctx.engine.rtScene);
    const u = starMat.uniforms; u.time.value = t; u.kick.value = ctx.audio.kick(t, 0.14);
    u.pulseA.value = 0.5 + 0.5 * Math.cos(t * Math.PI * 2 / ctx.audio.beat(t).period);
    starMat.transparent = true; starMat.blending = THREE.AdditiveBlending;
    ctx.engine.renderer.autoClear = false;
    ctx.engine.quadMesh.material = starMat; ctx.engine.renderer.setRenderTarget(ctx.engine.rtScene);
    ctx.engine.renderer.render(ctx.engine.quadScene, ctx.engine.quadCam);
    ctx.engine.renderer.autoClear = true;
  },
};

// ------------------------------------------------------------------ TRANSIT + light curve
function drawStarDisk(c, cx, cy, R, col, ink, light) {
  // limb darkening: bright center falling toward a crisp edge
  const g = c.createRadialGradient(cx, cy, 0, cx, cy, R);
  g.addColorStop(0, light ? '#fff6e0' : col); g.addColorStop(0.55, col); g.addColorStop(0.97, light ? col : ink); g.addColorStop(1, light ? 'rgba(0,0,0,0)' : ink);
  c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, 7); c.fill();
  if (!light) { c.strokeStyle = ink; c.lineWidth = 4; c.beginPath(); c.arc(cx, cy, R, 0, 7); c.stroke(); }
}
function lightCurve(c, x, y, w, h, k, depth, col, lw = 4, label = true) {
  // k = transit progress (0..1 over the plotted window); planet crosses in the middle 60%
  c.strokeStyle = col; c.lineWidth = lw; c.beginPath();
  const N = 200;
  for (let i = 0; i <= N * k; i++) {
    const u = i / N;
    const inside = clamp((u - 0.2) / 0.08) * (1 - clamp((u - 0.72) / 0.08));
    const f = 1 - depth * inside + (hash1(i * 3.1) - 0.5) * 0.012;
    const px = x + u * w, py = y + (1 - f) * h * 6;
    if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
  }
  c.stroke();
}
// circle-circle overlap area (for an honest transit dip)
function overlap(d, R, r) {
  if (d >= R + r) return 0;
  if (d <= R - r) return Math.PI * r * r;
  const a = Math.acos((d * d + r * r - R * R) / (2 * d * r)), b = Math.acos((d * d + R * R - r * r) / (2 * d * R));
  return r * r * a + R * R * b - 0.5 * Math.sqrt(Math.max(0, (-d + r + R) * (d + r - R) * (d - r + R) * (d + r + R)));
}
export const transit = {
  init(ctx) { if (!c2d) c2d = new C2D(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const k = clamp((t - p.t0) / (p.t1 - p.t0));
    const c = K().begin(css(INK.klein));
    // faint star field
    c.fillStyle = 'rgba(243,239,230,0.55)';
    for (let i = 0; i < 140; i++) { c.beginPath(); c.arc(hash1(i) * 1920, hash1(i + 50) * 760, 0.8 + hash1(i + 9) * 1.6, 0, 7); c.fill(); }
    const cx = 960, cy = 400, R = 270, r = 62;
    // star with limb darkening + granulation, crisp edge
    const g = c.createRadialGradient(cx - 40, cy - 40, 10, cx, cy, R);
    g.addColorStop(0, '#ffd9a0'); g.addColorStop(0.55, css(INK.orange)); g.addColorStop(1, '#c2360c');
    c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, 7); c.fill();
    c.save(); c.beginPath(); c.arc(cx, cy, R, 0, 7); c.clip();
    for (let i = 0; i < 260; i++) {
      const a = hash1(i * 1.3) * 7, rr = Math.sqrt(hash1(i * 2.7)) * R;
      c.fillStyle = `rgba(255,230,190,${0.06 + 0.08 * hash1(i * 5.1)})`;
      c.beginPath(); c.arc(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, 6 + hash1(i * 3.3) * 12, 0, 7); c.fill();
    }
    c.restore();
    // planet crossing, with a thin sunlit atmosphere rim
    const px = lerp(cx - R - 160, cx + R + 160, easeInOutCubic(range(k, 0.0, 1.0)));
    const py = cy + 70;
    c.fillStyle = css(INK.ink); c.beginPath(); c.arc(px, py, r, 0, 7); c.fill();
    c.strokeStyle = 'rgba(156,203,255,0.9)'; c.lineWidth = 3; c.beginPath(); c.arc(px, py, r + 2, 0, 7); c.stroke();
    // light curve panel, dip = true geometric overlap
    const X = 210, Y = 760, Wd = 1500, Ht = 230;
    c.fillStyle = css(INK.paper); c.fillRect(X, Y, Wd, Ht);
    c.strokeStyle = 'rgba(11,11,20,0.15)'; c.lineWidth = 1;
    for (let gx = X; gx <= X + Wd; gx += 75) { c.beginPath(); c.moveTo(gx, Y); c.lineTo(gx, Y + Ht); c.stroke(); }
    const flux = (u) => { const x = lerp(cx - R - 160, cx + R + 160, easeInOutCubic(u)); const d = Math.hypot(x - cx, py - cy); return 1 - overlap(d, R, r) / (Math.PI * R * R); };
    const minF = 1 - (r * r) / (R * R);
    c.strokeStyle = css(INK.ink); c.lineWidth = 6; c.lineJoin = 'round'; c.beginPath();
    const N = 240;
    for (let i = 0; i <= N * k; i++) {
      const u = i / N; const f = flux(u) + (hash1(i * 7.7) - 0.5) * 0.004;
      const yy = Y + 40 + (1 - f) / (1 - minF) * (Ht - 80);
      const xx = X + 20 + u * (Wd - 40);
      if (i === 0) c.moveTo(xx, yy); else c.lineTo(xx, yy);
    }
    c.stroke();
    const f = flux(k);
    const hx = X + 20 + k * (Wd - 40), hy = Y + 40 + (1 - f) / (1 - minF) * (Ht - 80);
    c.fillStyle = css(INK.orange); c.beginPath(); c.arc(hx, hy, 11, 0, 7); c.fill();
    font(c, 'JetBrainsMono', 22, 700); c.fillStyle = css(INK.ink);
    c.fillText('RELATIVE FLUX', X + 16, Y + 28); c.fillText(`${(f * 100).toFixed(2)}%`, X + Wd - 130, Y + 28);
    c.fillText('TIME →', X + Wd - 110, Y + Ht - 14);
    K().end({ halftone: 0.25 });
  },
};

// ------------------------------------------------------------------ MUTUAL TRANSIT -> heartbeat
export const mutual = {
  init(ctx) { if (!c2d) c2d = new C2D(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const A = ctx.audio;
    const k = clamp((t - p.t0) / (p.t1 - p.t0));
    const c = K().begin('#04050b');
    const merge = smooth(range(k, 0.6, 0.85));
    const R = 190, pr = 44, cy = 430;
    const sides = [
      { cx: lerp(500, 960, merge), col: 'rgba(255,140,110,1)', planet: css(INK.pink), rgb: '255,72,176', label: 'ETZ-1715 b  ·  SEEN FROM EARTH', ph0: 0.0 },
      { cx: lerp(1420, 960, merge), col: 'rgba(255,225,140,1)', planet: css(INK.pale), rgb: '156,203,255', glyphs: 'EARTH SEEN FROM HOME', ph0: 0.05 },
    ];
    // the line of sight between the two systems
    if (merge < 0.99) {
      const a = 1 - merge;
      c.setLineDash([10, 12]); c.strokeStyle = `rgba(255,225,77,${0.65 * a})`; c.lineWidth = 2;
      c.beginPath(); c.moveTo(sides[0].cx + R + 40, cy); c.lineTo(sides[1].cx - R - 40, cy); c.stroke(); c.setLineDash([]);
      font(c, 'JetBrainsMono', 24, 600); c.fillStyle = `rgba(255,225,77,${0.95 * a})`;
      const s217 = '217 LY'; c.fillText(s217, (sides[0].cx + sides[1].cx) / 2 - c.measureText(s217).width / 2, cy - 16);
    }
    for (const [i, s] of sides.entries()) {
      const alpha = 1 - merge * (i === 1 ? 0.5 : 0);
      c.globalAlpha = alpha;
      drawStarDisk(c, s.cx, cy, R, s.col, '#04050b', true);
      // each world watches the other cross its star (planet path offset a little below the equator)
      const xOf = (u) => lerp(s.cx - R - pr - 30, s.cx + R + pr + 30, easeInOutCubic(range(u, 0.05 + s.ph0, 0.6 + s.ph0)));
      const px = xOf(k), py = cy + 34;
      c.fillStyle = '#04050b'; c.beginPath(); c.arc(px, py, pr, 0, 7); c.fill();
      c.strokeStyle = s.planet; c.lineWidth = 3; c.beginPath(); c.arc(px, py, pr, 0, 7); c.stroke();
      c.globalAlpha = alpha * (1 - merge);
      if (s.glyphs) { let xx = s.cx - 200; for (const ch of s.glyphs) { drawGlyph(c, ch, xx, 692, 28, s.planet, 0.09); xx += 22; } }
      else { font(c, 'JetBrainsMono', 26, 600); c.fillStyle = s.planet; c.fillText(s.label, s.cx - c.measureText(s.label).width / 2, 692); }
      // honest light curve (flux = 1 - covered area / disc area, depth drawn x6 so the dip reads) in a small panel
      if (merge < 1) {
        const x0 = s.cx - 250, w = 500, y0 = 730, h = 110;
        c.globalAlpha = alpha * Math.pow(1 - merge, 3);
        c.strokeStyle = `rgba(${s.rgb},0.35)`; c.lineWidth = 1.5; c.strokeRect(x0, y0, w, h);
        c.strokeStyle = `rgba(${s.rgb},0.95)`; c.lineWidth = 4; c.beginPath();
        const N = 120, area = Math.PI * R * R;
        for (let j = 0; j <= N; j++) {
          const u = (j / N) * k;
          const d = Math.hypot(xOf(u) - s.cx, 34);
          const f = 1 - 6 * overlap(d, R, pr) / area + (hash1(j * 3.1 + i) - 0.5) * 0.01;
          const X = x0 + (j / N) * w * k, Y = y0 + 18 + (1 - f) * (h - 30);
          if (j === 0) c.moveTo(X, Y); else c.lineTo(X, Y);
        }
        c.stroke();
      }
    }
    c.globalAlpha = 1;
    // then the two dips become one heartbeat, pulsing on the kicks
    if (merge > 0) {
      const y = 820;
      c.globalAlpha = merge;
      c.strokeStyle = css(INK.yellow); c.lineWidth = 5; c.beginPath();
      for (let x = 160; x <= 1760; x += 4) {
        const tt = t - (1760 - x) / 900;           // scrolling trace
        const b = A.kick(tt, 0.06);
        const yy = y + 60 - b * 170 * Math.sin((x * 0.09)) - b * 60;
        if (x === 160) c.moveTo(x, yy); else c.lineTo(x, yy);
      }
      c.stroke(); c.globalAlpha = 1;
    }
    K().end({});
  },
};

