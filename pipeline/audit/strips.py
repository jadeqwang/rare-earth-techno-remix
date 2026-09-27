"""Mouth strips from the RELEASED video: one cell per drawing (on twos), with the song time, the word being sung
and the vocal level at that moment. Green bar = voiced vocal (mouth should be open), grey = rest (should be closed)."""
import sys, json, os, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, '/tmp/work/audit')
from shots import SHOTS, SEL, displayed, plate_to_screen, word_at
import vocal
T, DB, VP, F0 = vocal.load()
REL = '/home/user/rare-earth-techno-remix/out/rare_earth_1080p.mp4'
FACES = json.load(open('/tmp/work/audit/faces.json'))
CL = '/home/user/rare-earth-techno-remix/pipeline/base_clips'
# manual mouth tracks for plates the cascade can't follow: (plate frame, cx, cy, face width)
MANUAL = json.load(open('/tmp/work/audit/manual_mouths.json')) if os.path.exists('/tmp/work/audit/manual_mouths.json') else {}

def release_frames(i0, i1, cache={}):
    key = (i0, i1)
    d = f'/tmp/work/audit/rel_{i0}_{i1}'
    if not os.path.exists(d):
        os.makedirs(d)
        subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-ss', f'{i0/24:.4f}', '-i', REL, '-frames:v', str(i1-i0),
                        '-start_number', str(i0), f'{d}/r_%05d.png'], check=True)
    return d

def mouth_track(clip, n):
    if clip in MANUAL:
        k = np.array(MANUAL[clip], float)
        return np.stack([np.interp(np.arange(n), k[:,0], k[:,c]) for c in (1,2,3)], 1)
    b = np.array(FACES[clip]['boxes'])
    return np.stack([b[:,0]+0.5*b[:,2], b[:,1]+0.655*b[:,3], b[:,2]], 1)

def vocal_at(t):
    j = np.searchsorted(T, t)
    j = min(len(T)-1, j)
    return DB[j], VP[j]

def strip(shot, per_row=12, cell=(150,112), out=None):
    clip, t0, t1 = SHOTS[shot][:3]
    n = FACES[clip]['n']
    disp = displayed(shot, n)
    i0, i1 = disp[0][0], disp[-1][0]+1
    d = release_frames(i0, i1)
    tr = mouth_track(clip, n)
    # one cell per drawing: the first release frame showing each plate frame; drawings are on twos
    cells = []
    seen = None
    for i, t, fi in disp:
        if fi == seen: continue
        seen = fi
        cells.append((i, t, fi))
    rows = int(np.ceil(len(cells)/per_row))
    CW, CH = cell
    EH = 56
    im = Image.new('RGB', (per_row*CW, rows*(CH+EH+16)+30), (20,20,24))
    dr = ImageDraw.Draw(im)
    lag = displayed.__globals__['lag_of'](shot)
    dr.text((4,4), f'{shot}  clip {clip}  {t0:.2f}-{t1:.2f}s  start {SEL[clip]["start"]}  lag {lag:+.3f}', fill=(255,255,0))
    mm = (T >= t0-0.5) & (T < t1+0.5); LO, HI = np.percentile(DB[mm], 5), np.percentile(DB[mm], 99)
    words = [(w['t'], w['w']) for L in displayed.__globals__['A']['lines'] for w in L['words']]
    for k, (i, t, fi) in enumerate(cells):
        fr = cv2.imread(f'{d}/r_{i:05d}.png')
        cx, cy, fw = tr[fi]
        X, Y, s = plate_to_screen(shot, t, cx, cy)
        w = 0.55*fw*s; h = w*CH/CW
        x0, y0 = int(X - w/2), int(Y - h*0.5)
        crop = np.zeros((int(h), int(w), 3), np.uint8)
        H_, W_ = fr.shape[:2]
        xs0, ys0 = max(0, x0), max(0, y0); xs1, ys1 = min(W_, x0+int(w)), min(H_, y0+int(h))
        if xs1 > xs0 and ys1 > ys0:
            crop[ys0-y0:ys1-y0, xs0-x0:xs1-x0] = fr[ys0:ys1, xs0:xs1]
        crop = cv2.resize(crop, (CW, CH), interpolation=cv2.INTER_AREA)
        r, c = divmod(k, per_row)
        x, y = c*CW, 30 + r*(CH+EH+16)
        im.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (x, y))
        dr.rectangle([x, y, x+44, y+11], fill=(0,0,0)); dr.text((x+2, y), f'{t:.2f}', fill=(255,255,255))
        # envelope under the cell: the cell's own display time [t, t+2/24)
        ey = y + CH + 2
        m = (T >= t) & (T < t + 2/24)
        if m.sum() > 1:
            xs = x + (T[m]-t)/(2/24)*CW
            ys = ey + EH - 4 - np.clip((DB[m]-LO)/(HI-LO), 0, 1)*(EH-8)
            pts = list(zip(xs, ys))
            for p0, p1, v in zip(pts[:-1], pts[1:], VP[m][1:]):
                dr.line([p0, p1], fill=(int(80+175*v), int(200*v)+40, 90), width=3)
        dr.line([x, ey+EH-4, x+CW, ey+EH-4], fill=(60,60,60))
        dr.line([x, ey, x, ey+EH], fill=(45,45,45))
        for wt, ww in words:
            if t <= wt < t + 2/24:
                xx = x + (wt - t)/(2/24)*CW
                dr.line([xx, ey, xx, ey+EH], fill=(255,200,60), width=2)
                dr.text((xx+2, ey+EH+1), ww[:12], fill=(255,200,60))
    out = out or f'/tmp/work/audit/strip_{shot}.jpg'
    im.save(out, quality=88)
    return out

if __name__ == '__main__':
    for s in (sys.argv[1:] or SHOTS):
        print(strip(s), flush=True)
