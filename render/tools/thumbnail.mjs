// Video thumbnail: one frame of the film with the title card's lettering in place of the shot's own type.
//   node tools/thumbnail.mjs --t 24.5 --w 3840 --h 2160 --out ../out/thumbnail_4k.png
import { chromium } from 'playwright-core';
import { serve } from './serve.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : '1']);
  return acc;
}, []));
const W = Number(args.w || 3840), H = Number(args.h || 2160);
const PORT = 8900 + Math.floor(Math.random() * 100);
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

// drawn in the 1920×1080 design space, like every type layer in the film
function lettering(ty) {
  const c = ty.ctx;
  const PAPER = 'rgba(243,239,230,1)', ORANGE = 'rgba(255,90,31,0.95)', PALE = 'rgba(156,203,255,1)', PINK = 'rgba(255,72,176,1)';
  // ink wash from the left, under the type, so it reads over the console screens
  const g = c.createLinearGradient(0, 0, 1060, 0);
  g.addColorStop(0, 'rgba(11,11,20,0.88)'); g.addColorStop(0.5, 'rgba(11,11,20,0.62)'); g.addColorStop(1, 'rgba(11,11,20,0)');
  c.fillStyle = g; c.fillRect(0, 0, 1060, 1080);
  // RARE / EARTH, the title card's condensed serif on its orange plate
  // sized so EARTH ends left of her face (x < ~880)
  ty.font('NotoSerifDisplay', 255, 900, 'extra-condensed');
  ty.plateText('RARE', 84, 400, PAPER, ORANGE, [8, 7]);
  ty.plateText('EARTH', 84, 625, PAPER, ORANGE, [8, 7]);
  ty.font('NotoSansSC', 60, 900); c.fillStyle = PALE; c.fillText('稀有地球', 92, 725);
  const wz = c.measureText('稀有地球').width;
  ty.font('Unbounded', 40, 800); c.fillStyle = PINK; c.fillText('Уникальная Земля', 92 + wz + 32, 721);
  // credits, from the end card
  ty.font('JetBrainsMono', 27, 500); c.fillStyle = 'rgba(243,239,230,0.88)';
  c.fillText('written by Jade Q Wang', 94, 815);
  c.fillText('and Charlie van Norman', 94, 853);
  c.fillText('Robot Ninja Apocalypse  ·  SETI, 2011', 94, 891);
}

const server = await serve(PORT);
const browser = await chromium.launch({ executablePath: CHROME,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-web-security'] });
try {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${PORT}/index.html?w=${W}&h=${H}`);
  await page.waitForFunction(() => window.__ready !== undefined, null, { timeout: 60000 });
  await page.evaluate(() => window.__ready);
  await page.evaluate(`window.__typeOverride = ${args.plain ? 'null' : lettering.toString()}; window.__typeOverride = window.__typeOverride || (() => {});`);
  for (const t of String(args.t || '24.5').split(',').map(Number)) {
    await page.evaluate((tt) => window.renderAt(tt), t);
    const out = (args.out || '../out/thumbnail_4k.png').replace('{t}', t.toFixed(3));
    await page.screenshot({ path: out, clip: { x: 0, y: 0, width: W, height: H } });
    console.log('wrote', out);
  }
} finally {
  await browser.close();
  server.close();
}
