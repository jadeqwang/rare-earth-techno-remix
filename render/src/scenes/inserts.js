// Typographic / diagram inserts and compositors: Drake equation, funding, the journey, split screens, end card.
import * as THREE from 'three';
import { C2D, font } from '../c2d.js';
import { INK, css, clamp, range, smooth, easeOutCubic, easeOutBack, easeInOutCubic, lerp, hash1, pulse } from '../util.js';
import { skyMaterial, setSky } from './sky.js';
import { earthMaterial, setEarth } from './earth.js';
import { drawGlyph } from '../type.js';
import { SCENES } from './index.js';

let c2d = null;
const K = (ctx) => (c2d ||= new C2D(ctx.engine));

// ------------------------------------------------------------------ DRAKE: L = ?
export const drake = {
  async draw(ctx, shot, t, lt) {
    const A = ctx.audio;
    const c = K(ctx).begin(css(INK.paper));
    const terms = ['N', '=', 'R*', '·', 'fₚ', '·', 'nₑ', '·', 'fₗ', '·', 'fᵢ', '·', 'f꜀', '·', 'L'];
    const b = A.beat(t);
    // fit the whole equation (L included) to the frame
    let fs = 196;
    font(c, 'NotoSerifDisplay', fs, 700, 'semi-condensed', 'italic');
    let widths = terms.map((s) => c.measureText(s + ' ').width);
    const tw0 = widths.reduce((a, b2) => a + b2, 0);
    if (tw0 > 1700) { fs = Math.floor(fs * 1700 / tw0); font(c, 'NotoSerifDisplay', fs, 700, 'semi-condensed', 'italic'); widths = terms.map((s) => c.measureText(s + ' ').width); }
    let x = 960 - widths.reduce((a, b2) => a + b2, 0) / 2;
    const shown = Math.min(terms.length, 3 + Math.floor((t - shot.t0) / (b.period * 0.5)));
    for (let i = 0; i < terms.length; i++) {
      if (i < shown) {
        const isL = i === terms.length - 1;
        c.fillStyle = isL ? css(INK.red) : css(INK.ink);
        c.fillText(terms[i], x, 560);
        if (isL) {
          // L = the lifetime of a transmitting civilization; circle it, flicker on the snare
          const f = 0.6 + 0.4 * (A.snare(t) > 0.3 ? 1 : 0);
          c.strokeStyle = css(INK.red, f); c.lineWidth = 7;
          const wl = c.measureText('L').width;
          c.beginPath(); c.ellipse(x + wl * 0.5, 560 - fs * 0.33, fs * 0.55, fs * 0.66, -0.1, 0, Math.PI * 2 * clamp((t - shot.t0) / 0.8)); c.stroke();
          font(c, 'JetBrainsMono', 30, 700);
          c.fillStyle = css(INK.red); c.fillText('L = ?', x - 20, 560 + fs * 0.62);
          font(c, 'NotoSerifDisplay', fs, 700, 'semi-condensed', 'italic');
        }
      }
      x += widths[i];
    }
    font(c, 'JetBrainsMono', 24, 500);
    c.fillStyle = css(INK.ink, 0.8);
    c.fillText('L — how long a civilization keeps transmitting before it goes quiet', 480, 790);
    // hard red flicker on "wars"
    const wars = A.W(11, 1);
    if (t > wars && t < wars + 0.5 && Math.floor((t - wars) * 16) % 2 === 0) { c.fillStyle = css(INK.red, 0.85); c.fillRect(0, 0, 1920, 1080); }
    K(ctx).end({ halftone: 0.2 });
  },
};

// ------------------------------------------------------------------ FUNDING (internet brutalism)
export const brutal = {
  async draw(ctx, shot, t, lt) {
    const A = ctx.audio;
    const c = K(ctx).begin(css(INK.paper));
    const t0 = shot.t0;
    // headline slams, word by word
    font(c, 'Anton', 250, 400);
    const words = ['KEEP', 'UP', 'FUNDING'];
    const wt = [A.W(13, 0), A.W(13, 1), A.W(13, 2)];
    let x = 90;
    for (let i = 0; i < 3; i++) {
      if (t < wt[i]) break;
      const k = easeOutBack(clamp((t - wt[i]) / 0.14), 2);
      c.save(); c.translate(x, 330); c.scale(lerp(1.3, 1, k), lerp(1.3, 1, k));
      c.fillStyle = i === 2 ? css(INK.klein) : css(INK.ink); c.fillText(words[i], 0, 0); c.restore();
      x += c.measureText(words[i] + ' ').width;
    }
    // Win98-style window with a progress bar
    const wx = 140, wy = 470, ww = 1060, wh = 330;
    c.fillStyle = '#c0c0c0'; c.fillRect(wx, wy, ww, wh);
    c.fillStyle = '#000080'; c.fillRect(wx + 4, wy + 4, ww - 8, 40);
    font(c, 'JetBrainsMono', 22, 700); c.fillStyle = '#ffffff'; c.fillText('SETI_ARRAY_RESTART.EXE', wx + 16, wy + 32);
    c.fillStyle = '#c0c0c0'; c.fillRect(wx + ww - 40, wy + 10, 28, 28); c.fillStyle = '#000'; c.fillText('×', wx + ww - 33, wy + 32);
    font(c, 'JetBrainsMono', 24, 500); c.fillStyle = '#000';
    c.fillText('Allen Telescope Array — hibernating since APR 2011', wx + 24, wy + 90);
    c.fillText('Receivers: 42 · Band: 0.5–11.2 GHz · Target: everything', wx + 24, wy + 128);
    const prog = clamp((t - A.W(13, 2)) / 1.2);
    const bx = wx + 24, by = wy + 170, bw = ww - 48, bh = 54;
    c.fillStyle = '#fff'; c.fillRect(bx, by, bw, bh);
    c.strokeStyle = '#808080'; c.lineWidth = 3; c.strokeRect(bx, by, bw, bh);
    const blocks = Math.floor(prog * 34);
    c.fillStyle = '#000080';
    for (let i = 0; i < blocks; i++) c.fillRect(bx + 6 + i * ((bw - 12) / 34), by + 6, (bw - 12) / 34 - 4, bh - 12);
    c.fillStyle = '#000'; c.fillText(`FUNDED  ${Math.floor(prog * 100)}%`, bx, by + bh + 44);
    // stamp at "planet"
    const st = A.W(13, 4);
    if (t > st) {
      const k = easeOutBack(clamp((t - st) / 0.18), 3);
      c.save(); c.translate(1500, 690); c.rotate(-0.18); c.scale(lerp(2.2, 1, k), lerp(2.2, 1, k));
      c.strokeStyle = css(INK.red); c.lineWidth = 12; c.strokeRect(-230, -95, 460, 170);
      font(c, 'Anton', 130, 400); c.fillStyle = css(INK.red); c.fillText('FUNDED', -200, 45); c.restore();
    }
    // margin notes
    font(c, 'JetBrainsMono', 20, 500); c.fillStyle = css(INK.ink, 0.75);
    c.fillText('BACK ONLINE · DEC 2011 · crowdfunded by thousands of strangers', 140, 1000);
    c.fillText('▌▌▌ ▌ ▌▌ ▌▌▌▌ ▌ ▌▌▌ ▌▌ ▌', 1500, 1000);
    K(ctx).end({ halftone: 0.15 });
  },
};

// ------------------------------------------------------------------ JOURNEY: the transmission crosses the gap
export const journey = {
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const e = ctx.engine;
    const k = clamp((t - p.t0) / (p.t1 - p.t0));
    const sm = skyMaterial(e);
    const warp = smooth(range(k, 0.12, 0.3)) * (1 - smooth(range(k, 0.72, 0.86)));
    setSky(sm.uniforms, { mode: 'light', band: 0.9, density: 1.5, warp, warpCenter: [1500, 540], zoom: 1 + k * 0.8, spin: k * 0.2 }, ctx);
    e.pass(sm, e.rtScene);
    // Earth recedes at the start
    if (k < 0.3) {
      const em = earthMaterial(e);
      setEarth(ctx, { mode: 'light', center: [lerp(420, -200, easeInOutCubic(range(k, 0, 0.3))), 560], radius: lerp(260, 90, range(k, 0, 0.3)), lat: 20, lon: -110 + lt * 8, sun: [0.8, 0.3, 0.5] });
      e.passOver(em, e.rtScene);
    }
    // ETZ-1715 b arrives at the end
    if (k > 0.72) {
      const pm = SCENES.planet;
      const sub = { ...shot, p: { mode: 'light', noSky: true, center: [lerp(2300, 1300, easeOutCubic(range(k, 0.72, 1))), 540], radius: lerp(60, 230, range(k, 0.72, 1)), zoomRate: 0 } };
      await pm.draw(ctx, sub, t, lt);
    }
    // the beam + counters (2D, over)
    const c = K(ctx).begin(null);
    const bx0 = k < 0.3 ? lerp(420, -200, easeInOutCubic(range(k, 0, 0.3))) : -200;
    const head = lerp(460, 2100, easeInOutCubic(range(k, 0.02, 0.9)));
    const grad = c.createLinearGradient(bx0, 0, head, 0);
    grad.addColorStop(0, 'rgba(255,225,77,0.0)'); grad.addColorStop(0.7, 'rgba(255,225,77,0.55)'); grad.addColorStop(1, 'rgba(255,245,200,1)');
    c.strokeStyle = grad; c.lineWidth = 5 + ctx.audio.kick(t) * 8; c.beginPath(); c.moveTo(bx0, 560); c.lineTo(head, 560); c.stroke();
    c.fillStyle = 'rgba(255,245,200,1)'; c.beginPath(); c.arc(head, 560, 9 + ctx.audio.kick(t) * 8, 0, 7); c.fill();
    font(c, 'JetBrainsMono', 28, 600); c.fillStyle = css(INK.paper, 0.9);
    const ly = Math.floor(217 * easeInOutCubic(range(k, 0.05, 0.92)));
    c.fillText(`TRANSMISSION IN FLIGHT   ${String(ly).padStart(3, '0')} / 217 LY`, 90, 1000);
    c.fillText(`LAUNCHED  2026   ·   ARRIVES  ${2026 + ly}`, 1180, 1000);
    K(ctx).end({ over: true });
  },
};

// ------------------------------------------------------------------ SPLIT: two worlds side by side
let splitMat = null;
// CONTACT: both signals meet halfway. Earth's beam from the left limb, theirs from the right, and a flare
// where they touch that blooms on every kick (the anime beam-clash, as a handshake).
export const clash = {
  async draw(ctx, shot, t, lt) {
    const e = ctx.engine, A = ctx.audio;
    const k = clamp(lt / Math.max(0.01, shot.t1 - shot.t0));
    await SCENES.burst.draw(ctx, { ...shot, p: { stars: true, c1: INK.yellow, c2: INK.pale, center: [960, 540], lines: 1.2 } }, t, lt);
    const em = earthMaterial(e);
    setEarth(ctx, { mode: 'light', center: [-330 + 40 * k, 540], radius: 760, lat: 18, lon: -95 + lt * 6, sun: [-0.2, 0.25, -1.0], roll: 0.05 });
    e.passOver(em, e.rtScene);
    await SCENES.planet.draw(ctx, { ...shot, p: { mode: 'light', noSky: true, center: [2250 - 40 * k, 540], radius: 760, zoomRate: 0, blink: 1, infra: 0, spin0: 2.0 } }, t, lt);
    const c = K(ctx).begin(null);
    c.globalCompositeOperation = 'lighter';
    const kick = A.kick(t, 0.12);
    const y = 540, xe = 430 + 40 * k, xz = 1490 - 40 * k;
    const reach = easeOutCubic(clamp(lt / 0.16));
    const beam = (x0, x1, rgb) => {
      c.lineCap = 'round';
      for (const [w, a] of [[54 + kick * 44, 0.10], [20 + kick * 16, 0.30], [6 + kick * 5, 0.95]]) {
        c.strokeStyle = `rgba(${rgb},${a})`; c.lineWidth = w;
        c.beginPath(); c.moveTo(x0, y); c.lineTo(x1, y); c.stroke();
      }
    };
    beam(xe, lerp(xe, 960, reach), '156,203,255');
    beam(xz, lerp(xz, 960, reach), '255,72,176');
    if (reach >= 1) {
      const R = 70 + kick * 150;
      const g = c.createRadialGradient(960, y, 0, 960, y, R * 2.2);
      g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.18, 'rgba(255,240,170,0.95)');
      g.addColorStop(0.5, 'rgba(255,225,77,0.35)'); g.addColorStop(1, 'rgba(255,225,77,0)');
      c.fillStyle = g; c.fillRect(960 - R * 2.2, y - R * 2.2, R * 4.4, R * 4.4);
      // anamorphic streaks
      c.save(); c.translate(960, y);
      c.fillStyle = `rgba(255,236,150,${0.55 + 0.4 * kick})`; c.beginPath(); c.ellipse(0, 0, 700 + kick * 520, 3 + kick * 3, 0, 0, 7); c.fill();
      c.fillStyle = `rgba(255,255,255,${0.4 + 0.4 * kick})`; c.beginPath(); c.ellipse(0, 0, 4 + kick * 3, 180 + kick * 160, 0, 0, 7); c.fill();
      c.restore();
    }
    c.globalCompositeOperation = 'source-over';
    font(c, 'JetBrainsMono', 26, 600); c.fillStyle = css(INK.paper, 0.9);
    c.fillText('SOL III', 90, 1000);
    const lab = 'ETZ-1715 b'; c.fillText(lab, 1830 - c.measureText(lab).width, 1000);
    const mid = 'SIGNAL LOCK  ·  BOTH WAYS'; c.fillStyle = css(INK.yellow, 0.95); c.fillText(mid, 960 - c.measureText(mid).width / 2, 1000);
    K(ctx).end({ over: true });
  },
};

export const split = {
  init(ctx) {
    splitMat = ctx.engine.shader(/* glsl */`
      uniform sampler2D tA; uniform sampler2D tB; uniform float gap; uniform vec3 lineC; uniform float offA; uniform float offB; uniform float kick;
      void main(){
        float x = vUv.x;
        vec3 c = x < .5 ? texture(tA, vec2(x + offA, vUv.y)).rgb : texture(tB, vec2(x - offB, vUv.y)).rgb;
        float l = exp(-abs(x - .5) * 900.) * (1. + kick * 2.);
        c += lineC * l;
        fragColor = vec4(c, 1.);
      }`, { tA: { value: null }, tB: { value: null }, gap: { value: 0 }, lineC: { value: new THREE.Color(...INK.yellow) }, offA: { value: 0.25 }, offB: { value: 0.25 }, kick: { value: 0 } });
  },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const e = ctx.engine;
    await SCENES[p.left.scene].draw(ctx, { ...shot, p: p.left.p, scene: p.left.scene }, t, lt);
    e.renderer.setRenderTarget(e.rtTmp); e.renderer.clear();
    copy(e, e.rtScene, e.rtTmp);
    await SCENES[p.right.scene].draw(ctx, { ...shot, p: p.right.p, scene: p.right.scene }, t, lt);
    copy(e, e.rtScene, e.rtTmp2);
    splitMat.uniforms.tA.value = e.rtTmp.texture; splitMat.uniforms.tB.value = e.rtTmp2.texture;
    splitMat.uniforms.offA.value = p.offA ?? 0.25; splitMat.uniforms.offB.value = p.offB ?? 0.25;
    splitMat.uniforms.kick.value = ctx.audio.kick(t);
    e.pass(splitMat, e.rtScene);
  },
};
let copyMat = null;
function copy(e, from, to) {
  if (!copyMat) copyMat = e.shader(`uniform sampler2D t; void main(){ fragColor = texture(t, vUv); }`, { t: { value: null } });
  copyMat.uniforms.t.value = from.texture;
  e.pass(copyMat, to);
}

// ------------------------------------------------------------------ END CARD
export const endcard = {
  async draw(ctx, shot, t, lt) {
    const A = ctx.audio;
    const c = K(ctx).begin(css(INK.paper));
    const k = easeOutCubic(clamp(lt / 1.2));
    const link = smooth(range(lt, 0.4, 1.6));
    const x1 = 760, x2 = 1160, y = 470;
    // the thin line between them
    c.strokeStyle = css(INK.ink, 0.7); c.lineWidth = 2;
    c.beginPath(); c.moveTo(x1, y); c.lineTo(lerp(x1, x2, link), y); c.stroke();
    // their reply crosses the line and lands on Sol exactly when "Still here." is heard (sound design, 128.02 s)
    const arrive = 128.02;
    const blink = t > arrive && t < arrive + 0.35 ? 1.9 : 1;
    c.fillStyle = css(INK.pale); c.beginPath(); c.arc(x1, y, 16 * k * blink, 0, 7); c.fill();
    c.fillStyle = css(INK.pink); c.beginPath(); c.arc(x2, y, 16 * k, 0, 7); c.fill();
    if (t > arrive) {
      const rr = 16 + (t - arrive) * 160, ra = Math.max(0, 1 - (t - arrive) / 0.9);
      c.strokeStyle = css(INK.pale, ra); c.lineWidth = 3; c.beginPath(); c.arc(x1, y, rr, 0, 7); c.stroke();
    }
    font(c, 'JetBrainsMono', 20, 600); c.fillStyle = css(INK.ink, 0.8);
    c.fillText('SOL III', x1 - 40, y + 60); c.fillText('ETZ-1715 b', x2 - 60, y + 60);
    if (t > arrive + 0.1) { c.fillStyle = css(INK.orange, smooth(range(t, arrive + 0.1, arrive + 0.4))); c.fillText('RX  STILL HERE.', x1 - 40, y + 92); }
    // the reply in flight: one bright pulse crossing from their world to ours
    const ph = range(t, 126.3, arrive);
    if (ph > 0 && ph < 1) {
      const px = lerp(x2, x1, easeInOutCubic(ph));
      c.fillStyle = css(INK.orange, 0.95);
      c.beginPath(); c.arc(px, y, 7, 0, 7); c.fill();
    }
    font(c, 'NotoSerifDisplay', 190, 900, 'extra-condensed');
    const s = 'RARE EARTH'; const w = c.measureText(s).width;
    c.fillStyle = css(INK.ink, smooth(range(lt, 0.8, 1.6))); c.fillText(s, 960 - w / 2, 760);
    const a2 = smooth(range(lt, 1.2, 2.0));
    const zh = '稀有地球', ru = 'Уникальная Земля';
    font(c, 'NotoSansSC', 36, 900); const wz = c.measureText(zh).width;
    font(c, 'Unbounded', 26, 800); const wr = c.measureText(ru).width;
    const x0 = 960 - (wz + 40 + wr) / 2;
    font(c, 'NotoSansSC', 36, 900); c.fillStyle = css(INK.klein, a2); c.fillText(zh, x0, 832);
    font(c, 'Unbounded', 26, 800); c.fillStyle = css(INK.pink, a2); c.fillText(ru, x0 + wz + 40, 830);
    font(c, 'JetBrainsMono', 20, 500); c.fillStyle = css(INK.ink, 0.75 * smooth(range(lt, 1.4, 2.2)));
    const cr = 'written in 2011 for a SETI event   ·   video drawn in javascript   ·   keep looking';
    c.fillText(cr, 960 - c.measureText(cr).width / 2, 900);
    K(ctx).end({ halftone: 0.1 });
  },
};
