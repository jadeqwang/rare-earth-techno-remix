// 3D -> SIGNAL PRINT. Renders a three.js scene into a G-buffer (tone, depth, accent, coverage) and stylizes
// it with the same inks as the rotoscope: halftone shading + ink contour lines (print) or neon edges (light).
import * as THREE from 'three';
import { INK } from './util.js';

export const GBUF_VERT = /* glsl */`
  varying vec3 vN; varying float vZ; varying vec3 vW;
  #ifdef USE_INSTANCING
  #endif
  void main(){
    vec4 wp = modelMatrix * vec4(position, 1.);
    #ifdef USE_INSTANCING
      wp = modelMatrix * instanceMatrix * vec4(position, 1.);
      vN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal);
    #else
      vN = normalize(mat3(modelMatrix) * normal);
    #endif
    vW = wp.xyz;
    vec4 vp = viewMatrix * wp;
    vZ = -vp.z;
    gl_Position = projectionMatrix * vp;
  }`;

export function gbufMaterial({ accent = 0, lightDir = [0.3, 0.8, 0.5], ambient = 0.18, doubleSide = true, toneMul = 1 } = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: GBUF_VERT,
    fragmentShader: /* glsl */`
      uniform vec3 lightDir; uniform float ambient; uniform float accent; uniform float far; uniform float toneMul;
      uniform vec3 camPos;
      varying vec3 vN; varying float vZ; varying vec3 vW;
      void main(){
        vec3 n = dot(vN, vN) > 1e-8 ? normalize(vN) : vec3(0., 1., 0.);
        if (!gl_FrontFacing) n = -n;
        float lam = max(0., dot(n, normalize(lightDir)));
        vec3 v = normalize(camPos - vW);
        float rim = pow(1. - max(0., dot(n, v)), 3.);
        float tone = clamp((ambient + (1. - ambient) * lam) * toneMul, 0., 1.);
        gl_FragColor = vec4(tone, clamp(vZ / far, 0., 1.), accent + rim * .001, 1.);
      }`,
    uniforms: { lightDir: { value: new THREE.Vector3(...lightDir) }, ambient: { value: ambient }, accent: { value: accent },
      far: { value: 400 }, toneMul: { value: toneMul }, camPos: { value: new THREE.Vector3() } },
    side: doubleSide ? THREE.DoubleSide : THREE.FrontSide,
  });
}

export class Toon3D {
  constructor(engine) {
    this.e = engine;
    this.gbuf = new THREE.WebGLRenderTarget(engine.W, engine.H, { type: THREE.HalfFloatType, depthBuffer: true, samples: 0 });
    this.mat = engine.shader(/* glsl */`
      uniform sampler2D tG; uniform vec2 res; uniform float S; uniform float mode; uniform float kick; uniform float time;
      uniform vec3 inkA; uniform vec3 inkLine; uniform vec3 paperC; uniform vec3 glow; uniform vec3 glow2; uniform vec3 accentC;
      uniform float cell; uniform float lineW; uniform float fillLight; uniform float fog; uniform vec3 fogC;
      void main(){
        vec2 px = vUv * res / S;
        vec2 tx = lineW / res;
        vec4 g = texture(tG, vUv);
        float cov = g.a;
        // edges from depth + tone discontinuities (cross kernel)
        vec4 gl = texture(tG, vUv - vec2(tx.x, 0.)), gr = texture(tG, vUv + vec2(tx.x, 0.));
        vec4 gd = texture(tG, vUv - vec2(0., tx.y)), gu = texture(tG, vUv + vec2(0., tx.y));
        float dz = abs(gl.g - gr.g) + abs(gd.g - gu.g);
        float dt = abs(gl.r - gr.r) + abs(gd.r - gu.r);
        float da = abs(gl.a - gr.a) + abs(gd.a - gu.a);
        float edge = clamp(smoothstep(.004, .02, dz) + smoothstep(.18, .4, dt) + da, 0., 1.);
        float depthFog = smoothstep(.0, 1., g.g) * fog;
        float acc = g.b;
        vec3 col; float a = max(cov, edge * .999);
        if (mode < .5) {
          float shade = clamp(1. - g.r, 0., 1.);
          vec3 c = paperC;
          c = overprint(c, inkA, halftone(px, shade * (1. - depthFog * .7), cell * (1. + kick * .1), .26));
          c = mix(c, fogC, depthFog * .6);
          c = overprint(c, accentC, acc);
          c = overprint(c, inkLine, edge * (1. - depthFog * .6));
          col = c;
        } else {
          // blueprint neon: thin lines that fade with distance, faint fill, bright accent points
          float near = 1. - smoothstep(.12, .62, g.g);
          vec3 c = paperC * .6 + glow * g.r * fillLight * cov * (.25 + .75 * near);
          c += mix(glow, glow2, acc) * edge * 1.1 * near;
          c += accentC * acc * (.4 + 1.4 * near);
          col = c;
          a = max(cov, edge * near);
        }
        fragColor = vec4(col, a);
      }`, {
      tG: { value: this.gbuf.texture }, res: { value: new THREE.Vector2(engine.W, engine.H) }, S: { value: engine.S },
      mode: { value: 0 }, kick: { value: 0 }, time: { value: 0 },
      inkA: { value: new THREE.Color(...INK.klein) }, inkLine: { value: new THREE.Color(...INK.ink) }, paperC: { value: new THREE.Color(...INK.paper) },
      glow: { value: new THREE.Color(...INK.pale) }, glow2: { value: new THREE.Color(...INK.yellow) }, accentC: { value: new THREE.Color(...INK.orange) },
      cell: { value: 6 }, lineW: { value: 1.2 }, fillLight: { value: 0.25 }, fog: { value: 0.5 }, fogC: { value: new THREE.Color(...INK.pale) },
    });
    this.mat.transparent = true;
  }

  // render `scene` with `camera`, stylize, and blend over engine.rtScene (which should already hold the sky)
  draw(scene, camera, p, t, audio) {
    const r = this.e.renderer;
    scene.traverse((o) => { if (o.material && o.material.uniforms && o.material.uniforms.camPos) o.material.uniforms.camPos.value.copy(camera.position); });
    r.setRenderTarget(this.gbuf);
    r.setClearColor(0x000000, 0);
    r.clear(true, true, true);
    r.render(scene, camera);
    r.setClearColor(0x000000, 1);
    const u = this.mat.uniforms;
    const light = p.mode === 'light';
    u.mode.value = light ? 1 : 0;
    u.kick.value = audio.kick(t); u.time.value = t;
    u.inkA.value.setRGB(...(p.inkA ?? INK.klein));
    u.inkLine.value.setRGB(...(p.inkLine ?? INK.ink));
    u.paperC.value.setRGB(...(p.paper ?? (light ? [0.02, 0.022, 0.04] : INK.paper)));
    u.glow.value.setRGB(...(p.glow ?? INK.pale));
    u.glow2.value.setRGB(...(p.glow2 ?? INK.yellow));
    u.accentC.value.setRGB(...(p.accentC ?? INK.orange));
    u.fogC.value.setRGB(...(p.fogC ?? (light ? [0.02, 0.022, 0.04] : INK.pale)));
    u.cell.value = p.cell ?? 6; u.lineW.value = p.lineW ?? 1.3; u.fillLight.value = p.fillLight ?? 0.25; u.fog.value = p.fog ?? 0.5;
    this.e.passOver(this.mat, this.e.rtScene);
  }
}
