// Scene registry. Each scene: { init?(ctx), draw(ctx, shot, t, lt) } rendering into engine.rtScene.
import { sky } from './sky.js';
import { roto } from './roto.js';
import { solid } from './solid.js';
import { array } from './array.js';
import { earth } from './earth.js';
import { dot, zoom } from './dot.js';
import { waterfall, wow, star, transit, mutual } from './data.js';
import { planet, otherworld } from './etz.js';
import { petals } from './petals.js';
import { galaxy } from './galaxy.js';
import { drake, brutal, journey, split, endcard } from './inserts.js';
import { burst } from './burst.js';

export const SCENES = { sky, roto, solid, array, earth, dot, zoom, waterfall, wow, star, transit, mutual, planet, otherworld,
  petals, galaxy, drake, brutal, journey, split, endcard, burst };
