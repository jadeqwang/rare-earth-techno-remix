// WAR: "before they launch or self-destruct". The Drake equation's L drawn as the way a civilization can end itself:
// the night side of Earth over the pole, missile tracks rising between the silo fields like an early-warning display,
// the warheads landing on the cities, the lights going out. On "or": the same launch, a different payload.
import { skyMaterial, setSky } from './sky.js';
import { earthMaterial, setEarth } from './earth.js';
import { C2D, font } from '../c2d.js';
import { INK, css, clamp, range, smooth, easeOutCubic, easeInCubic, lerp, hash1, hash2 } from '../util.js';

let c2d = null;
const K = (ctx) => (c2d ||= new C2D(ctx.engine));
const D2R = Math.PI / 180;

// ---------------------------------------------------------------- the globe, and where a lat/lon lands on screen
// The inverse of the earth shader's lookup (scenes/earth.js): screen -> view normal n -> g = rotY(rotX(n, -lat0), lon0).
// Returns canvas design px (y down), and whether the point is in front of the globe or outside its disc.
export function globeProject(view, lat, lon, h = 0) {
  const la = lat * D2R, lo = lon * D2R;
  const g = [Math.cos(la) * Math.sin(lo), Math.sin(la), Math.cos(la) * Math.cos(lo)];
  const a = -view.lon * D2R, b = view.lat * D2R;
  const y1 = [Math.cos(a) * g[0] + Math.sin(a) * g[2], g[1], -Math.sin(a) * g[0] + Math.cos(a) * g[2]];
  const n = [y1[0], Math.cos(b) * y1[1] - Math.sin(b) * y1[2], Math.sin(b) * y1[1] + Math.cos(b) * y1[2]];
  const s = 1 + h;
  const qa = [n[0] * s, n[1] * s];
  // the shader applies q = rot(roll) * q with GLSL's column-major mat2(c,-s,s,c): undo it
  const c = Math.cos(view.roll ?? 0), si = Math.sin(view.roll ?? 0);
  const qb = [c * qa[0] - si * qa[1], si * qa[0] + c * qa[1]];
  const x = view.center[0] + view.radius * qb[0];
  const yUp = view.center[1] + view.radius * qb[1];
  const vis = n[2] > 0 || qa[0] * qa[0] + qa[1] * qa[1] > 1;
  return [x, 1080 - yUp, vis];
}

// unit vector <-> lat/lon, and the great circle between two points
const vec = (lat, lon) => [Math.cos(lat * D2R) * Math.sin(lon * D2R), Math.sin(lat * D2R), Math.cos(lat * D2R) * Math.cos(lon * D2R)];
const toLL = (v) => [Math.asin(clamp(v[1], -1, 1)) / D2R, Math.atan2(v[0], v[2]) / D2R];
function slerp(p, q, s) {
  const d = clamp(p[0] * q[0] + p[1] * q[1] + p[2] * q[2], -1, 1), w = Math.acos(d);
  if (w < 1e-6) return p;
  const A = Math.sin((1 - s) * w) / Math.sin(w), B = Math.sin(s * w) / Math.sin(w);
  return [A * p[0] + B * q[0], A * p[1] + B * q[1], A * p[2] + B * q[2]];
}

// ---------------------------------------------------------------- the exchange
// Launch areas: the missile fields of the Great Plains and of central Russia, and submarines at sea. Targets: major
// cities on both sides. Everything is deterministic (hash-seeded), so every render draws the same war.
const SITES_A = [[47.5, -111.2], [48.4, -101.4], [41.1, -104.8], [44, -140], [40, -45]];              // US fields, Pacific, Atlantic
const SITES_B = [[54.0, 35.8], [51.7, 45.6], [55.3, 89.8], [51.0, 59.8], [70, 20], [62, 170]];        // Russian fields, Barents, Bering
const TARGETS_A = [[40.72, -74.0], [34.05, -118.23], [41.85, -87.64], [38.9, -77.0], [29.76, -95.37], [47.6, -122.3],
  [37.77, -122.42], [42.36, -71.06], [39.74, -104.99], [33.75, -84.39], [25.79, -80.23], [43.66, -79.39], [45.5, -73.57],
  [49.28, -123.12], [32.77, -96.8], [44.98, -93.27], [39.95, -75.18], [51.5, -0.12], [48.86, 2.35], [52.52, 13.4]];
const TARGETS_B = [[55.75, 37.61], [59.94, 30.31], [55.03, 82.92], [56.84, 60.6], [53.2, 50.15], [54.99, 73.37], [43.12, 131.9],
  [56.33, 44.0], [48.72, 44.5], [55.8, 49.1], [52.29, 104.3], [47.23, 39.7], [58.0, 56.25], [51.67, 39.2], [69.0, 33.1]];

function exchange(t0) {
  const out = [];
  let k = 0;
  const add = (sites, targets, tLaunch, spread) => {
    for (let i = 0; i < targets.length; i++, k++) {
      const s = sites[Math.floor(hash2(k, 1) * sites.length)];
      const tl = t0 + tLaunch + hash2(k, 2) * spread;
      out.push({ from: s, to: targets[i], tl, ti: t0 + 0.82 + hash2(k, 3) * 0.36, h: 0.16 + 0.1 * hash2(k, 4), k });
    }
  };
  add(SITES_A, TARGETS_B, 0.02, 0.26);   // first launches, then the answer
  add(SITES_B, TARGETS_A, 0.12, 0.32);
  return out;
}

// ---------------------------------------------------------------- drawing
function track(c, view, m, t) {
  const p = vec(...m.from), q = vec(...m.to);
  const u = clamp((t - m.tl) / (m.ti - m.tl));
  if (u <= 0) return null;
  const f = easeInCubic(u) * 0.35 + u * 0.65;      // the boost is slow, then it coasts
  const N = 40;
  let prev = null, head = null;
  c.beginPath();
  for (let i = 0; i <= N; i++) {
    const s = f * i / N;
    const [la, lo] = toLL(slerp(p, q, s));
    const pt = globeProject(view, la, lo, m.h * 4 * s * (1 - s));
    if (pt[2]) { if (prev && prev[2]) c.lineTo(pt[0], pt[1]); else c.moveTo(pt[0], pt[1]); }
    prev = pt; head = pt;
  }
  return head;
}

function flash(c, x, y, age, big) {
  // the fireball: white core, then a ring running out, an ember that stays
  const core = Math.exp(-age / 0.06), r = (10 + 90 * easeOutCubic(clamp(age / 0.25))) * big;
  let g = c.createRadialGradient(x, y, 0, x, y, r * 1.6);
  g.addColorStop(0, `rgba(255,255,255,${0.95 * core})`); g.addColorStop(0.25, `rgba(255,236,190,${0.8 * core})`);
  g.addColorStop(1, 'rgba(255,90,40,0)');
  c.fillStyle = g; c.fillRect(x - r * 1.7, y - r * 1.7, r * 3.4, r * 3.4);
  const ra = Math.max(0, 1 - age / 0.45);
  if (ra > 0) {
    c.strokeStyle = `rgba(255,200,150,${0.7 * ra})`; c.lineWidth = 2.5 * big;
    c.beginPath(); c.ellipse(x, y, r * 1.2, r * 0.8, 0, 0, Math.PI * 2); c.stroke();
  }
  const em = 0.55 * Math.min(1, age / 0.15);
  g = c.createRadialGradient(x, y, 0, x, y, 26 * big);
  g.addColorStop(0, `rgba(255,120,50,${em})`); g.addColorStop(1, 'rgba(255,40,20,0)');
  c.fillStyle = g; c.fillRect(x - 30 * big, y - 30 * big, 60 * big, 60 * big);
}

export const war = {
  async draw(ctx, shot, t, lt) {
    const e = ctx.engine, A = ctx.audio;
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const t0 = p.t0 ?? shot.t0, tImpact = p.tImpact ?? t0 + 0.82;
    const salvo = exchange(t0);
    // the camera settles in over the pole; the globe reddens as the warheads land, then its lights go out
    const push = easeOutCubic(range(t, t0, t0 + 1.5));
    const view = { center: [960, lerp(380, 400, push)], radius: lerp(610, 660, push), lat: 64, lon: -60 + lt * 3, roll: 0 };
    const burn = smooth(range(t, tImpact, tImpact + 0.35));
    const dark = smooth(range(t, tImpact + 0.35, tImpact + 0.7));
    const sm = skyMaterial(e);
    setSky(sm.uniforms, { mode: 'light', band: 0.5, density: 1.0 }, ctx);
    e.pass(sm, e.rtScene);
    earthMaterial(e);
    setEarth(ctx, { mode: 'light', center: view.center, radius: view.radius, lat: view.lat, lon: view.lon, roll: view.roll,
      sun: [0.15, 0.9, -0.45], red: 0.75 * burn * (1 - 0.35 * dark), lightsGain: 3.0 * (1 - 0.9 * dark) });
    e.passOver(earthMaterial(e), e.rtScene);

    const c = K(ctx).begin(null);
    c.globalCompositeOperation = 'lighter';
    c.lineCap = 'round'; c.lineJoin = 'round';
    // tracks: a red trail with a white-hot head, the early-warning display's picture of an attack
    for (const m of salvo) {
      if (t < m.tl || t > m.ti + 0.6) continue;
      const fade = 1 - range(t, m.ti + 0.1, m.ti + 0.6);
      for (const [w, a] of [[9, 0.12], [3.5, 0.45], [1.4, 0.95]]) {
        c.strokeStyle = `rgba(255,${w < 2 ? 120 : 50},${w < 2 ? 90 : 40},${a * fade})`; c.lineWidth = w;
        track(c, view, m, t); c.stroke();
      }
      const head = t < m.ti ? track(c, view, m, t) : null;
      if (head && head[2]) {
        c.fillStyle = 'rgba(255,255,255,0.95)'; c.beginPath(); c.arc(head[0], head[1], 3.2 + A.kick(t) * 2, 0, Math.PI * 2); c.fill();
      }
    }
    // launch blooms at the sites
    for (const m of salvo) {
      const age = t - m.tl;
      if (age < 0 || age > 0.25) continue;
      const [x, y, v] = globeProject(view, ...m.from);
      if (!v) continue;
      const g = c.createRadialGradient(x, y, 0, x, y, 22);
      g.addColorStop(0, `rgba(255,220,160,${0.8 * (1 - age / 0.25)})`); g.addColorStop(1, 'rgba(255,80,40,0)');
      c.fillStyle = g; c.fillRect(x - 24, y - 24, 48, 48);
    }
    // detonations
    for (const m of salvo) {
      const age = t - m.ti;
      if (age < 0) continue;
      const [x, y, v] = globeProject(view, ...m.to);
      if (!v) continue;
      flash(c, x, y, age, 0.8 + 0.5 * hash1(m.k * 3.3));
    }
    c.globalCompositeOperation = 'source-over';
    // the early-warning HUD: tracks counted up, the time to impact run down (an ICBM flies about 30 minutes)
    font(c, 'JetBrainsMono', 26, 600);
    const inAir = salvo.filter((m) => t >= m.tl && t < m.ti).length, hit = salvo.filter((m) => t >= m.ti).length;
    const tag = (s, x, col, align = 'left') => {
      const w = c.measureText(s).width, x0 = align === 'right' ? x - w : x;
      c.fillStyle = css(INK.ink, 0.78); c.fillRect(x0 - 10, 44, w + 20, 37);
      c.fillStyle = col; c.fillText(s, x0, 71);
    };
    const eta = Math.max(0, 30 * 60 * (1 - range(t, t0 + 0.02, tImpact)));
    const mm = String(Math.floor(eta / 60)).padStart(2, '0'), ss = String(Math.floor(eta % 60)).padStart(2, '0');
    tag(`LAUNCH DETECTED  ·  ICBM TRACKS ${String(inAir + hit).padStart(2, '0')}`, 90, css(INK.red, 0.95));
    if (t < tImpact + 0.3) tag(`IMPACT IN ${mm}:${ss}`, 1830, css(INK.paper, 0.9), 'right');
    else tag(`NUCLEAR DETONATIONS ${hit}  ·  SIGNAL LOST`, 1830, css(INK.red, 0.95), 'right');
    K(ctx).end({ over: true });
  },
};
