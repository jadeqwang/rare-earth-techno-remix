"""Sound design layer for RARE EARTH.

The song itself is untouched. Everything here sits where the track is quiet (the intro, the "( )" blank,
and a short tail after the last note), so it frames the song instead of competing with it:

  0.0 - 3.4 s   receiver static on the Sutro dish, three star-blink pings, and a radio voice: "Still listening."
  61.03-61.45   the blank: the signal drops out into static ("and now we're (     )")
  after 127.96  a data burst, then the reply from 217 light-years: "Still here."

Voices are ElevenLabs v3 (through Cloudflare's unified model catalog, see gen.py); static, pings and the data
burst are synthesized here. Every processed voice is checked for intelligibility with Whisper before mixing.

  python3 pipeline/sound_design.py            # writes /tmp/work/sfx/Rare_Earth_DDR_sfx.wav (song + layer) and the stem
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
import gen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = "/tmp/work/sfx"
SONG = os.path.join(ROOT, "audio", "Rare_Earth_DDR.mp3")
SR = 44100
TAIL = 129.6            # video length: the song (127.96 s) plus the reply

VOICES = {
    # name: (voice_id, text)   — ElevenLabs premade voices
    "listen": ("XB0fDUnXU5powFXDhCwa", "Still listening."),
    "here": ("XB0fDUnXU5powFXDhCwa", "Still here."),
    "here_w": ("XB0fDUnXU5powFXDhCwa", "[whispers] Still here."),
}


def tts(name):
    path = os.path.join(WORK, f"v_{name}.mp3")
    if not os.path.exists(path):
        vid, text = VOICES[name]
        st, d = gen.run_sync("elevenlabs/eleven-v3", {"text": text, "voice_id": vid, "output_format": "mp3_44100_128"})
        url = d["result"]["result"]["audio"]
        open(path, "wb").write(urllib.request.urlopen(url, timeout=60).read())
    y, _ = librosa.load(path, sr=SR, mono=True)
    return trim(y)


def trim(y, db=-45):
    e = np.abs(y) > 10 ** (db / 20)
    idx = np.where(e)[0]
    return y[max(0, idx[0] - 200): idx[-1] + 2000] if len(idx) else y


def whisper_text(y):
    tmp = os.path.join(WORK, "_check.wav")
    sf.write(tmp, y / (np.max(np.abs(y)) + 1e-9) * 0.8, SR)
    mp3 = tmp.replace(".wav", ".mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, mp3], check=True)
    st, d = gen.run_sync("@cf/openai/whisper-large-v3-turbo", {"audio": base64.b64encode(open(mp3, "rb").read()).decode()})
    return ((d or {}).get("result") or {}).get("text", "").strip()


def bp(y, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), y)


def env(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    if a: e[:a] = np.linspace(0, 1, a) ** 2
    if r: e[-r:] = np.linspace(1, 0, r) ** 2
    return e


def rms_db(y):
    return 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12)


def at_db(y, db):
    return y * 10 ** ((db - rms_db(y)) / 20)


rng = np.random.default_rng(1420)


def static(dur, lo=700, hi=7000):
    n = int(dur * SR)
    w = rng.standard_normal(n)
    s = bp(w, lo, hi)
    # slow receiver wander + sparse crackle
    wob = 1 + 0.35 * np.sin(np.linspace(0, dur * 2 * np.pi * 0.7, n)) * np.sin(np.linspace(0, dur * 2 * np.pi * 0.13, n))
    s *= wob
    cr = np.zeros(n)
    for i in rng.integers(0, n, int(dur * 9)):
        k = rng.integers(20, 120)
        cr[i:i + k] += rng.standard_normal(min(k, n - i)) * rng.uniform(1.5, 4)
    return s + bp(cr, 1500, 9000)


def ping(f0=2840.0, dur=0.09):
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + 0.25 * np.exp(-t * 60))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 38) * (1 - np.exp(-t * 900))


def click(dur=0.012):
    t = np.arange(int(dur * SR)) / SR
    return bp(rng.standard_normal(len(t)), 800, 5000) * np.exp(-t * 500)


def radio(y, drive=2.2):
    y = bp(y, 320, 3300, 4)
    y = np.tanh(y / (np.max(np.abs(y)) + 1e-9) * drive)
    return y


def data_burst(dur=0.42):
    # FSK-like chirps: the reply's carrier arriving before the words
    n = int(dur * SR)
    t = np.arange(n) / SR
    sym = 0.018
    freqs = np.where(rng.random(int(dur / sym) + 1) > 0.5, 1800.0, 2600.0)
    f = freqs[(t / sym).astype(int)]
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.01, 0.05)
    return bp(y, 500, 5000)


def alien(y):
    # the reply: two copies of the voice pitched apart, ring-modulated slightly, a long echo — still intelligible
    a = librosa.effects.pitch_shift(y, sr=SR, n_steps=-4)
    b = librosa.effects.pitch_shift(y, sr=SR, n_steps=3) * 0.45
    n = max(len(a), len(b))
    v = np.zeros(n); v[:len(a)] += a; v[:len(b)] += b
    t = np.arange(n) / SR
    v = v * (0.8 + 0.2 * np.sin(2 * np.pi * 38 * t))
    v = bp(v, 260, 4800)
    out = np.zeros(n + int(1.2 * SR))
    for k, (d, g) in enumerate([(0, 1.0), (0.23, 0.42), (0.46, 0.2), (0.69, 0.09)]):
        i = int(d * SR); out[i:i + n] += v * g
    return out


def place(dst, y, t, db, peak=0.6):
    i = int(t * SR)
    y = at_db(y, db)
    pk = np.max(np.abs(y))
    if pk > peak: y = y * (peak / pk)          # headroom: nothing in the layer peaks above -4.4 dBFS
    j = min(len(dst), i + len(y))
    dst[i:j] += y[: j - i]


def main():
    os.makedirs(WORK, exist_ok=True)
    song, _ = librosa.load(SONG, sr=SR, mono=False)
    if song.ndim == 1: song = np.stack([song, song])
    n = int(TAIL * SR)
    layer = np.zeros(n)

    # --- cold open: receiver static under the intro, pings on the star blinks, the operator's voice
    st = static(3.5) * env(int(3.5 * SR), 0.25, 1.1)
    place(layer, st, 0.0, -36)
    for tp in (0.55, 2.15, 2.75):
        place(layer, ping(), tp, -33)
    v = tts("listen")
    rv = radio(v)
    print("listen:", repr(whisper_text(rv)))
    place(layer, click(), 0.84, -30)
    place(layer, rv, 0.88, -25)
    place(layer, click(), 0.88 + len(rv) / SR + 0.02, -30)

    # --- the blank: signal lost
    bl = static(0.42, 1000, 8000)
    gate = (np.floor(np.arange(len(bl)) / SR * 26) % 2 == 0).astype(float) * 0.6 + 0.4
    place(layer, bl * gate * env(len(bl), 0.02, 0.0), 61.03, -27)

    # --- the reply, after the song's last note
    place(layer, data_burst(), 127.55, -31)
    h = tts("here")
    hw = tts("here_w")
    m = max(len(h), len(hw)); vv = np.zeros(m); vv[:len(h)] += h; vv[:len(hw)] += 0.6 * hw
    rep = alien(vv)
    print("here:", repr(whisper_text(rep)))
    place(layer, rep, 128.02, -22.5)
    place(layer, static(1.6, 900, 6000) * env(int(1.6 * SR), 0.3, 0.9), 127.9, -40)

    # mix: song untouched, padded to the tail; the layer centred with a touch of width
    mix = np.zeros((2, n))
    mix[:, : song.shape[1]] += song[:, :n]
    wide = np.roll(layer, int(0.004 * SR))
    mix[0] += layer; mix[1] += 0.85 * layer + 0.15 * wide
    peak = np.max(np.abs(mix))
    if peak > 0.99: mix *= 0.99 / peak
    sf.write(os.path.join(WORK, "Rare_Earth_DDR_sfx.wav"), mix.T, SR, subtype="PCM_16")
    sf.write(os.path.join(WORK, "sfx_stem.wav"), layer, SR)
    print("wrote", os.path.join(WORK, "Rare_Earth_DDR_sfx.wav"), mix.shape[1] / SR, "s; peak", round(float(peak), 3))


if __name__ == "__main__":
    main()
