// ETZ-1715 b — the other world. Ringed planet from space, and their skies/towers from the surface.
import * as THREE from 'three';
import { INK, clamp, smooth, range } from '../util.js';
import { skyMaterial, setSky } from './sky.js';
import { SCENES } from './index.js';

let planetMat = null, worldMat = null;

function mkPlanet(engine) {
  planetMat = engine.shader(/* glsl */`
    uniform vec2 res; uniform float S; uniform float time; uniform float kick; uniform float mode; uniform float blink; uniform float infra;
    uniform vec2 center; uniform float radius; uniform float spin; uniform float tilt; uniform vec3 sunDir;
    uniform vec3 inkA; uniform vec3 inkB; uniform vec3 inkC; uniform vec3 paperC; uniform float cell;
    const float PI = 3.14159265;
    vec3 rotY(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(c*v.x + s*v.z, v.y, -s*v.x + c*v.z); }
    vec3 rotX(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(v.x, c*v.y - s*v.z, s*v.y + c*v.z); }
    float hexLines(vec2 p){ // distance to a hex lattice's edges
      vec2 r = vec2(1., 1.732); vec2 h = r * .5;
      vec2 a = mod(p, r) - h; vec2 b = mod(p - h, r) - h;
      vec2 g = dot(a, a) < dot(b, b) ? a : b;
      vec2 q = abs(g); float d = max(q.x * .866 + q.y * .5, q.y);
      return .5 - d; }
    void main(){
      vec2 px = vUv * res / S;
      vec2 q = (px - center) / radius;
      // ring plane (tilted toward us)
      vec3 nR = normalize(vec3(-.18, cos(tilt), sin(tilt)));
      float zr = -(q.x * nR.x + q.y * nR.y) / nR.z;
      vec3 P = vec3(q, zr);
      float rr = length(P);
      float ringBand = smoothstep(1.35, 1.40, rr) * (1. - smoothstep(2.25, 2.35, rr));
      float ringDen = ringBand * (.35 + .65 * fbm3(vec2(rr * 40., 1.))) * (1. - .8 * smoothstep(1.78, 1.8, rr) * (1. - smoothstep(1.86, 1.88, rr)));
      float station = smoothstep(1.13, 1.12, rr) * smoothstep(1.105, 1.115, rr);   // thin orbital ring
      float nodes = station * step(.985, fract(atan(P.y, P.x) / (2. * PI) * 24. + time * .02));
      float r2 = dot(q, q);
      float inside = step(r2, 1.);
      float zs = sqrt(max(0., 1. - r2));
      float ringFront = step(zs, zr);          // ring point in front of the planet surface
      vec3 col = paperC; float alpha = 0.;
      // --- planet surface
      vec3 surf = vec3(0.); float cov = 0.;
      if (r2 < 1.) {
        vec3 n = vec3(q, zs);
        vec3 g = rotX(n, -.35); g = rotY(g, spin);
        float lat = asin(g.y), lon = atan(g.x, g.z);
        vec2 uvp = vec2(lon * 1.6, lat * 3.);
        float land = smoothstep(.48, .56, fbm(uvp * 1.3 + 3.));
        float day = smoothstep(-.1, .25, dot(n, normalize(sunDir)));
        float limb = pow(1. - zs, 2.5);
        float lattice = smoothstep(.06, .0, hexLines(vec2(lon, lat) * 9.)) * land;
        float cityGlow = lattice * (1. - day) * (.6 + .4 * fbm3(uvp * 6.));
        float bl = blink > 0. ? (.25 + 1.3 * kick) : 1.;
        if (mode < .5) {
          vec3 c = paperC;
          c = overprint(c, inkA, halftone(px, mix(.55, .92, 1. - day) + limb * .1, cell, .26));   // violet ocean / night
          c = overprint(c, inkB, halftone(px + 2., land * mix(.25, .6, day), cell, .9));        // pink land
          c = overprint(c, inkC, cityGlow * 1.2);                                                   // mint lattice
          surf = c; cov = 1.;
        } else {
          vec3 c = inkA * .08 * day + inkB * land * .15 * day;
          c += inkC * cityGlow * 2.2 * bl;
          c += inkB * limb * .6;
          surf = c; cov = 1.;
        }
      }
      // --- composite: ring behind, planet, ring in front, station ring, atmosphere
      vec3 ringCol = mode < .5 ? inkB : inkB * .9;
      float ringVis = ringDen * (inside > .5 ? ringFront : 1.);
      if (mode < .5) {
        col = paperC; alpha = 0.;
        if (r2 < 1.) { col = surf; alpha = 1.; }
        col = overprint(col, ringCol, halftone(px + 1., ringVis * .8, cell * .8, 1.2)); alpha = max(alpha, ringVis > .02 ? halftone(px + 1., ringVis * .8, cell * .8, 1.2) : 0.);
        float stv = station * (inside > .5 ? step(zs, .5) : 1.);
        col = overprint(col, vec3(.043,.043,.078), stv); alpha = max(alpha, stv);
        float atm = (1. - inside) * exp(-(sqrt(r2) - 1.) * 18.);
        col = overprint(col, inkB, halftone(px, atm, cell, .5)); alpha = max(alpha, halftone(px, atm, cell, .5));
      } else {
        col = vec3(0.);
        if (r2 < 1.) { col = surf; alpha = 1.; }
        col += ringCol * ringVis * .45; alpha = max(alpha, ringVis * .6);
        col += inkC * (station * .8 + nodes * 3.) * (inside > .5 ? step(zs, .5) : 1.);
        alpha = max(alpha, station);
        float atm = (1. - inside) * exp(-(sqrt(r2) - 1.) * 16.);
        col += inkB * atm * 1.2; alpha = max(alpha, atm);
      }
      // --- orbital infrastructure: a satellite train in equatorial orbit and a space elevator with its climber
      if (infra > 0.) {
        vec3 U = normalize(cross(nR, vec3(0., 0., 1.)));
        vec3 V = -normalize(cross(nR, U));
        float sats = 0., satHalo = 0.;
        for (int i = 0; i < 24; i++) {
          float ph = -2.4 + time * .3 + float(i) * .05;
          vec3 sp = 1.2 * (cos(ph) * U + sin(ph) * V);
          float vis = (sp.z > 0. || dot(sp.xy, sp.xy) > 1.) ? 1. : 0.;
          float d = length(q - sp.xy) * radius;
          sats += vis * smoothstep(3.6, 2.0, d); satHalo += vis * smoothstep(6.5, 4.4, d);
        }
        vec3 D = cos(.8) * U + sin(.8) * V;
        vec2 e0 = D.xy, e1 = D.xy * 3.0, ab = e1 - e0;
        float hh = clamp(dot(q - e0, ab) / dot(ab, ab), 0., 1.);
        float tether = smoothstep(2.4, 1.0, length(q - e0 - ab * hh) * radius);
        float climber = smoothstep(6.5, 4., length(q - e0 - ab * fract(time * .2)) * radius);
        float cw = smoothstep(11., 8.5, length((q - e1) * radius * vec2(1., 1.6)));
        sats = clamp(sats, 0., 1.) * infra; satHalo = clamp(satHalo, 0., 1.) * infra;
        tether *= infra; climber *= infra; cw *= infra;
        if (mode < .5) {
          vec3 inkK = vec3(.043, .043, .078);
          col = overprint(col, inkK, max(max(tether * .9, cw), satHalo));
          col = mix(col, paperC, max(sats, climber));
        } else {
          col += inkC * tether * .9 + vec3(1., .92, .6) * (climber * 2.5 + sats * 1.8) + inkC * cw * 1.5;
        }
        alpha = max(alpha, max(max(tether, cw), max(satHalo, climber)));
      }
      fragColor = vec4(col, clamp(alpha, 0., 1.));
    }`, {
    res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S }, time: { value: 0 }, kick: { value: 0 }, infra: { value: 1 },
    mode: { value: 0 }, blink: { value: 0 }, center: { value: new THREE.Vector2(960, 540) }, radius: { value: 300 },
    spin: { value: 0 }, tilt: { value: 1.25 }, sunDir: { value: new THREE.Vector3(-0.8, 0.3, 0.5) },
    inkA: { value: new THREE.Color(...INK.violet) }, inkB: { value: new THREE.Color(...INK.pink) }, inkC: { value: new THREE.Color(...INK.mint) },
    paperC: { value: new THREE.Color(...INK.paper) }, cell: { value: 5 },
  });
  planetMat.transparent = true;
}

function mkWorld(engine) {
  worldMat = engine.shader(/* glsl */`
    uniform vec2 res; uniform float S; uniform float time; uniform float kick; uniform float mode; uniform float view;
    uniform vec3 pink; uniform vec3 mint; uniform vec3 violet; uniform vec3 coral; uniform vec3 paperC; uniform float cell; uniform float sol;
    float sdBox(vec2 p, vec2 b){ vec2 d = abs(p) - b; return length(max(d, 0.)) + min(max(d.x, d.y), 0.); }
    void main(){
      vec2 px = vUv * res / S;
      float y = vUv.y;
      bool light = mode > .5;
      // sky
      vec3 skyTop = light ? vec3(.03, .015, .07) : violet;
      vec3 skyBot = light ? vec3(.12, .03, .14) : pink;
      float sk = smoothstep(.2, 1., y);
      // planetary ring arc across the sky
      vec2 rc = px - vec2(1500., -900.);
      float rr = length(rc * vec2(1., 1.25));
      float arc = smoothstep(1900., 1915., rr) * (1. - smoothstep(1990., 2010., rr)) * (.6 + .4 * fbm3(vec2(rr * .05, 3.)));
      arc *= 1. - smoothstep(1945., 1950., rr) * (1. - smoothstep(1957., 1962., rr));
      // coral sun
      float sunD = length(px - vec2(1380., 380.));
      float sun = view > .5 && view < 1.5 ? 0. : (light ? 0. : 1. - smoothstep(170., 173., sunD));
      // cloud sea
      float cl = 0.;
      for (int i = 0; i < 4; i++) {
        float fi = float(i);
        float h = 330. - fi * 70. + 40. * fbm3(vec2(px.x * (.004 + fi * .002) + time * (.05 + fi * .03), fi * 3.));
        cl = max(cl, (1. - smoothstep(h - 2., h + 2., px.y)) * (.35 + fi * .18));
      }
      // tower (their signal tower): a slender white spire rising out of the cloud sea, a halo ring of lights near the top
      vec2 tp = px - vec2(820., 0.);
      float hN = clamp(tp.y / 980., 0., 1.);
      float w = mix(86., 12., pow(hN, .65));
      float spire = step(abs(tp.x), w) * step(tp.y, 930.) + step(abs(tp.x), 3.) * step(tp.y, 1040.) * step(930., tp.y);
      float seam = step(abs(tp.x), 1.2) * step(tp.y, 900.);
      float ringY = 800.;
      vec2 rq = (px - vec2(820., ringY)) / vec2(235., 46.);
      float ringD = abs(length(rq) - 1.) * 46.;
      float halo = 1. - smoothstep(4., 7., ringD);
      vec2 rq2 = (px - vec2(820., 560.)) / vec2(140., 26.);
      halo = max(halo, (1. - smoothstep(2.5, 4.5, abs(length(rq2) - 1.) * 26.)) * .9);
      float haloFront = step(0., -rq.y + .05);      // front half of the ring draws over the spire
      float lights = 0.;
      for (int k = 0; k < 20; k++) {
        float a = float(k) / 20. * 6.2832 + time * .6;
        vec2 lp = vec2(820. + cos(a) * 235., ringY + sin(a) * 46.);
        float on = .35 + .65 * step(.45, fract(float(k) * .37 + time * 1.7)) + kick * 1.8;
        lights += on * exp(-length(px - lp) / 6.5);
      }
      float wins = 0.;
      for (int k = 0; k < 12; k++) { float wy = 360. + float(k) * 36.; wins += exp(-length(px - vec2(820., wy)) / 3.) * (.5 + .5 * step(.5, fract(float(k) * .61 + time * .9))); }
      float tower = clamp(spire, 0., 1.);
      float ringBar = halo;
      if (view > .5 && view < 2.5) { tower = 0.; lights = 0.; ringBar = 0.; wins = 0.; seam = 0.; }   // only the tower views show it
      // stars + SOL (a pale blue dot) at night
      float st = 0.;
      if (light) { vec2 g = floor(px / 9.); float h = hash12(g); st = step(.985, h) * (1. - smoothstep(0., 1.6, length(fract(px / 9.) - .5) * 9.)); }
      float solD = length(px - vec2(560., 760.));
      float solv = sol * (exp(-solD / 3.) + exp(-solD / 14.) * .5);
      vec3 col;
      if (!light) {
        vec3 c = paperC;
        c = overprint(c, violet, halftone(px, mix(.95, .15, 1. - sk), cell, .26));
        c = overprint(c, pink, halftone(px + 2., .55 * (1. - sk) + .2, cell, .9));
        c = overprint(c, pink, arc);
        c = overprint(c, coral, sun);
        c = overprint(c, violet, halftone(px, cl * .9, cell * .85, .5));
        c = mix(c, paperC, tower);                                  // white spire
        c = overprint(c, violet, tower * halftone(px, .25 + .5 * smoothstep(0., 60., abs(tp.x)) , cell * .7, .3));
        c = overprint(c, vec3(.043,.043,.078), seam * .6 + ringBar * .95);
        c = overprint(c, mint, clamp(lights + wins, 0., 1.));
        col = c;
      } else {
        vec3 c = mix(skyBot, skyTop, sk);
        c += pink * arc * .35 + vec3(1.) * st * .8;
        c += violet * cl * .6 + pink * cl * .08;
        c = mix(c, vec3(.05, .03, .09), tower);
        c += pink * tower * .12 + mint * ringBar * .25;
        c += mint * (lights * 2. + wins * 1.5);
        if (view < .5 || view > 2.5) {
          float beam = exp(-abs(px.x - 820.) / (3. + kick * 6.)) * step(1040., px.y) * (.4 + 1.2 * kick);
          c += mint * beam;
        }
        c += vec3(.61, .8, 1.) * solv * 2.;
        col = c;
      }
      fragColor = vec4(col, 1.);
    }`, {
    res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S }, time: { value: 0 }, kick: { value: 0 },
    mode: { value: 0 }, view: { value: 0 }, sol: { value: 0 },
    pink: { value: new THREE.Color(...INK.pink) }, mint: { value: new THREE.Color(...INK.mint) }, violet: { value: new THREE.Color(...INK.violet) },
    coral: { value: new THREE.Color(1.0, 0.5, 0.42) }, paperC: { value: new THREE.Color(...INK.paper) }, cell: { value: 6 },
  });
}

export const planet = {
  init(ctx) { mkPlanet(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const e = ctx.engine;
    const light = p.mode === 'light';
    if (!p.noSky) {
      const sm = skyMaterial(e);
      setSky(sm.uniforms, { mode: p.mode, band: 0.5, density: 1.1, skyInk: INK.violet, bandInk: INK.pink, glowInk: INK.pink, ...(p.sky || {}) }, ctx);
      e.pass(sm, e.rtScene);
    }
    const u = planetMat.uniforms;
    u.time.value = t; u.kick.value = ctx.audio.kick(t, 0.15);
    u.mode.value = light ? 1 : 0; u.blink.value = p.blink ?? 0;
    u.center.value.set(...(p.center ?? [960, 560]));
    u.radius.value = (p.radius ?? 300) * (1 + (p.zoomRate ?? 0.03) * lt);
    u.spin.value = (p.spin0 ?? 0) + lt * 0.12;
    u.tilt.value = p.tilt ?? 0.32;
    u.infra.value = p.infra ?? 1;
    u.paperC.value.setRGB(...(light ? [0, 0, 0] : INK.paper));
    e.passOver(planetMat, e.rtScene);
  },
};

export const otherworld = {
  init(ctx) { mkWorld(ctx.engine); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    // the city/vista are rotoscoped from the Seedance plate (se04) in the other world's inks
    if (p.view === 'city' || p.view === 'vista') {
      const light = p.mode === 'light';
      return SCENES.roto.draw(ctx, { ...shot, p: { clip: 'se04', start: shot.t0 - (p.clipOffset ?? 0), lag: 0, mode: p.mode || 'print',
        inkA: INK.violet, inkB: INK.pink, inkC: INK.mint, paper: light ? [0.02, 0.01, 0.04] : INK.paper,
        glow: INK.pink, glow2: INK.mint, cell: 6, twos: true, envFill: light ? 0.9 : 0 } }, t, lt);
    }
    const u = worldMat.uniforms;
    u.time.value = t; u.kick.value = ctx.audio.kick(t, 0.15);
    u.mode.value = p.mode === 'light' ? 1 : 0;
    u.view.value = { tower: 0, night: 1, sky: 2, towerNight: 3 }[p.view || 'tower'] ?? 0;
    if (p.view === 'tower' && p.mode === 'light') u.view.value = 0;
    u.sol.value = p.sol ?? 0;
    ctx.engine.pass(worldMat, ctx.engine.rtScene);
  },
};
