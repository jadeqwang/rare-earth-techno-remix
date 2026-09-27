// Procedural night sky, in PRINT (halftone ink on paper) or LIGHT (emissive) look.
import * as THREE from 'three';
import { INK } from '../util.js';

let mat = null;

export function skyMaterial(engine) {
  if (mat) return mat;
  mat = engine.shader(/* glsl */`
    uniform vec2 res; uniform float S; uniform float time; uniform float kick;
    uniform float mode;           // 0 print, 1 light
    uniform vec3 skyInk; uniform vec3 bandInk; uniform vec3 glowInk; uniform vec3 paperC; uniform vec3 starCol;
    uniform vec2 pan;             // design px
    uniform float spin;           // radians
    uniform float zoom;
    uniform float density;        // star density multiplier
    uniform float band;           // milky way strength
    uniform float bandAngle;
    uniform float horizon;        // horizon glow height (0..1 of screen, from bottom), <0 disables
    uniform float horizonAmt;
    uniform float cell;
    uniform float warp;           // star streaks (hyperspace), 0..1
    uniform vec2 warpCenter;
    uniform float twinkle;
    float starLayer(vec2 p, float scale, float thresh, out float twk){
      vec2 q = p / scale; vec2 id = floor(q); vec2 f = fract(q) - .5;
      vec2 h = hash22(id);
      float b = hash12(id + 7.3);
      twk = hash12(id + 3.1);
      if (b < thresh) return 0.;
      vec2 sp = (h - .5) * .7;
      float d = length(f - sp) * scale;
      float br = (b - thresh) / (1. - thresh);
      return br * (1. - smoothstep(.0, 1.2 + br * 1.8, d));
    }
    void main(){
      vec2 px = vUv * res / S;                   // design px
      vec2 c = vec2(960., 540.);
      vec2 p = (px - c) / zoom;
      p = rot(spin) * p + pan;
      float twk;
      float st = 0.;
      float dens = clamp(density, 0., 3.);
      st += starLayer(p, 23., 1. - .10 * dens, twk);
      float twk2; st += .8 * starLayer(p + 51.3, 41., 1. - .12 * dens, twk2);
      float twk3; st += 1.4 * starLayer(p + 13.7, 97., 1. - .22 * dens, twk3);
      st *= 1. + twinkle * (sin(time * 9. + twk * 40.) * .5 + .5) * .6 + kick * .5 * step(.7, twk);
      // warp streaks
      if (warp > 0.) {
        vec2 dir = normalize(px - warpCenter + 1e-4);
        float ang = atan(dir.y, dir.x);
        float r = length(px - warpCenter);
        float a1 = floor(ang * 180.);
        float hsh = hash12(vec2(a1, 3.));
        float seg = fract(r * .002 - time * (1.5 + hsh * 3.) * warp + hsh);
        float streak = smoothstep(.0, .02, abs(fract(ang * 180.) - .5) < .12 ? 1. : 0.) * step(.85, hsh) * smoothstep(.0, .6, seg) * (1. - smoothstep(.6, 1., seg));
        st += streak * warp * 1.5 * smoothstep(60., 400., r);
      }
      // milky way band
      vec2 bp = rot(bandAngle) * (p * .0012);
      float bdx = bp.y * 3.2 + (fbm3(bp * 3.) - .5) * .9; float bd = exp(-bdx * bdx);
      float dust = fbm3(bp * 7. + 4.);
      float mw = band * bd * (.55 + .6 * dust);
      float lanes = smoothstep(.55, .75, fbm3(bp * 11. + 9.)) * bd * band;
      // horizon glow
      float hz = horizon < 0. ? 0. : horizonAmt * exp(-max(0., vUv.y - horizon) * 7.) * smoothstep(horizon - .25, horizon, vUv.y + .2);
      vec3 col;
      if (mode < .5) {
        // print: dense sky ink, lighter in the band, stars knocked out to paper
        float skyTone = .88 - .2 * vUv.y * 0. - mw * .45 + lanes * .25;
        float cov = halftone(px, clamp(skyTone - hz * .6, 0., 1.), cell, .78);
        col = overprint(paperC, skyInk, cov);
        col = overprint(col, bandInk, halftone(px + 3., mw * .55, cell * .8, 1.3) * .8);
        col = overprint(col, glowInk, halftone(px + 1.7, hz, cell, .1));
        col = mix(col, paperC, clamp(st * 1.3, 0., 1.));
      } else {
        col = paperC;                               // near-black
        col += bandInk * mw * .22 + glowInk * hz * .5;
        col -= lanes * .03;
        col += starCol * st * 1.6;
      }
      fragColor = vec4(col, 1.);
    }`, {
    res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S }, time: { value: 0 }, kick: { value: 0 },
    mode: { value: 0 }, skyInk: { value: new THREE.Color(...INK.klein) }, bandInk: { value: new THREE.Color(...INK.pale) },
    glowInk: { value: new THREE.Color(...INK.orange) }, paperC: { value: new THREE.Color(...INK.paper) }, starCol: { value: new THREE.Color(1, 1, 1) },
    pan: { value: new THREE.Vector2() }, spin: { value: 0 }, zoom: { value: 1 }, density: { value: 1 }, band: { value: 0.8 },
    bandAngle: { value: 0.5 }, horizon: { value: -1 }, horizonAmt: { value: 0.8 }, cell: { value: 6 }, warp: { value: 0 },
    warpCenter: { value: new THREE.Vector2(960, 540) }, twinkle: { value: 0.3 },
  });
  return mat;
}

export function setSky(u, p, ctx) {
  const set = (k, v) => { if (v === undefined) return; if (u[k].value && u[k].value.setRGB && Array.isArray(v)) u[k].value.setRGB(...v); else if (u[k].value && u[k].value.set && Array.isArray(v)) u[k].value.set(...v); else u[k].value = v; };
  u.time.value = ctx.t; u.kick.value = ctx.audio.kick(ctx.t);
  const light = p.mode === 'light';
  u.mode.value = light ? 1 : 0;
  set('paperC', p.paper ?? (light ? [0.018, 0.02, 0.04] : INK.paper));
  set('skyInk', p.skyInk ?? INK.klein); set('bandInk', p.bandInk ?? INK.pale); set('glowInk', p.glowInk ?? INK.orange);
  set('starCol', p.starCol ?? [1, 1, 1]);
  u.pan.value.set(...(p.pan ?? [0, 0])); u.spin.value = p.spin ?? 0; u.zoom.value = p.zoom ?? 1;
  u.density.value = p.density ?? 1; u.band.value = p.band ?? 0.8; u.bandAngle.value = p.bandAngle ?? 0.5;
  u.horizon.value = p.horizon ?? -1; u.horizonAmt.value = p.horizonAmt ?? 0.8; u.cell.value = p.cell ?? 6;
  u.warp.value = p.warp ?? 0; u.warpCenter.value.set(...(p.warpCenter ?? [960, 540])); u.twinkle.value = p.twinkle ?? 0.3;
}

export const sky = {
  async draw(ctx, shot, t, lt) {
    const m = skyMaterial(ctx.engine);
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    setSky(m.uniforms, p, ctx);
    ctx.engine.pass(m, ctx.engine.rtScene);
  },
};
