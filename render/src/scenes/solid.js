// Flat color (used for the blank / hard black frames).
import * as THREE from 'three';
let mat = null;
export const solid = {
  init(ctx) { mat = ctx.engine.shader(`uniform vec3 c; void main(){ fragColor = vec4(c, 1.); }`, { c: { value: new THREE.Color() } }); },
  async draw(ctx, shot, t, lt) {
    const p = typeof shot.p === 'function' ? shot.p(t, lt, ctx) : (shot.p || {});
    mat.uniforms.c.value.setRGB(...(p.color ?? [0, 0, 0]));
    ctx.engine.pass(mat, ctx.engine.rtScene);
  },
};
