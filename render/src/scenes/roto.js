// Rotoscoped base clip, redrawn from guide maps, optionally over a procedural background scene.
import * as THREE from 'three';
import { makeRotoMaterial, getTex, clipMeta, frameIndex } from '../roto.js';
import { INK } from '../util.js';
import { SCENES } from './index.js';

let mat = null;

export const roto = {
  async init(ctx) { mat = makeRotoMaterial(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const e = ctx.engine;
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : shot.p;
    let meta;
    try { meta = await clipMeta(p.clip); } catch (err) {
      // clip not generated / selected yet: placeholder so the edit still renders
      return SCENES.sky.draw(ctx, { ...shot, p: { mode: 'light', band: 0.4, density: 0.5 } }, t, lt);
    }
    // background first (keyed clips)
    if (p.bg) {
      const bgShot = { ...shot, p: p.bg.p, scene: p.bg.scene };
      await SCENES[p.bg.scene].draw(ctx, bgShot, t, lt);
    }
    const clipT = (p.clipTime !== undefined ? p.clipTime : (t - p.start)) + (p.lag || 0);
    const fi = frameIndex(meta, clipT, p.twos !== false);
    const pad = String(fi).padStart(4, '0');
    const [g, c] = await Promise.all([getTex(`/work/guides/${p.clip}/g_${pad}.png`), getTex(`/work/guides/${p.clip}/c_${pad}.jpg`)]);
    const u = mat.uniforms;
    u.tGuide.value = g; u.tColor.value = c;
    u.time.value = t; u.kick.value = ctx.audio.kick(t);
    const mode = p.mode || 'print';
    u.mode.value = mode === 'print' ? 0 : mode === 'light' ? 1 : 2;
    const col = (k, v) => u[k].value.setRGB(...v);
    col('inkA', p.inkA ?? INK.klein); col('inkB', p.inkB ?? INK.orange); col('inkC', p.inkC ?? INK.pale);
    col('inkLine', p.inkLine ?? INK.ink);
    col('paperC', p.paper ?? (mode === 'print' ? INK.paper : [0.015, 0.016, 0.03]));
    col('glowCol', p.glow ?? INK.mint); col('glowCol2', p.glow2 ?? INK.yellow);
    u.cell.value = p.cell ?? 6.5;
    u.boil.value = p.boil ?? 1.2;
    u.drawSeed.value = fi * 0.37 + (p.seed || 0);
    const r = p.rect ?? [0, 0, 1, 1];
    u.frameRect.value.set(...r);
    const keyed = meta.key === 'green' || p.keyed;
    u.bgKeep.value = keyed && p.bg ? 0 : 1;
    u.alphaOut.value = keyed && p.bg ? 1 : 0;
    u.lineGain.value = p.lineGain ?? 1.3;
    u.toneGamma.value = p.toneGamma ?? 1.0;
    if (keyed && p.bg) e.passOver(mat, e.rtScene); else e.pass(mat, e.rtScene);
  },
};
