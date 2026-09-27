// BURST: drop backgrounds for the keyed performance shots — anime speed lines + signal rings on every kick.
import * as THREE from 'three';
import { INK } from '../util.js';
import { skyMaterial, setSky } from './sky.js';

let mat = null;
export const burst = {
  init(ctx) {
    mat = ctx.engine.shader(/* glsl */`
      uniform vec2 res; uniform float S; uniform float time; uniform float kick; uniform float barPh; uniform float sinceKick;
      uniform vec3 c1; uniform vec3 c2; uniform vec2 center; uniform float lines; uniform float rings;
      void main(){
        vec2 px = vUv * res / S; vec2 d = px - center; float r = length(d); float a = atan(d.y, d.x);
        // speed lines: thin radial wedges, re-seeded every beat, rotating slowly with the bar
        float n = 90.;
        float id = floor((a + 3.14159 + barPh * .25) / 6.28318 * n);
        float h = hash12(vec2(id, floor(time * 4.)));
        float w = fract((a + 3.14159 + barPh * .25) / 6.28318 * n) - .5;
        float sl = step(.62, h) * (1. - smoothstep(.0, .08 + .12 * h, abs(w))) * smoothstep(180., 520., r);
        // signal rings from the kick
        float ringR = sinceKick * 1500.;
        float ring = exp(-pow((r - ringR) / (6. + sinceKick * 30.), 2.)) * exp(-sinceKick * 2.2);
        float ring2 = exp(-pow((r - ringR * .6) / 4., 2.)) * exp(-sinceKick * 3.) * .5;
        vec3 col = vec3(.012, .014, .03);
        col += c1 * sl * lines * (.35 + .65 * kick);
        col += c2 * (ring + ring2) * rings;
        col += c1 * .06 * exp(-r / 500.);
        fragColor = vec4(col, 1.);
      }`, {
      res: { value: new THREE.Vector2(ctx.engine.W, ctx.engine.H) }, S: { value: ctx.engine.S }, time: { value: 0 }, kick: { value: 0 },
      barPh: { value: 0 }, sinceKick: { value: 9 }, c1: { value: new THREE.Color(...INK.pale) }, c2: { value: new THREE.Color(...INK.yellow) },
      center: { value: new THREE.Vector2(960, 500) }, lines: { value: 1 }, rings: { value: 1 },
    });
  },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const A = ctx.audio;
    const u = mat.uniforms;
    u.time.value = t; u.kick.value = A.kick(t, 0.12);
    u.barPh.value = A.bar(t).phase + A.bar(t).k;
    u.sinceKick.value = Math.min(9, t - A.lastKickTime(t));
    u.c1.value.setRGB(...(p.c1 ?? INK.pale)); u.c2.value.setRGB(...(p.c2 ?? INK.yellow));
    u.center.value.set(...(p.center ?? [960, 480]));
    u.lines.value = p.lines ?? 1; u.rings.value = p.rings ?? 1;
    ctx.engine.pass(mat, ctx.engine.rtScene);
    if (p.stars) {
      const sm = skyMaterial(ctx.engine);
      setSky(sm.uniforms, { mode: 'light', band: 0, density: 0.8 }, ctx);
      sm.transparent = true; sm.blending = THREE.AdditiveBlending;
      ctx.engine.renderer.autoClear = false; ctx.engine.pass(sm, ctx.engine.rtScene); ctx.engine.renderer.autoClear = true;
      sm.blending = THREE.NormalBlending; sm.transparent = false;
    }
  },
};
