import sys, numpy as np
sys.path.insert(0,'/tmp/work/audit')
import vocal
from shots import A
from PIL import Image, ImageDraw
T, DB, VP, F0 = vocal.load()
def plot(a, b, out, W=1800, H=260):
    im = Image.new('RGB', (W, H), (16,16,20)); d = ImageDraw.Draw(im)
    m = (T >= a) & (T < b)
    xs = (T[m]-a)/(b-a)*W
    ys = H-40 - np.clip((DB[m]+70)/50, 0, 1)*(H-80)
    for k in range(1, len(xs)):
        c = (int(60+195*VP[m][k]), int(220*VP[m][k]), 80)
        d.line([xs[k-1], ys[k-1], xs[k], ys[k]], fill=c, width=2)
    # f0 as dots
    for x, f, v in zip(xs, F0[m], VP[m]):
        if v > 0.5 and f > 0: d.point((x, H-40 - (np.log2(f/100)/3.5)*(H-80)), fill=(90,160,255))
    t = np.ceil(a*12)/12
    while t < b:
        x = (t-a)/(b-a)*W
        d.line([x, H-38, x, H-30], fill=(90,90,90))
        if abs(t*4 - round(t*4)) < 1e-6: d.text((x+1, H-28), f'{t:.2f}', fill=(150,150,150))
        t += 1/12
    for L in A['lines']:
        for w in L['words']:
            if a <= w['t'] < b:
                x = (w['t']-a)/(b-a)*W
                d.line([x, 0, x, H-40], fill=(255,200,60)); d.text((x+2, 4), w['w'], fill=(255,200,60))
    im.save(out)
if __name__ == '__main__':
    a, b = float(sys.argv[1]), float(sys.argv[2]); plot(a, b, sys.argv[3])
