"""Vocal activity at 100 Hz: log RMS (dB) + pYIN voicing prob, cached."""
import os, numpy as np, librosa
from scipy.ndimage import gaussian_filter1d
CACHE = '/tmp/work/audit/vocal_100hz.npz'
def load():
    if os.path.exists(CACHE):
        d = np.load(CACHE); return d['t'], d['db'], d['vp'], d['f0']
    y, sr = librosa.load('/tmp/work/vocals.wav', sr=16000, mono=True)
    hop = 160
    rms = librosa.feature.rms(y=y, frame_length=640, hop_length=hop, center=True)[0]
    f0, _, vp = librosa.pyin(y, fmin=120, fmax=1100, sr=sr, frame_length=1024, hop_length=hop)
    n = min(len(rms), len(vp))
    t = np.arange(n) * hop / sr
    db = 20*np.log10(rms[:n] + 1e-6)
    np.savez(CACHE, t=t, db=db, vp=np.nan_to_num(vp[:n]), f0=np.nan_to_num(f0[:n]))
    return t, db, np.nan_to_num(vp[:n]), np.nan_to_num(f0[:n])
if __name__ == '__main__':
    t, db, vp, f0 = load(); print(len(t), db.max(), db.min())
