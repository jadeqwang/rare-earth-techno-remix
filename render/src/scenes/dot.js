// PALE BLUE DOT (after Voyager 1, 14 Feb 1990): scattered-sunlight bands, grain, one tiny blue dot.
// Also ZOOM: the powers-of-ten pull-back from San Francisco into that dot.
import * as THREE from 'three';
import { earthMaterial, setEarth } from './earth.js';
import { INK, clamp, smooth, range, easeInOutCubic, lerp } from '../util.js';

let mat = null;

function dotMaterial(engine) {
  if (mat) return mat;
  mat = engine.shader(/* glsl */`
    uniform vec2 res; uniform float S; uniform float time; uniform float kick;
    uniform vec2 dotPos; uniform float dotR; uniform float bands; uniform float ping; uniform float zoom; uniform vec2 zc;
    uniform vec3 inkA; uniform vec3 inkB; uniform vec3 inkC; uniform vec3 dotC; uniform float mode;
    float band(float x, float c, float w){ return exp(-pow((x - c) / w, 2.)); }
    void main(){
      vec2 px0 = vUv * res / S;
      vec2 px = (px0 - zc) / zoom + zc;
      // slightly tilted vertical bands like the Voyager frame
      float x = px.x + (px.y - 540.) * .085;
      float b1 = band(x, 520., 120.) * (.8 + .2 * fbm3(vec2(px.y * .004, 1.)));
      float b2 = band(x, 1020., 70.) * (.9 + .3 * fbm3(vec2(px.y * .006, 5.)));
      float b3 = band(x, 1330., 170.) * .6;
      float b4 = band(x, 1640., 50.) * .5;
      float streak = smoothstep(.97, 1., vnoise(vec2(x * .05, px.y * .0008)));
      float g = hash12(floor(px0 * .75) + floor(time * 12.)) * .08;   // sensor grain
      vec3 col;
      float dd = length(px - dotPos);
      float dotv = 1. - smoothstep(dotR - .8, dotR + .8, dd);
      float ring = ping * exp(-pow((dd - (dotR + 8. + (1. - ping) * 140.)) / 2.2, 2.));
      if (mode < .5) {
        vec3 c = vec3(.043, .043, .078);
        c = mix(c, inkA * .55, clamp(b1 * bands, 0., 1.) * .8);
        c = mix(c, inkB * .6, clamp(b2 * bands, 0., 1.) * .9);
        c = mix(c, inkC * .45, clamp(b3 * bands, 0., 1.) * .8);
        c = mix(c, inkB * .5, clamp(b4 * bands, 0., 1.) * .7);
        c += g + streak * .05;
        c = mix(c, dotC, dotv);
        c += dotC * ring;
        col = c;
      } else {
        vec3 c = vec3(.01, .012, .025);
        c += inkA * b1 * bands * .35 + inkB * b2 * bands * .45 + inkC * b3 * bands * .3 + inkB * b4 * bands * .25;
        c += g * .6;
        c += dotC * (dotv * 1.5 + exp(-dd / (dotR * 3.)) * .5) + dotC * ring;
        col = c;
      }
      fragColor = vec4(col, 1.);
    }`, {
    res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S }, time: { value: 0 }, kick: { value: 0 },
    dotPos: { value: new THREE.Vector2(1020, 560) }, dotR: { value: 3.5 }, bands: { value: 1 }, ping: { value: 0 },
    zoom: { value: 1 }, zc: { value: new THREE.Vector2(1020, 560) },
    inkA: { value: new THREE.Color(...INK.orange) }, inkB: { value: new THREE.Color(0.95, 0.75, 0.55) }, inkC: { value: new THREE.Color(...INK.pale) },
    dotC: { value: new THREE.Color(...INK.pale) }, mode: { value: 0 },
  });
  return mat;
}

export function drawDot(ctx, p) {
  const m = dotMaterial(ctx.engine);
  const u = m.uniforms;
  u.time.value = ctx.t; u.kick.value = ctx.audio.kick(ctx.t);
  u.dotPos.value.set(...(p.dotPos ?? [1020, 560]));
  u.dotR.value = p.dotR ?? 3.5;
  u.bands.value = p.bands ?? 1;
  u.ping.value = p.ping ?? 0;
  u.zoom.value = p.zoom ?? 1;
  u.zc.value.set(...(p.dotPos ?? [1020, 560]));
  u.mode.value = p.mode === 'light' ? 1 : 0;
  ctx.engine.pass(m, ctx.engine.rtScene);
}

export const dot = {
  init(ctx) { dotMaterial(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const A = ctx.audio;
    // a ping ring on every kick
    const kt = A.lastKickTime(t);
    const ping = t - kt < 0.9 ? 1 - (t - kt) / 0.9 : 0;
    drawDot(ctx, { ...p, ping, zoom: 1 + lt * 0.035, dotR: 3.5 + A.kick(t) * 2 });
  },
};

// ZOOM: SF night -> the whole planet -> a speck in the sunbeam
export const zoom = {
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const from = p.from ?? shot.t0, to = p.to ?? shot.t1;
    const k = clamp((t - from) / (to - from));
    // radius falls exponentially: 5200 px (continent-scale) -> 3.5 px (a dot)
    const r = Math.exp(lerp(Math.log(5200), Math.log(3.5), easeInOutCubic(Math.min(1, k * 1.12))));
    const dotPos = [lerp(960, 1020, smooth(range(k, 0.3, 0.9))), lerp(540, 560, smooth(range(k, 0.3, 0.9)))];
    const bands = smooth(range(k, 0.35, 0.85));
    drawDot(ctx, { dotPos, dotR: Math.max(3.5, 0), bands, mode: 'print' });
    if (r > 4) {
      const em = earthMaterial(ctx.engine);
      // keep SF at the center while zoomed in, the globe rotates slightly as we pull away
      setEarth(ctx, { mode: 'print', center: [dotPos[0], dotPos[1] + (r > 600 ? r * 0.0 : 0)], radius: r,
        lon: -122.4 + (1 - k) * 0, lat: 37.8 - k * 12, sun: [0.95, 0.25, -0.2], cell: r > 200 ? 5 : 3, lightsGain: 3.2 });
      em.uniforms.center.value.set(dotPos[0], dotPos[1]);
      ctx.engine.passOver(em, ctx.engine.rtScene);
    }
  },
};
