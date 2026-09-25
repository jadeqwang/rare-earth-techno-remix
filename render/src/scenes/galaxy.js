// THE GALAXY: a spiral of stars; in 'web' view, links between civilizations light up outward from Earth
// until the whole disc is talking (how could we be alone).
import * as THREE from 'three';
import { rng, clamp, smooth, easeInOutCubic, range, lerp, INK } from '../util.js';
import { skyMaterial, setSky } from './sky.js';
import { C2D } from '../c2d.js';
let c2d = null, edgeList = [], nodeReveal = [];

let scene, camera, points, links, linkMat, starMat, earthPos, civ = [];
const N = 42000;

function build() {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.1, 4000);
  const R = rng(2011);
  const pos = new Float32Array(N * 3), col = new Float32Array(N * 3), size = new Float32Array(N);
  const gauss = () => { let u = 0, v = 0; while (u === 0) u = R(); v = R(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  for (let i = 0; i < N; i++) {
    let x, y, z, c;
    if (i < N * 0.18) { // bulge
      const r = Math.abs(gauss()) * 55; const a = R() * 6.283; const e = gauss() * 0.4;
      x = Math.cos(a) * r; z = Math.sin(a) * r * 0.9; y = gauss() * 18 * Math.exp(-r / 80);
      c = [1.0, 0.86, 0.62];
    } else { // two log-spiral arms + disc
      const arm = R() < 0.5 ? 0 : Math.PI;
      const r = 40 + Math.pow(R(), 0.8) * 420;
      const a = arm + Math.log(r / 40) / 0.28 + gauss() * (0.22 + 60 / r);
      x = Math.cos(a) * r + gauss() * 10; z = Math.sin(a) * r + gauss() * 10; y = gauss() * 6;
      const blue = R();
      c = blue < 0.6 ? [0.62, 0.78, 1.0] : blue < 0.85 ? [1.0, 0.95, 0.9] : [1.0, 0.6, 0.75];
    }
    pos.set([x, y, z], i * 3); col.set(c, i * 3); size[i] = 0.6 + Math.pow(R(), 6) * 3.5;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setAttribute('size', new THREE.BufferAttribute(size, 1));
  starMat = new THREE.ShaderMaterial({
    uniforms: { scale: { value: 1 }, bright: { value: 1 } },
    vertexShader: `attribute float size; attribute vec3 color; varying vec3 vC; uniform float scale;
      void main(){ vC = color; vec4 mv = modelViewMatrix * vec4(position, 1.); gl_PointSize = clamp(size * scale * 300. / -mv.z, 1., 14.); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec3 vC; uniform float bright; void main(){ vec2 d = gl_PointCoord - .5; float a = exp(-dot(d, d) * 18.); gl_FragColor = vec4(vC * a * .55 * bright, 1.); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  points = new THREE.Points(g, starMat);
  scene.add(points);
  // civilizations (a few hundred stars) and the links between them
  earthPos = new THREE.Vector3(Math.cos(2.2) * 260, 0, Math.sin(2.2) * 260);
  civ = [earthPos.clone()];
  for (let i = 0; i < 640; i++) {
    const k = Math.floor(R() * N * 0.82 + N * 0.18);
    civ.push(new THREE.Vector3(pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2]));
  }
  // links: a Euclidean minimum spanning tree (so every civilization is reachable from Earth) plus 2 nearest neighbours
  const n = civ.length, edges = [], seen = new Set();
  const addE = (a, b) => { const key = a < b ? a * 4096 + b : b * 4096 + a; if (seen.has(key)) return; seen.add(key); edges.push([a, b, civ[a].distanceTo(civ[b])]); };
  const inT = new Array(n).fill(false), best = new Array(n).fill(Infinity), from = new Array(n).fill(-1);
  best[0] = 0;
  for (let it = 0; it < n; it++) {
    let u = -1; for (let i = 0; i < n; i++) if (!inT[i] && (u < 0 || best[i] < best[u])) u = i;
    inT[u] = true; if (from[u] >= 0) addE(from[u], u);
    for (let v = 0; v < n; v++) if (!inT[v]) { const d = civ[u].distanceTo(civ[v]); if (d < best[v]) { best[v] = d; from[v] = u; } }
  }
  for (let a = 0; a < n; a++) {
    const near = civ.map((v, b) => [b, v.distanceTo(civ[a])]).filter(([b]) => b !== a).sort((x, y) => x[1] - y[1]).slice(0, 2);
    for (const [b] of near) addE(a, b);
  }
  // reveal order = shortest-path distance from Earth through the graph (Dijkstra, O(n^2) is fine here)
  const adj = Array.from({ length: n }, () => []);
  for (const [a, b, d] of edges) { adj[a].push([b, d]); adj[b].push([a, d]); }
  const dist = new Array(n).fill(Infinity), done = new Array(n).fill(false); dist[0] = 0;
  for (let it = 0; it < n; it++) {
    let u = -1; for (let i = 0; i < n; i++) if (!done[i] && (u < 0 || dist[i] < dist[u])) u = i;
    done[u] = true; for (const [v, d] of adj[u]) if (dist[u] + d < dist[v]) dist[v] = dist[u] + d;
  }
  const maxD = Math.max(...dist);
  for (const e of edges) e.push(Math.min(dist[e[0]], dist[e[1]]) / maxD);
  edgeList = edges;
  nodeReveal = dist.map((d) => d / maxD);
  const lp = [], lr = [];
  for (const [a, b] of edges) { lp.push(civ[a].x, civ[a].y, civ[a].z, civ[b].x, civ[b].y, civ[b].z); const r = Math.min(dist[a], dist[b]) / maxD; lr.push(r, r); }
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
  lg.setAttribute('reveal', new THREE.Float32BufferAttribute(lr, 1));
  linkMat = new THREE.ShaderMaterial({
    uniforms: { prog: { value: 0 }, col: { value: new THREE.Color(...INK.yellow) }, col2: { value: new THREE.Color(...INK.mint) } },
    vertexShader: `attribute float reveal; varying float vR; void main(){ vR = reveal; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
    fragmentShader: `uniform float prog; uniform vec3 col; uniform vec3 col2; varying float vR;
      void main(){ float on = smoothstep(vR, vR + .04, prog); float head = exp(-pow((prog - vR) * 25., 2.)); gl_FragColor = vec4(mix(col2, col, head) * (on * .55 + head * 1.5), 1.); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  links = new THREE.LineSegments(lg, linkMat);
  scene.add(links);
}

export const galaxy = {
  init(ctx) { build(); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    const e = ctx.engine;
    const sm = skyMaterial(e);
    setSky(sm.uniforms, { mode: 'light', band: 0.25, density: 0.7 }, ctx);
    e.pass(sm, e.rtScene);
    const view = p.view || 'bg';
    let prog = 0;
    if (view === 'web') {
      const k = clamp((t - p.t0) / (p.t1 - p.t0));
      const ez = easeInOutCubic(k);
      // start at Earth, pull back and tilt until the whole disc is in frame
      const dist = lerp(40, 1250, Math.pow(ez, 1.3));
      const tilt = lerp(0.25, 1.05, ez);
      const target = earthPos.clone().lerp(new THREE.Vector3(0, 0, 0), smooth(range(k, 0.1, 0.8)));
      camera.position.set(target.x + Math.sin(0.6 + k * 0.5) * dist * Math.cos(tilt), dist * Math.sin(tilt), target.z + Math.cos(0.6 + k * 0.5) * dist * Math.cos(tilt));
      camera.lookAt(target);
      prog = smooth(range(k, 0.08, 0.92)) * 1.05;
      starMat.uniforms.scale.value = 1.0;
    } else {
      // backdrop: tilted disc slowly rotating
      const a = t * 0.03;
      camera.position.set(Math.sin(a) * 900, 380, Math.cos(a) * 900);
      camera.lookAt(0, -40, 0);
      prog = view === 'title' ? 0 : 0.0;
    }
    links.visible = false; // drawn as glowing 2D strokes below
    linkMat.uniforms.prog.value = prog;
    starMat.uniforms.bright.value = 1 + ctx.audio.kick(t, 0.2) * 0.8;
    camera.aspect = 16 / 9; camera.updateProjectionMatrix();
    const r = e.renderer;
    r.autoClear = false;
    r.setRenderTarget(e.rtScene);
    r.clearDepth();
    r.render(scene, camera);
    r.autoClear = true;
    if (view === 'web') {
      if (!c2d) c2d = new C2D(e);
      const c = c2d.begin(null);
      c.globalCompositeOperation = 'lighter';
      const proj = (v) => { const q = v.clone().project(camera); return [(q.x * 0.5 + 0.5) * 1920, (1 - (q.y * 0.5 + 0.5)) * 1080, q.z]; };
      const P = civ.map(proj);
      const kick = ctx.audio.kick(t, 0.15);
      for (const pass of [0, 1]) {         // wide soft glow, then a crisp core
        for (const [a, b, , rv] of edgeList) {
          if (prog < rv) continue;
          const pa = P[a], pb = P[b];
          if (pa[2] > 1 || pb[2] > 1) continue;
          const head = Math.exp(-Math.pow((prog - rv) * 18, 2));
          const warm = head > 0.3;
          const al = pass === 0 ? 0.16 + 0.1 * kick : (warm ? 0.6 + 0.4 * head : 0.62 + 0.3 * kick);
          c.strokeStyle = warm ? `rgba(255,236,150,${al})` : `rgba(63,224,197,${al})`;
          c.lineWidth = pass === 0 ? 7 + head * 6 : 2.0 + head * 2.5;
          c.beginPath(); c.moveTo(pa[0], pa[1]); c.lineTo(pb[0], pb[1]); c.stroke();
        }
      }
      for (let i = 0; i < P.length; i++) {
        if (prog < nodeReveal[i] || P[i][2] > 1) continue;
        c.fillStyle = i === 0 ? 'rgba(156,203,255,1)' : 'rgba(255,245,210,0.9)';
        c.beginPath(); c.arc(P[i][0], P[i][1], i === 0 ? 7 + kick * 5 : 3.2 + kick * 2, 0, 7); c.fill();
      }
      c2d.end({ over: true });
    }
  },
};
