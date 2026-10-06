"""Forced alignment of each lyric line to the vocal stem with PocketSphinx (phone level)."""
import json, sys, numpy as np, librosa, soundfile as sf
from pocketsphinx import Decoder, Config
A = json.load(open('/home/user/rare-earth-techno-remix/render/data/audio.json'))
y, sr = librosa.load('/tmp/work/vocals.wav', sr=16000, mono=True)

def norm_words(text):
    import re
    ws = re.sub(r"[^a-zA-Z' -]", ' ', text).lower().replace('-', ' ').split()
    return ws

def align_line(t0, t1, text, pad=0.35):
    a, b = max(0, t0 - pad), t1 + pad
    seg = y[int(a*sr):int(b*sr)]
    seg = seg / (np.abs(seg).max() + 1e-9) * 0.9
    pcm = (seg * 32767).astype(np.int16).tobytes()
    dec = Decoder(samprate=16000, bestpath=False, lm=None, loglevel='FATAL')
    words = norm_words(text)
    dec.set_align_text(' '.join(words))
    dec.start_utt(); dec.process_raw(pcm, full_utt=True); dec.end_utt()
    if dec.hyp() is None: return None
    dec.set_alignment()
    dec.start_utt(); dec.process_raw(pcm, full_utt=True); dec.end_utt()
    al = dec.get_alignment()
    out = []
    if al is None: return None
    for w in al:
        ph = []
        for p in w:
            ph.append((p.name, a + p.start/100, a + (p.start+p.duration)/100))
        out.append((w.name, a + w.start/100, a + (w.start+w.duration)/100, ph))
    return out

if __name__ == '__main__':
    res = {}
    for L in A['lines']:
        r = align_line(L['t'], L['end'], L['text'])
        res[L['i']] = r
        print(L['i'], L['text'])
        if r:
            for w, s, e, ph in r:
                print(f'   {w:12s} {s:7.2f}-{e:7.2f}  ' + ' '.join(f'{p}@{ps:.2f}' for p, ps, pe in ph))
    json.dump(res, open('/tmp/work/audit/align.json', 'w'))
