// THE ARRAY: forty-two radio dishes that dance. Choreography is driven by the song's beat grid.
import * as THREE from 'three';
import { Toon3D, gbufMaterial } from '../toon3d.js';
import { skyMaterial, setSky } from './sky.js';
import { rng, clamp, smooth, easeOutBack, easeOutCubic, hash1, lerp, INK } from '../util.js';

let toon, scene, camera, dishes = [], built = false;

function buildDish(matDish, matMetal, matAccent) {
  const root = new THREE.Group();
  const ped = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.5, 4.2, 10), matMetal);
  ped.position.y = 2.1; root.add(ped);
  const az = new THREE.Group(); az.position.y = 4.4; root.add(az);
  const yoke = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.6, 0.8), matMetal); az.add(yoke);
  const el = new THREE.Group(); el.position.y = 0.6; az.add(el);
  // paraboloid dish, opening along +Y in the elevation frame
  const pts = []; const R = 3.0, f = 2.4;
  for (let i = 0; i <= 14; i++) { const r = (i / 14) * R; pts.push(new THREE.Vector2(Math.max(0.001, r), (r * r) / (4 * f))); }
  const dish = new THREE.Mesh(new THREE.LatheGeometry(pts, 36), matDish);
  dish.position.y = 0.2; el.add(dish);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(R, 0.09, 6, 48), matMetal);
  rim.rotation.x = Math.PI / 2; rim.position.y = 0.2 + (R * R) / (4 * f); el.add(rim);
  // feed: 3 struts to the focus + feed horn
  const focus = new THREE.Vector3(0, f + 0.2, 0);
  for (let k = 0; k < 3; k++) {
    const a = (k / 3) * Math.PI * 2;
    const rim = new THREE.Vector3(Math.cos(a) * R * 0.95, (R * R) / (4 * f) + 0.2, Math.sin(a) * R * 0.95);
    const len = rim.distanceTo(focus);
    const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, len, 5), matMetal);
    strut.position.copy(rim.clone().add(focus).multiplyScalar(0.5));
    strut.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), focus.clone().sub(rim).normalize());
    el.add(strut);
  }
  const horn = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.28, 0.6, 10), matAccent);
  horn.position.copy(focus); el.add(horn);
  return { root, az, el };
}

function build() {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(42, 16 / 9, 0.5, 500);
  const matDish = gbufMaterial({ ambient: 0.22, toneMul: 1.12 });
  const matMetal = gbufMaterial({ ambient: 0.15, toneMul: 0.85 });
  const matAccent = gbufMaterial({ ambient: 0.4, accent: 1 });
  const matGround = gbufMaterial({ ambient: 0.1, toneMul: 0.55, lightDir: [0.2, 1, 0.3] });
  for (const m of [matDish, matMetal, matAccent, matGround]) m.uniforms.far.value = 260;
  const R = rng(1420);
  const pts = [];
  while (pts.length < 42) {
    const x = (R() - 0.5) * 150, z = -(R() * 110) - 8;
    if (pts.every((p) => Math.hypot(p[0] - x, p[1] - z) > 14)) pts.push([x, z]);
  }
  pts.sort((a, b) => a[1] - b[1]);
  dishes = pts.map(([x, z], i) => {
    const d = buildDish(matDish, matMetal, matAccent);
    d.root.position.set(x, 0, z);
    d.i = i; d.x = x; d.z = z; d.seed = hash1(i * 3.7);
    scene.add(d.root);
    return d;
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(900, 900, 1, 1), matGround);
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  // distant ridge
  const ridge = new THREE.Shape();
  ridge.moveTo(-500, 0);
  for (let i = 0; i <= 80; i++) {
    const x = -500 + i * 12.5;
    const h = 28 + 22 * Math.sin(i * 0.23) + 12 * Math.sin(i * 0.71 + 1) + 7 * hash1(i);
    ridge.lineTo(x, h);
  }
  ridge.lineTo(500, 0); ridge.lineTo(-500, 0);
  const rm = new THREE.Mesh(new THREE.ShapeGeometry(ridge), gbufMaterial({ ambient: 0.06, toneMul: 0.4 }));
  rm.material.uniforms.far.value = 260;
  rm.position.set(0, -2, -240); scene.add(rm);
  built = true;
}

// choreography -> [azimuth, elevation] (radians) per dish
function pose(d, t, p, A) {
  const b = A.beat(t);
  const mode = p.choreo || 'sweep';
  const baseEl = 0.95;
  if (mode === 'sweep') {
    return [0.5 * Math.sin(t * 0.45) + 0.08 * Math.sin(t * 0.9 + d.seed), baseEl + 0.12 * Math.sin(t * 0.6)];
  }
  if (mode === 'snap' || mode === 'dance') {
    // every beat the whole array snaps to a new target (in unison); 'dance' adds canon + alternating groups
    const k = b.i;
    const tgt = (n) => [(hash1(n * 1.7) - 0.5) * 1.6, 0.55 + hash1(n * 2.9) * 0.9];
    const delay = mode === 'dance' ? clamp((d.x + 75) / 150) * 0.35 : 0;
    const ph = clamp((b.phase - delay) / 0.28);
    const e = easeOutBack(ph, 2.2);
    const [a0, e0] = tgt(k - 1), [a1, e1] = tgt(k);
    let az = lerp(a0, a1, e), el = lerp(e0, e1, e);
    if (mode === 'dance') {
      const grp = (d.i % 2) ? 1 : -1;
      az += grp * 0.35 * Math.sin(Math.PI * (k % 2 ? b.phase : 1 - b.phase));
      el += 0.12 * A.kick(t, 0.15) * grp;
    }
    return [az, el];
  }
  if (mode === 'snapup') {
    // pointed at the ground, then a wave snaps every dish up to the zenith: KEEP ON LOOKING
    const delay = (Math.hypot(d.x, d.z + 40) / 110) * 0.45;
    const ph = clamp((t - (p.t0 ?? 0) - delay) / 0.35);
    const e = easeOutBack(ph, 1.6);
    return [lerp(0.6 * (d.seed - 0.5), 0, e), lerp(-0.25, 1.52, e)];
  }
  if (mode === 'wave') {
    return [0.2 * Math.sin(t * 0.8), baseEl + 0.35 * Math.sin(t * 2.4 - d.x * 0.05)];
  }
  return [0, baseEl];
}

export const array = {
  init(ctx) { toon = new Toon3D(ctx.engine); build(); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const A = ctx.audio;
    // sky
    const sm = skyMaterial(ctx.engine);
    setSky(sm.uniforms, { mode: p.mode, band: 1.0, bandAngle: 0.35, density: 1.3, horizon: p.mode === 'light' ? 0.28 : 0.3, horizonAmt: 0.5,
      glowInk: p.mode === 'light' ? INK.klein : INK.orange, pan: [lt * 6, 0], ...(p.sky || {}) }, ctx);
    ctx.engine.pass(sm, ctx.engine.rtScene);
    // choreography
    for (const d of dishes) {
      const [az, el] = pose(d, t, p, A);
      d.az.rotation.y = az + (p.face ?? Math.PI); // dishes face the camera side so we see the bowls
      d.el.rotation.x = -(Math.PI / 2 - el); // el=pi/2 -> pointing up
    }
    // camera
    const cam = p.cam || 'low';
    if (cam === 'low') {
      camera.position.set(-6 + lt * 1.2, 2.2, 14 - lt * 2.0);
      camera.lookAt(8, 9, -60);
    } else if (cam === 'high') {
      camera.position.set(40 - lt * 3, 36, 30);
      camera.lookAt(0, 0, -50);
    } else if (cam === 'hero') {
      const a = lt * 0.12;
      camera.position.set(Math.sin(a) * 30, 5 + lt * 0.8, 20 + Math.cos(a) * 6);
      camera.lookAt(0, 12, -50);
    }
    camera.aspect = 16 / 9; camera.updateProjectionMatrix();
    toon.draw(scene, camera, { mode: p.mode, fog: 0.8, accentC: p.mode === 'light' ? INK.mint : INK.orange, glow: INK.pale,
      fillLight: 0.3, lineW: p.mode === 'light' ? 1.2 : 1.3, ...p.toon }, t, A);
  },
};
