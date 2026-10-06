"""Contact sheet of a plate's displayed frames for a shot (every drawing), full frame, with frame numbers."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/tmp/work/audit')
from shots import SHOTS, SEL, displayed
from PIL import Image, ImageDraw
CL = '/home/user/rare-earth-techno-remix/pipeline/base_clips'
def read(path):
    cap = cv2.VideoCapture(path); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(f)
    return fr
def sheet(shot, step=1, cols=6, scale=0.25, crop=None, src=None):
    clip = SHOTS[shot][0]
    fr = read(f"{CL}/{src or SEL[clip]['file']}")
    disp = displayed(shot, len(fr))
    fis = []
    for i, t, fi in disp:
        if not fis or fis[-1][1] != fi: fis.append((t, fi))
    fis = fis[::step]
    x0, y0, x1, y1 = crop or (0, 0, 1280, 720)
    w, h = int((x1-x0)*scale), int((y1-y0)*scale)
    rows = (len(fis)+cols-1)//cols
    im = Image.new('RGB', (cols*w, rows*h), (0,0,0)); d = ImageDraw.Draw(im)
    for k, (t, fi) in enumerate(fis):
        f = cv2.resize(fr[fi][y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_AREA)
        r, c = divmod(k, cols)
        im.paste(Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)), (c*w, r*h))
        d.rectangle([c*w, r*h, c*w+92, r*h+12], fill=(0,0,0)); d.text((c*w+2, r*h), f'{t:.2f} f{fi}', fill=(255,255,0))
    out = f'/tmp/work/audit/plates_{shot}.jpg'; im.save(out, quality=85); return out
if __name__ == '__main__':
    shot = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    crop = tuple(map(int, sys.argv[3].split(','))) if len(sys.argv) > 3 else None
    scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    print(sheet(shot, step, crop=crop, scale=scale))
