"""Spectrogram of the vocal stem with envelope, PocketSphinx phones and word labels, for track reading."""
import sys, json, numpy as np, librosa, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, '/tmp/work/audit')
import vocal
T, DB, VP, F0 = vocal.load()
AL = json.load(open('/tmp/work/audit/align.json'))
y, sr = librosa.load('/tmp/work/vocals.wav', sr=16000, mono=True)
def view(a, b, out, W=1800):
    seg = y[int(a*sr):int(b*sr)]
    S = librosa.amplitude_to_db(np.abs(librosa.stft(seg, n_fft=1024, hop_length=80)), ref=np.max)
    S = S[:int(5000/(sr/1024))]          # 0..5 kHz
    img = np.clip((S + 70) / 70, 0, 1)
    img = (cv2.applyColorMap((img * 255).astype(np.uint8), cv2.COLORMAP_MAGMA))[::-1]
    H = 300
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((H + 200, W, 3), np.uint8); canvas[:H] = img
    im = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)); d = ImageDraw.Draw(im)
    X = lambda t: (t - a) / (b - a) * W
    # envelope
    m = (T >= a) & (T < b); mm = (T >= a-1) & (T < b+1)
    lo, hi = np.percentile(DB[mm], 5), np.percentile(DB[mm], 99.5)
    pts = [(X(t), H + 95 - np.clip((v - lo) / (hi - lo), 0, 1) * 90) for t, v in zip(T[m], DB[m])]
    d.line(pts, fill=(255, 255, 255), width=2)
    for t, v in zip(T[m], VP[m]):
        d.point((X(t), H + 100 - v * 10), fill=(90, 220, 90))
    # frame grid (24 fps) and time labels
    t = np.ceil(a * 24) / 24
    while t < b:
        x = X(t); k = int(round(t * 24))
        d.line([x, H, x, H + 8 + (6 if k % 2 == 0 else 0)], fill=(120, 120, 120))
        if k % 6 == 0: d.text((x + 1, H + 102), f'{t:.2f}', fill=(170, 170, 170))
        t += 1 / 24
    # phones
    for li, words in AL.items():
        if not words: continue
        for w, s, e, ph in words:
            if e < a or s > b: continue
            if w == '<sil>':
                d.rectangle([X(s), H + 120, X(e), H + 128], fill=(60, 60, 90)); continue
            d.line([X(s), 0, X(s), H + 150], fill=(255, 210, 60), width=1)
            d.text((X(s) + 2, H + 150), w, fill=(255, 210, 60))
            for p, ps, pe in ph:
                d.line([X(ps), H + 118, X(ps), H + 145], fill=(120, 200, 255))
                d.text((X(ps) + 2, H + 130), p, fill=(120, 200, 255))
    im.save(out)
if __name__ == '__main__':
    view(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3])
