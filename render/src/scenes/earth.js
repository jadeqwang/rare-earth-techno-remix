// EARTH: ray-cast globe from Natural Earth land + populated places. Print / light / red / lightstick-blink.
import * as THREE from 'three';
import { skyMaterial, setSky } from './sky.js';
import { INK, clamp, smooth } from '../util.js';

let mat = null, landTex = null, lightsTex = null;

function loadTex(url) {
  return new Promise((res) => new THREE.TextureLoader().load(url, (t) => {
    t.colorSpace = THREE.NoColorSpace; t.flipY = false; t.needsUpdate = true; t.wrapS = THREE.RepeatWrapping; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; res(t);
  }));
}

export function earthMaterial(engine) {
  if (mat) return mat;
  mat = engine.shader(/* glsl */`
    uniform sampler2D tLand; uniform sampler2D tLights;
    uniform vec2 res; uniform float S; uniform float time; uniform float kick;
    uniform vec2 center; uniform float radius;            // design px
    uniform float lon0; uniform float lat0; uniform float roll;
    uniform vec3 sunDir;                                  // view space
    uniform float mode;                                   // 0 print 1 light
    uniform float red; uniform float blink; uniform float blinkT0;
    uniform vec3 inkOcean; uniform vec3 inkLand; uniform vec3 inkLights; uniform vec3 paperC; uniform vec3 rimC;
    uniform float cell; uniform float lightsGain;
    uniform vec2 sfLonLat;
    const float PI = 3.14159265;
    vec3 rotY(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(c*v.x + s*v.z, v.y, -s*v.x + c*v.z); }
    vec3 rotX(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(v.x, c*v.y - s*v.z, s*v.y + c*v.z); }
    void main(){
      vec2 px = vUv * res / S;
      vec2 q = (px - center) / radius;
      q = rot(roll) * q;
      float r2 = dot(q, q);
      float rr = sqrt(r2);
      // atmosphere outside the disc
      if (r2 > 1.) {
        float atm = exp(-(rr - 1.) * 14.) * (mode < .5 ? .9 : 1.2);
        float lit = clamp(dot(normalize(vec3(q, 0.)), normalize(sunDir)) * .5 + .5, 0., 1.);
        atm *= mix(.35, 1., lit);
        vec3 c = mode < .5 ? rimC : rimC * 1.4;
        if (red > 0.) c = mix(c, vec3(1., .12, .1), red);
        if (mode < .5) { float cov = halftone(px, atm * .8, cell, .5); fragColor = vec4(c, cov); }
        else fragColor = vec4(c * atm, atm);
        return;
      }
      vec3 n = vec3(q.x, q.y, sqrt(1. - r2));          // view-space normal
      // to globe coordinates: undo view tilt (lat0) and spin (lon0)
      vec3 g = rotX(n, -lat0);
      g = rotY(g, lon0);
      float lat = asin(clamp(g.y, -1., 1.));
      float lon = atan(g.x, g.z);
      vec2 uv = vec2(lon / (2. * PI) + .5, .5 - lat / PI);
      float land = texture(tLand, uv).r;
      float dl = 1.5 / 4096.;
      float coast = abs(texture(tLand, uv + vec2(dl, 0.)).r - texture(tLand, uv - vec2(dl, 0.)).r)
                  + abs(texture(tLand, uv + vec2(0., dl)).r - texture(tLand, uv - vec2(0., dl)).r);
      coast = smoothstep(.15, .6, coast);
      float lights = texture(tLights, uv).r * lightsGain;
      float day = smoothstep(-.08, .22, dot(n, normalize(sunDir)));
      float limb = pow(1. - n.z, 2.);
      // lightstick: synchronized blink on kicks + a wave ring travelling out from San Francisco
      float bl = 1.;
      if (blink > 0.) {
        vec3 sf = vec3(cos(sfLonLat.y) * sin(sfLonLat.x), sin(sfLonLat.y), cos(sfLonLat.y) * cos(sfLonLat.x));
        float ang = acos(clamp(dot(normalize(g), sf), -1., 1.));
        float wave = exp(-pow((ang - fract((time - blinkT0) * .55) * 3.3) * 4., 2.));
        bl = .25 + .9 * kick + (blink > 1.5 ? 1.2 * wave : .6 * wave);
      }
      vec3 col;
      if (mode < .5) {
        float oceanTone = mix(.95, .62, day) + limb * .1;
        float landTone = mix(.72, .16, day);
        float tone = mix(oceanTone, landTone, land);
        vec3 c = paperC;
        c = overprint(c, mix(inkOcean, inkLand, land * .0), halftone(px, tone, cell, .26));
        c = overprint(c, inkLand, land * .35 * day);
        c = overprint(c, inkLights, halftone(px + 2., clamp(lights * (1. - day) * bl, 0., 1.), cell * .6, 1.1));
        c = overprint(c, vec3(.043,.043,.078), coast * .9);
        if (red > 0.) c = mix(c, overprint(paperC, vec3(1.,.15,.1), .9), red * (.5 + .5 * land));
        col = c;
      } else {
        vec3 c = inkOcean * .05 * day + inkLand * land * .18 * day;
        c += inkLand * coast * .35 * (.3 + .7 * day);
        c += inkLights * lights * (1. - day * .9) * 1.6 * bl;
        c += rimC * limb * .5 * (.3 + .7 * day);
        if (red > 0.) c = mix(c, vec3(1., .1, .08) * (land * .8 + coast + limb), red);
        col = c;
      }
      fragColor = vec4(col, 1.);
    }`, {
    tLand: { value: null }, tLights: { value: null },
    res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S }, time: { value: 0 }, kick: { value: 0 },
    center: { value: new THREE.Vector2(960, 540) }, radius: { value: 380 }, lon0: { value: 0 }, lat0: { value: 0 }, roll: { value: 0 },
    sunDir: { value: new THREE.Vector3(0.8, 0.3, 0.4) }, mode: { value: 0 }, red: { value: 0 }, blink: { value: 0 }, blinkT0: { value: 0 },
    inkOcean: { value: new THREE.Color(...INK.klein) }, inkLand: { value: new THREE.Color(...INK.pale) }, inkLights: { value: new THREE.Color(...INK.orange) },
    paperC: { value: new THREE.Color(...INK.paper) }, rimC: { value: new THREE.Color(...INK.pale) },
    cell: { value: 5 }, lightsGain: { value: 2.2 }, sfLonLat: { value: new THREE.Vector2(-122.45 * Math.PI / 180, 37.76 * Math.PI / 180) },
  });
  mat.transparent = true;
  return mat;
}

export async function initEarth(engine) {
  earthMaterial(engine);
  if (!landTex) { [landTex, lightsTex] = await Promise.all([loadTex('assets/geo/land_4k.png'), loadTex('assets/geo/lights_4k.png')]); }
  mat.uniforms.tLand.value = landTex; mat.uniforms.tLights.value = lightsTex;
}

export function setEarth(ctx, p) {
  const u = mat.uniforms;
  const light = p.mode === 'light';
  u.time.value = ctx.t; u.kick.value = ctx.audio.kick(ctx.t, 0.18);
  u.mode.value = light ? 1 : 0;
  u.center.value.set(...(p.center ?? [960, 540]));
  u.radius.value = p.radius ?? 380;
  u.lon0.value = (p.lon ?? -122.4) * Math.PI / 180;
  u.lat0.value = (p.lat ?? 25) * Math.PI / 180;
  u.roll.value = p.roll ?? 0;
  u.sunDir.value.set(...(p.sun ?? [0.9, 0.35, -0.15]));
  u.red.value = p.red ?? 0;
  u.blink.value = p.blink ?? 0; u.blinkT0.value = p.blinkT0 ?? 0;
  u.cell.value = p.cell ?? 5;
  u.lightsGain.value = p.lightsGain ?? (light ? 3.0 : 2.4);
  u.paperC.value.setRGB(...(p.paper ?? INK.paper));
  u.inkLights.value.setRGB(...(p.lightsInk ?? (light ? [1.0, 0.62, 0.25] : INK.orange)));
}

export const earth = {
  async init(ctx) { await initEarth(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const e = ctx.engine;
    const sm = skyMaterial(e);
    setSky(sm.uniforms, { mode: p.mode, band: 0.6, density: 1.0, ...(p.sky || {}) }, ctx);
    e.pass(sm, e.rtScene);
    const view = p.view || 'night';
    const q = { ...p };
    if (view === 'night') {
      // night side facing us, thin sunlit crescent on the right, slow spin
      Object.assign(q, { center: p.center ?? [960, 1060], radius: p.radius ?? 900, lat: 30, lon: (p.lon ?? -100) + lt * 4, sun: [1.0, 0.2, -0.35], roll: 0.08 });
    }
    if (p.red) Object.assign(q, { center: [960, 560], radius: 420, lat: 20, lon: -60 + lt * 25, sun: [0.6, 0.3, 0.7] });
    setEarth(ctx, q);
    e.passOver(mat, e.rtScene);
  },
};
