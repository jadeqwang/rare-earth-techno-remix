// THE EDIT. Every shot is placed on the song's own clock: lyric word onsets (A.W) and the tracked,
// accelerating beat grid (bars below). Shots never overlap; transitions are cuts, flashes and impact frames.
import { INK, css, clamp, range, smooth, easeOutCubic, easeInOutCubic, lerp, pulse } from './util.js';
import { SELECT } from './selects.js';

const P = css(INK.paper), PALE = css(INK.pale), ORANGE = css(INK.orange), MINT = css(INK.mint),
  PINK = css(INK.pink), YELLOW = css(INK.yellow), KLEIN = css(INK.klein), INKC = css(INK.ink);

// Earth print look / ETZ print look / light look
const PRINT = { paper: 1, grain: 0.06, vignette: 0.25 };
const LIGHT = { bloom: 0.9, grain: 0.05, vignette: 0.35, bloomThreshold: 0.5 };
const LIGHT3D = { bloom: 0.55, grain: 0.05, vignette: 0.35, bloomThreshold: 0.72 };

export function buildTimeline(A) {
  const W = (i, j) => A.W(i, j), L = (i) => A.L(i);
  const bars = A.bars;
  const bar = (t) => bars.reduce((best, b) => (Math.abs(b - t) < Math.abs(best - t) ? b : best), bars[0]);
  // rotoscope shot helper: clip = shot id in SELECT (chosen take + measured lip-sync lag)
  const R = (clip, extra = {}) => {
    const s = SELECT[clip] || { start: 0, lag: 0 };
    return { clip, start: s.start, lag: s.lag || 0, mode: 'print', ...extra };
  };
  const skyL = (extra = {}) => ({ scene: 'sky', p: { mode: 'light', band: 1.0, density: 1.2, ...extra } });
  const skyP = (extra = {}) => ({ scene: 'sky', p: { mode: 'print', band: 0.9, horizon: 0.1, ...extra } });

  const S = [];
  const add = (s) => { S.push(s); return s; };

  // ================================================================ COLD OPEN + V1 (Earth, asking)
  add({ id: 'poster', t0: 0, t1: 5.70, scene: 'roto',
    p: (t) => R('sd01', { rect: [-0.04 * smooth(t / 5.7), -0.03 * smooth(t / 5.7), 1 + 0.08 * smooth(t / 5.7), 1 + 0.08 * smooth(t / 5.7)] }),
    look: (t) => ({ ...PRINT, fade: smooth(t / 0.6) }),
    type: (ty, t) => {
      // poster title, dissolving before the first word
      const a = 1 - range(t, 2.5, 3.05);
      if (a > 0) {
        ty.ctx.globalAlpha = a;
        ty.font('NotoSerifDisplay', 250, 900, 'extra-condensed');
        ty.plateText('RARE', 90, 400, P, css(INK.orange, 0.9), [7, 6], a);
        ty.plateText('EARTH', 90, 640, P, css(INK.orange, 0.9), [7, 6], a);
        ty.font('BlackHanSans', 46); ty.ctx.fillStyle = PALE; ty.ctx.fillText('희귀한 지구', 96, 720);
        ty.font('DelaGothicOne', 40); ty.ctx.fillText('レアアース', 96, 780);
        ty.ctx.globalAlpha = 1;
      }
      ty.hud('RX  1420.40575 MHz   ·   SUTRO / SF   ·   NIGHT 4,017', 90, 70, { alpha: 0.85 });
      ty.hud('LISTENING  ' + (Math.floor(t * 2) % 2 ? '●' : '○'), 1830, 70, { align: 'right', alpha: 0.85 });
      ty.stack(t, [0], { x: 92, y: 360, size: 220, lineH: 205, maxW: 1150, accent: PALE, plate: css(INK.orange, 0.9) });
    } });

  add({ id: 'yearning', t0: 5.70, t1: 8.86, scene: 'roto', p: R('sd02'), look: PRINT,
    type: (ty, t) => ty.stack(t, [1], { x: 90, y: 250, size: 118, lineH: 125, maxW: 900, accent: PALE }) });

  add({ id: 'searching', t0: 8.86, t1: 10.88, scene: 'array',
    p: { mode: 'print', choreo: 'sweep', cam: 'low' }, look: PRINT,
    type: (ty, t) => {
      ty.keyword(t, 'SEARCHING', W(2, 0), { size: 250, y: 330, plate: css(INK.orange, 0.9) });
      ty.keyword(t, 'FOR ME', W(2, 1), { size: 120, y: 470, stretch: 'normal' });
      ty.hud(`SCANNING  ${(1.4e9 + Math.floor((t - 8.86) * 3.1e8)).toLocaleString('en-US')}  CHANNELS`, 90, 1010);
    } });

  add({ id: 'listen', t0: 10.88, t1: 12.73, scene: 'roto', p: R('sd03'), look: PRINT,
    type: (ty, t) => ty.stack(t, [3], { x: 90, y: 300, size: 150, lineH: 150, maxW: 780, accent: PALE }) });

  add({ id: 'pullback', t0: 12.73, t1: 14.81, scene: 'roto', p: R('sd04'), look: PRINT,
    type: (ty, t) => {
      ty.keyword(t, 'A RARE EARTH', W(4, 0), { size: 200, y: 560, plate: css(INK.orange, 0.9) });
      ty.keyword(t, 'LOOKING FOR', W(4, 3), { size: 90, y: 690, stretch: 'normal' });
    } });

  add({ id: 'zoomout', t0: 14.81, t1: 18.04, scene: 'zoom', p: { from: 14.81, to: 18.04 }, look: PRINT,
    type: (ty, t) => {
      const k = range(t, 14.81, 17.2);
      ty.font('Archivo', 170, 900, 'expanded');
      const word = 'FRIEND';
      const sp = lerp(10, 90, easeOutCubic(k));
      let x = 960 - (ty.ctx.measureText(word).width + sp * (word.length - 1)) / 2;
      for (const ch of word) { ty.plateText(ch, x, 330, P, css(INK.orange, 0.85), [6, 5], 1 - range(t, 17.4, 18.0)); x += ty.ctx.measureText(ch).width + sp; }
    } });

  // ================================================================ V2 (Earth, the signal)
  add({ id: 'palebluedot', t0: 18.04, t1: 21.89, scene: 'dot', p: {}, look: { ...PRINT, paper: 0.3 },
    type: (ty, t) => {
      ty.subtitle(t, 5, { y: 960, size: 46, text: 'Lived my life on a', end: W(5, 5) - 0.1 });
      ty.keyword(t, 'PALE BLUE DOT', W(5, 5), { size: 150, y: 240, color: PALE, stretch: 'expanded' });
      ty.hud('VOYAGER 1  ·  14 FEB 1990  ·  6.4 × 10⁹ km', 90, 1010, { alpha: 0.7 });
      const c = ty.ctx, a = range(t, 18.3, 18.8) * (1 - range(t, 21.5, 21.89));
      if (a > 0) {
        c.globalAlpha = a; c.strokeStyle = PALE; c.lineWidth = 2.5;
        c.beginPath(); c.arc(1020, 560, 34 + 4 * Math.sin(t * 3), 0, Math.PI * 2); c.stroke();
        c.beginPath(); c.moveTo(1048, 536); c.lineTo(1150, 450); c.lineTo(1330, 450); c.stroke();
        ty.hud('YOU ARE HERE', 1160, 438, { size: 26, color: PALE });
        c.globalAlpha = 1;
      }
    } });

  add({ id: 'waterfall', t0: 21.89, t1: 23.17, scene: 'waterfall', p: { mode: 'print', signalAt: W(6, 1) }, look: PRINT,
    type: (ty, t) => {
      ty.keyword(t, 'SIGNAL', W(6, 1), { size: 260, y: 600, color: P, plate: css(INK.orange, 0.95) });
      ty.subtitle(t, 6, { y: 980, size: 44, text: 'Your signal here', end: 23.1 });
    } });

  add({ id: 'caught', t0: 23.17, t1: 24.79, scene: 'roto', p: R('sd05'), look: PRINT,
    type: (ty, t) => ty.subtitle(t, 6, { y: 990, size: 52, text: 'I think I’ve caught' }) });

  add({ id: 'wow', t0: 24.79, t1: 25.30, scene: 'wow', p: { circleAt: 24.85 }, look: { paper: 0.6, grain: 0.07 } });

  add({ id: 'blink', t0: 25.30, t1: 27.82, scene: 'roto', p: R('sd06'), look: PRINT,
    type: (ty, t) => {
      ty.keyword(t, 'BEATING', W(7, 1), { size: 170, y: 300, x: 480, t1: W(7, 2), kickAmt: 0.12 });
      ty.keyword(t, 'BLINKING', W(7, 2), { size: 170, y: 300, x: 1440, kickAmt: 0.12 });
    } });

  add({ id: 'star', t0: 27.82, t1: 28.64, scene: 'star', p: { mode: 'light' }, look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'STAR', W(7, 5), { size: 300, y: 900, color: P }) });

  add({ id: 'transit', t0: 28.64, t1: 30.98, scene: 'transit', p: { mode: 'print', t0: 28.64, t1: 30.98 }, look: PRINT,
    type: (ty, t) => {
      ty.subtitle(t, 8, { y: 150, size: 46, text: 'A planet’s transit', end: 30.9 });
      ty.keyword(t, 'TRANSIT', W(8, 2), { size: 180, y: 330, color: P, plate: css(INK.orange, 0.9) });
    } });

  add({ id: 'transit_eye', t0: 30.98, t1: 35.94, scene: 'roto', p: R('sd07'), look: PRINT,
    type: (ty, t) => ty.stack(t, [8], { x: 90, y: 160, size: 84, lineH: 92, maxW: 560, accent: PALE, fromScale: 1.3,
      filter: (w) => w.t >= 30.9 }) });

  add({ id: 'alone', t0: 35.94, t1: 39.95, scene: 'roto', p: R('sd08'), look: PRINT,
    type: (ty, t) => {
      ty.keyword(t, 'HOW COULD WE', W(9, 0), { size: 110, y: 200, stretch: 'normal' });
      const k = range(t, W(9, 4), 39.9);
      ty.font('Archivo', 210, 900, 'expanded');
      const word = 'ALONE?'; const sp = lerp(0, 60, easeOutCubic(k));
      let x = 960 - (ty.ctx.measureText(word).width + sp * (word.length - 1)) / 2;
      if (t >= W(9, 3)) for (const ch of word) { ty.plateText(ch, x, 400, P, css(INK.orange, 0.9), [7, 6]); x += ty.ctx.measureText(ch).width + sp; }
    } });

  // ================================================================ BUILD (the other world)
  add({ id: 'warp', t0: 39.95, t1: 43.94, scene: 'sky',
    p: (t) => ({ mode: 'light', band: 0.8, density: 1.4, warp: smooth(range(t, 39.95, 41.5)) * (1 - range(t, 43.2, 43.94)), zoom: 1 + range(t, 39.95, 43.94) * 0.6 }),
    look: LIGHT,
    type: (ty, t) => {
      const ly = Math.floor(217 * easeInOutCubic(range(t, 40.3, 43.5)));
      ty.hud(`DISTANCE  ${ly} LY`, 90, 1000, { size: 30 });
      ty.hud(`ONE-WAY LATENCY  ${ly} YEARS`, 1830, 1000, { size: 30, align: 'right' });
      ty.decode(t, 'ETZ-1715 b', 42.3, { size: 120, y: 560 });
    } });

  add({ id: 'planet', t0: 43.94, t1: 47.55, scene: 'planet', p: { mode: 'print' }, look: { ...PRINT, paperCol: INK.paper },
    type: (ty, t) => {
      ty.hud('ETZ-1715 b   ·   SUPER-EARTH   ·   1.7 R⊕   ·   RINGED', 90, 70);
      ty.hud('INHABITED', 1830, 70, { align: 'right', color: css(INK.pink) });
      ty.glyphLine('WE ARE LISTENING', 90, 1010, 30, css(INK.ink, 0.9));
    } });

  add({ id: 'theircity', t0: 47.55, t1: 49.36, scene: 'otherworld', p: { mode: 'print', view: 'city' }, look: PRINT });
  add({ id: 'theirfield', t0: 49.36, t1: 51.16, scene: 'petals', p: { mode: 'print', choreo: 'bloom' }, look: PRINT,
    type: (ty, t) => ty.decode(t, 'ARE YOU THERE?', 49.7, { size: 90, y: 200, color: css(INK.ink), latinColor: css(INK.ink), glyphColor: css(INK.ink) }) });
  add({ id: 'theirtower', t0: 51.16, t1: 52.96, scene: 'otherworld', p: { mode: 'print', view: 'tower' }, look: PRINT });

  // one-beat alternation into the drop
  const bt = A.beats.filter((b) => b > 52.9 && b < 54.8);
  const flip = ['array', 'petals', 'array', 'petals'];
  for (let i = 0; i < bt.length - 1; i++) {
    const sc = flip[i % flip.length];
    add({ id: `flip${i}`, t0: i === 0 ? 52.96 : bt[i], t1: i === bt.length - 2 ? 54.76 : bt[i + 1], scene: sc,
      p: { mode: 'light', choreo: 'snap', cam: i % 2 ? 'high' : 'low' },
      look: (t) => ({ ...LIGHT3D, flash: pulse(t - bt[i], 0.04) * 0.6 }) });
  }

  // ================================================================ DROP 1 / V3 (the filter, keep looking)
  add({ id: 'title', t0: 54.76, t1: 55.45, scene: 'galaxy', p: { mode: 'light', view: 'title' },
    look: (t) => ({ ...LIGHT, invert: t < 54.84 ? 1 : 0, flash: pulse(t - 54.76, 0.06) * 0.5 }),
    type: (ty, t) => { ty.title(t, 54.76, { t1: 55.45 }); ty.subtitle(t, 10, { y: 1010, size: 40 }); } });

  add({ id: 'launch', t0: 55.45, t1: 56.87, scene: 'roto', p: R('se02', { mode: 'light', glow: INK.orange, glow2: INK.yellow }), look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'LAUNCH', W(10, 2), { size: 280, y: 980, color: P }) });

  add({ id: 'selfdestruct', t0: 56.87, t1: 57.59, scene: 'earth', p: { mode: 'light', red: 1 },
    look: (t) => ({ ...LIGHT, ca: 6, shakeX: Math.sin(t * 90) * 6, shakeY: Math.cos(t * 77) * 4 }),
    type: (ty, t) => ty.keyword(t, 'SELF-DESTRUCT', W(10, 4), { size: 200, y: 580, color: css(INK.red), kickAmt: 0.2 }) });

  add({ id: 'drake', t0: 57.59, t1: 61.03, scene: 'drake', p: {}, look: { paper: 0.9, grain: 0.07 },
    type: (ty, t) => {
      ty.terminal(t, [
        { t: W(11, 0), s: '> WEAPONS', color: css(INK.red) },
        { t: W(11, 1), s: '> WARS', color: css(INK.red) },
        { t: W(11, 2), s: '> AND NOW WE’RE', color: INKC },
      ], { x: 90, y: 860, size: 48, color: INKC });
    } });

  add({ id: 'blank', t0: 61.03, t1: 61.45, scene: 'solid', p: { color: [0, 0, 0] }, look: { grain: 0.02, vignette: 0 },
    type: (ty, t) => ty.censor(t, 61.03, 61.45) });

  add({ id: 'keep_array', t0: 61.45, t1: 62.42, scene: 'array', p: { mode: 'light', choreo: 'snapup', t0: 61.45 },
    look: (t) => ({ ...LIGHT3D, invert: t < 61.53 ? 1 : 0, flash: pulse(t - 61.45, 0.05) }),
    type: (ty, t) => ty.keyword(t, 'KEEP ON', W(12, 0), { size: 230, y: 330, color: P }) });

  add({ id: 'keep_yagi', t0: 62.42, t1: 63.23, scene: 'roto', p: R('sd09', { mode: 'light', bg: skyL() }), look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'LOOKING', W(12, 2), { size: 260, y: 1000, color: P }) });

  add({ id: 'faith', t0: 63.23, t1: 64.89, scene: 'petals', p: { mode: 'light', choreo: 'bloom' }, look: LIGHT3D,
    type: (ty, t) => ty.keyword(t, 'KEEP THE FAITH', W(12, 3), { size: 170, y: 560, color: P }) });

  add({ id: 'funding', t0: 64.89, t1: 67.17, scene: 'brutal', p: { view: 'funding', t0: 64.89 }, look: { paper: 0.8, grain: 0.07 } });

  add({ id: 'planetwaits', t0: 67.17, t1: 69.53, scene: 'roto', p: R('se03', { mode: 'print' }), look: PRINT,
    type: (ty, t) => { ty.keyword(t, 'OUR PLANET', W(13, 3), { size: 150, y: 250, color: P }); ty.keyword(t, 'WAITS', W(13, 5), { size: 230, y: 470, color: PALE }); } });

  add({ id: 'transmission', t0: 69.53, t1: 71.14, scene: 'waterfall', p: { mode: 'light', signalAt: 69.6 }, look: LIGHT,
    type: (ty, t) => ty.decode(t, 'FOR YOUR TRANSMISSION', W(14, 0), { size: 100, y: 560, dur: 0.6 }) });

  add({ id: 'vision', t0: 71.14, t1: 75.36, scene: 'roto', p: R('sd10', { mode: 'light', bg: { scene: 'galaxy', p: { mode: 'light', view: 'bg' } } }),
    look: (t) => ({ ...LIGHT, flash: pulse(t - W(15, 4), 0.07) * 0.7 }),
    type: (ty, t) => {
      ty.stack(t, [15], { x: 80, y: 250, size: 130, lineH: 135, maxW: 640, accent: YELLOW, plate: css(INK.mint, 0.8) });
    } });

  // ================================================================ DROP 2a / V4 (call and response)
  add({ id: 'care2', t0: 75.36, t1: 77.66, scene: 'roto', p: R('sd11', { mode: 'light', bg: skyL() }), look: LIGHT,
    type: (ty, t) => ty.stack(t, [16], { x: 80, y: 320, size: 190, lineH: 185, maxW: 900, accent: YELLOW, plate: css(INK.mint, 0.8) }) });

  add({ id: 'yearning2', t0: 77.66, t1: 81.00, scene: 'otherworld', p: { mode: 'light', view: 'vista' }, look: LIGHT,
    type: (ty, t) => {
      ty.decode(t, 'YOU’RE YEARNING TO SEE', W(17, 0), { size: 80, y: 200 });
      ty.decode(t, 'THE LIFE OUT THERE', W(17, 4), { size: 110, y: 330 });
    } });

  add({ id: 'searching2', t0: 81.00, t1: 82.20, scene: 'split', p: { left: { scene: 'array', p: { mode: 'light', choreo: 'sweep' } }, right: { scene: 'petals', p: { mode: 'light', choreo: 'sweep' } } },
    look: LIGHT3D, type: (ty, t) => ty.keyword(t, 'SEARCHING FOR ME', W(18, 0), { size: 130, y: 1000, color: P }) });

  add({ id: 'listen2', t0: 82.20, t1: 84.60, scene: 'roto', p: R('sd12', { mode: 'light', bg: skyL() }), look: LIGHT,
    type: (ty, t) => ty.stack(t, [19], { x: 1100, y: 330, size: 140, lineH: 140, maxW: 760, accent: YELLOW, plate: css(INK.mint, 0.8) }) });

  add({ id: 'journey', t0: 84.60, t1: 90.47, scene: 'journey', p: { t0: 84.60, t1: 90.47 }, look: LIGHT,
    type: (ty, t) => {
      ty.keyword(t, 'A RARE EARTH', W(20, 0), { size: 170, y: 230, color: P, t1: W(20, 3) });
      if (t < 88.4) ty.keyword(t, 'LOOKING FOR A FRIEND', W(20, 3), { size: 110, y: 230, color: P });
      else ty.decode(t, 'FRIEND', 88.4, { size: 220, y: 600, dur: 1.2, glyphColor: MINT, latinColor: P });
    } });

  // ================================================================ DROP 2b / V5 (arrival)
  add({ id: 'dot2', t0: 90.47, t1: 93.59, scene: 'otherworld', p: { mode: 'light', view: 'night', sol: 1 }, look: LIGHT,
    type: (ty, t) => {
      ty.decode(t, 'LIVED MY LIFE ON A', W(21, 0), { size: 70, y: 180 });
      ty.decode(t, 'PALE BLUE DOT', W(21, 5), { size: 150, y: 330, latinColor: PALE });
    } });

  add({ id: 'caught2', t0: 93.59, t1: 97.45, scene: 'roto', p: R('sd13', { mode: 'print', inkA: INK.klein, inkC: INK.mint }), look: PRINT,
    type: (ty, t) => ty.stack(t, [22], { x: 90, y: 230, size: 104, lineH: 112, maxW: 700, accent: MINT }) });

  add({ id: 'blinkearth', t0: 97.45, t1: 98.80, scene: 'earth', p: { mode: 'light', blink: 1, view: 'night' }, look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'BEATING', W(23, 1), { size: 200, y: 950, color: P, kickAmt: 0.15 }) });
  add({ id: 'blinketz', t0: 98.80, t1: 99.76, scene: 'planet', p: { mode: 'light', blink: 1 }, look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'BLINKING', W(23, 2), { size: 200, y: 950, color: P, kickAmt: 0.15 }) });
  add({ id: 'blinkdance', t0: 99.76, t1: 100.75, scene: 'roto', p: R('sd14', { mode: 'light', bg: skyL({ twinkle: 1 }) }), look: LIGHT,
    type: (ty, t) => ty.keyword(t, 'OF A STAR', W(23, 4), { size: 170, y: 250, color: YELLOW }) });

  add({ id: 'mutual', t0: 100.75, t1: 104.34, scene: 'mutual', p: { t0: 100.75, t1: 104.34 }, look: LIGHT,
    type: (ty, t) => ty.subtitle(t, 24, { y: 1010, size: 46, color: P, end: 104.3 }) });

  add({ id: 'own', t0: 104.34, t1: 107.79, scene: 'roto', p: R('sd15'), look: PRINT,
    type: (ty, t) => ty.stack(t, [24], { x: 1180, y: 250, size: 110, lineH: 118, maxW: 680, accent: PALE, filter: (w) => w.t >= 104.3 }) });

  add({ id: 'alone2', t0: 107.79, t1: 112.02, scene: 'split',
    p: { left: { scene: 'roto', p: R('sd16', { mode: 'light' }) }, right: { scene: 'otherworld', p: { mode: 'light', view: 'tower' } } },
    look: (t) => ({ ...LIGHT, flash: range(t, 111.3, 112.02) * 0.9 }),
    type: (ty, t) => {
      ty.keyword(t, 'HOW COULD WE BE ALONE?', W(25, 0), { size: 100, x: 480, y: 980, color: P, stretch: 'normal' });
      if (t > W(25, 0)) ty.glyphLine('HOW COULD WE BE ALONE', 1010, 990, 38, MINT);
    } });

  // ================================================================ FINAL DROP (contact) — instrumental
  const fb = A.beats.filter((b) => b >= 112.0 && b < 123.5);
  add({ id: 'contact', t0: 112.02, t1: 113.80, scene: 'roto', p: R('sd17', { mode: 'light', bg: { scene: 'galaxy', p: { mode: 'light', view: 'bg' } } }),
    look: (t) => ({ ...LIGHT, invert: t < 112.1 ? 1 : 0, flash: pulse(t - 112.02, 0.08) }) });
  add({ id: 'dance_split', t0: 113.80, t1: 115.58, scene: 'split', p: { left: { scene: 'array', p: { mode: 'light', choreo: 'dance' } }, right: { scene: 'petals', p: { mode: 'light', choreo: 'dance' } } }, look: LIGHT3D });
  add({ id: 'lightsticks', t0: 115.58, t1: 117.35, scene: 'earth', p: { mode: 'light', blink: 2, view: 'night' }, look: LIGHT });
  add({ id: 'galaxyweb', t0: 117.35, t1: 120.90, scene: 'galaxy', p: { mode: 'light', view: 'web', t0: 117.35, t1: 120.90 }, look: LIGHT });
  add({ id: 'stillhere', t0: 120.90, t1: 123.40, scene: 'roto', p: R('sd18', { mode: 'light', bg: { scene: 'galaxy', p: { mode: 'light', view: 'bg' } } }),
    look: LIGHT, type: (ty, t) => ty.decode(t, 'STILL HERE.', 121.0, { size: 230, y: 340, dur: 1.0, latinColor: YELLOW }) });

  // ================================================================ OUTRO
  add({ id: 'end', t0: 123.40, t1: 128.2, scene: 'endcard', p: {}, look: (t) => ({ paper: 1, grain: 0.05, fade: 1 - range(t, 127.2, 127.96) }) });

  // sanity: contiguous, non-overlapping
  S.sort((a, b) => a.t0 - b.t0);
  for (let i = 1; i < S.length; i++) if (Math.abs(S[i].t0 - S[i - 1].t1) > 1e-6) console.warn('gap/overlap', S[i - 1].id, S[i - 1].t1, S[i].id, S[i].t0);
  return S;
}
