// THE LISTENING FIELD on Echo: petal dishes that bloom and turn in unison, linked by mint light.
import * as THREE from 'three';
import { Toon3D, gbufMaterial } from '../toon3d.js';
import { skyMaterial, setSky } from './sky.js';
import { clamp, easeOutBack, easeOutCubic, hash1, lerp, INK, smooth } from '../util.js';

let toon, scene, camera, dishes = [];

function petalGeometry() {
  // a curved petal: a slice of a sphere cap, hinged at the origin, opening along +y
  const g = new THREE.SphereGeometry(5.0, 10, 6, -0.47, 0.94, 0.0, 0.62);
  g.translate(0, -5.0, 0);
  g.rotateX(Math.PI);   // cup faces up
  return g;
}

function build() {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(46, 16 / 9, 0.5, 400);
  const matPetal = gbufMaterial({ ambient: 0.28, toneMul: 1.15 });
  const matStem = gbufMaterial({ ambient: 0.12, toneMul: 0.7 });
  const matLink = gbufMaterial({ ambient: 1, accent: 1 });
  const matGround = gbufMaterial({ ambient: 0.08, toneMul: 0.45, lightDir: [0.1, 1, 0.2] });
  for (const m of [matPetal, matStem, matLink, matGround]) m.uniforms.far.value = 200;
  const pg = petalGeometry();
  const stemG = new THREE.CylinderGeometry(0.18, 0.3, 3.2, 8);
  let i = 0;
  const pos = [];
  for (let r = 0; r < 9; r++) for (let q = -6; q <= 6; q++) {
    const x = q * 9 + (r % 2) * 4.5 + (hash1(r * 17 + q) - 0.5) * 1.5;
    const z = -r * 7.8 - 6;
    pos.push([x, z]);
    const root = new THREE.Group(); root.position.set(x, 0, z);
    const stem = new THREE.Mesh(stemG, matStem); stem.position.y = 1.6; root.add(stem);
    const head = new THREE.Group(); head.position.y = 3.3; root.add(head);
    const petals = [];
    for (let k = 0; k < 6; k++) {
      const hinge = new THREE.Group(); hinge.rotation.y = (k / 6) * Math.PI * 2;
      const tilt = new THREE.Group(); hinge.add(tilt);
      const m = new THREE.Mesh(pg, matPetal); tilt.add(m);
      head.add(hinge); petals.push(tilt);
    }
    scene.add(root);
    dishes.push({ root, head, petals, x, z, i: i++, seed: hash1(i * 5.1) });
  }
  // mint links between neighbours on the ground
  const pts = [];
  for (let a = 0; a < pos.length; a++) for (let b = a + 1; b < pos.length; b++) {
    const d = Math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]);
    if (d < 10.5 && hash1(a * 31 + b) > 0.35) pts.push(pos[a][0], 0.05, pos[a][1], pos[b][0], 0.05, pos[b][1]);
  }
  const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  lg.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(pts.length).fill(0).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
  scene.add(new THREE.LineSegments(lg, matLink));
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), matGround); ground.rotation.x = -Math.PI / 2; scene.add(ground);
}

function pose(d, t, p, A) {
  const mode = p.choreo || 'bloom';
  const b = A.beat(t);
  let open = 1, az = 0, el = 1.2;
  if (mode === 'bloom') {
    const delay = (Math.hypot(d.x, d.z + 30) / 70) * 0.9;
    open = easeOutBack(clamp((t - (p.t0 ?? 0) - 0.1 - delay) / 0.6), 1.4);
    el = lerp(1.57, 1.1, open); az = 0.3 * Math.sin(d.seed * 6);
  } else if (mode === 'sweep') {
    open = 1; az = 0.5 * Math.sin(t * 0.5); el = 1.05 + 0.1 * Math.sin(t * 0.7);
  } else if (mode === 'converse') {
    // the counterpart of the array's 'converse' (scenes/array.js): same steps, aimed back the other way, blooming as it rises
    const k = p.step ?? 0, EL = [0.35, 0.6, 0.85, 1.05, 1.25], OPEN = [0.5, 0.65, 0.8, 0.9, 0.95];   // past ~1 the petals splay flat
    const delay = clamp(Math.hypot(d.x, d.z) / 110) * 0.1;
    const ph = clamp((t - p.tSnap - delay) / 0.22), e = easeOutBack(ph, 2.0);
    const antic = smooth(clamp((t - p.t0) / (p.tSnap - p.t0))) * (1 - ph);
    const AZ = (n) => p.aim * (0.75 - 0.15 * n);
    az = lerp(AZ(k), AZ(k + 1), e) - p.aim * 0.05 * antic;
    el = lerp(EL[k], EL[k + 1], e) - 0.08 * antic;
    open = lerp(OPEN[k], OPEN[k + 1], e) - 0.1 * antic;
  } else if (mode === 'snap' || mode === 'dance') {
    const tg = (n) => [(hash1(n * 2.3) - 0.5) * 1.4, 0.9 + hash1(n * 3.9) * 0.6];
    const delay = mode === 'dance' ? clamp((d.x + 60) / 120) * 0.35 : 0;
    const e = easeOutBack(clamp((b.phase - delay) / 0.28), 2.0);
    const [a0, e0] = tg(b.i - 1), [a1, e1] = tg(b.i);
    az = lerp(a0, a1, e); el = lerp(e0, e1, e);
    open = 0.75 + 0.25 * Math.cos(b.phase * Math.PI * 2) + (mode === 'dance' ? 0.3 * A.kick(t, 0.12) * (d.i % 2 ? 1 : -1) : 0);
  }
  return { open: clamp(open, 0, 1.3), az, el };
}

export const petals = {
  init(ctx) { toon = new Toon3D(ctx.engine); build(); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const A = ctx.audio;
    const light = p.mode === 'light';
    const sm = skyMaterial(ctx.engine);
    setSky(sm.uniforms, { mode: p.mode, band: 1.0, bandAngle: -0.3, density: 1.4, horizon: 0.32, horizonAmt: 0.6,
      skyInk: INK.violet, bandInk: INK.pink, glowInk: INK.pink, pan: [lt * 5, 0], ...(p.sky || {}) }, ctx);
    ctx.engine.pass(sm, ctx.engine.rtScene);
    for (const d of dishes) {
      const { open, az, el } = pose(d, t, { t0: shot.t0, ...p }, A);
      d.head.rotation.y = az + Math.PI; // face the camera side
      d.head.rotation.x = -(Math.PI / 2 - el) * 0.9;
      for (const pt of d.petals) pt.rotation.z = lerp(-1.35, 0.0, open); // closed bud -> open dish
    }
    const cam = p.cam || 'low';
    if (cam === 'low') { camera.position.set(-4 + lt * 1.4, 3.2, 12 - lt * 1.5); camera.lookAt(6, 7, -40); }
    else if (cam === 'mirror') {
      // the array's 'converse' angle mirrored (from the right, looking left), pushed in on each of its beats
      const push = p.push ?? 0;
      camera.position.set(4 - lt * 1.6 - push * 1.5, 8.5, 12 - lt * 3 - push * 4); camera.lookAt(-6, 2, -40);   // above the heads, into the cups
    }
    else { camera.position.set(30 - lt * 2, 26, 22); camera.lookAt(0, 0, -30); }
    camera.aspect = 16 / 9; camera.updateProjectionMatrix();
    toon.draw(scene, camera, { mode: p.mode, fog: 0.75, inkA: INK.violet, accentC: INK.mint, glow: INK.pink, glow2: INK.mint,
      fillLight: light ? 0.35 : 0.25, lineW: light ? 1.3 : 1.4,
      fogC: light ? [0.02, 0.01, 0.04] : INK.pink, ...p.toon }, t, A);
  },
};
