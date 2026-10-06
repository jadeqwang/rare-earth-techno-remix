"""Every changed drawing as rendered: old release frame vs new render, mouth crops side by side (old above, new below)."""
import sys, json, glob, os, subprocess
import numpy as np, cv2
sys.path.insert(0, '/home/user/rare-earth-techno-remix/pipeline/sync')
sys.path.insert(0, '/tmp/work/audit')
import relip
from shots import plate_to_screen
NAME2SHOT = {'yearning':'yearning','listen':'listen','caught':'caught','blink':'blink','transit_eye':'transit_eye','keep_yagi':'keep_yagi',
             'vision':'vision','vision2':'vision2','care2':'care2','listen2':'listen2','caught2':'caught2','blinkdance':'blinkdance','own':'own'}
OLD = '/home/user/rare-earth-techno-remix/out/rare_earth_1080p.mp4'
NEWDIR = sys.argv[1] if len(sys.argv) > 1 else '/tmp/work/frames_rel'
items = []
for f in sorted(glob.glob('/tmp/work/relip/sd*_relip.json')):
    key = os.path.basename(f).split('_')[0]
    L = json.load(open(f))
    spec = relip.PLATES[key]
    P = relip.Plate(spec)
    for name, win, start, lag in spec['shots']:
        for r in L['shots'][name]:
            if r['kept'] or r.get('how') == 'no clean fix, kept': continue
            t = r['t'] + 1e-4
            i = int(np.ceil(t * 24 - 1e-6))           # first release frame showing this drawing
            items.append((name, key, r, i, P.mouth_at(r['frame']), P.tr[r['frame']][2]))
idx = sorted(set(it[3] for it in items))
os.makedirs('/tmp/work/audit/oldf', exist_ok=True)
need = [i for i in idx if not os.path.exists(f'/tmp/work/audit/oldf/{i:05d}.png')]
if need:
    sel = '+'.join(f'eq(n\\,{i})' for i in need)
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', OLD, '-vf', f"select='{sel}'", '-vsync', '0',
                    '/tmp/work/audit/oldf/tmp_%05d.png'], check=True)
    for k, i in enumerate(need): os.rename(f'/tmp/work/audit/oldf/tmp_{k+1:05d}.png', f'/tmp/work/audit/oldf/{i:05d}.png')
items = [it for it in items if os.path.exists(f"{NEWDIR}/f_{it[3]:05d}.jpg")]
cells = []
for name, key, r, i, (mx, my), d in items:
    t = i / 24
    X, Y, s = plate_to_screen(NAME2SHOT[name], t, mx, my)
    w = 1.3 * d * s; h = 0.9 * w
    x0, y0 = int(X - w / 2), int(Y - h * 0.55)
    pair = []
    for img in (cv2.imread(f'/tmp/work/audit/oldf/{i:05d}.png'), cv2.imread(f'{NEWDIR}/f_{i:05d}.jpg')):
        H, W = img.shape[:2]
        c = np.zeros((int(h), int(w), 3), np.uint8)
        xs0, ys0, xs1, ys1 = max(0, x0), max(0, y0), min(W, x0 + int(w)), min(H, y0 + int(h))
        c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0] = img[ys0:ys1, xs0:xs1]
        pair.append(cv2.resize(c, (170, 153), interpolation=cv2.INTER_AREA))
    c = np.concatenate(pair, 0)
    cv2.rectangle(c, (0, 0), (100, 12), (0, 0, 0), -1)
    cv2.putText(c, f"{name[:8]} {t:.2f} w{r['want']:.1f}", (2, 10), 0, 0.33, (0, 255, 255), 1)
    cells.append(c)
while len(cells) % 10: cells.append(np.zeros_like(cells[0]))
rows = [np.concatenate(cells[k:k + 10], 1) for k in range(0, len(cells), 10)]
for part in range(0, len(rows), 5):
    out = f'/tmp/work/audit/final_{part // 5}.jpg'
    cv2.imwrite(out, np.concatenate(rows[part:part + 5], 0), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out)
print(len(items), 'changed drawings')
