"""Check the existing musical beat grid against transients in the source audio."""
from pathlib import Path
import hashlib
import json

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, find_peaks, resample_poly
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
OUT = ROOT / "analysis"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = PROJECT / "audio/Rare_Earth_DDR.mp3"
original = json.loads((PROJECT / "render/data/audio.json").read_text())
y, sr = sf.read(SOURCE, dtype="float32", always_2d=True)
mono = resample_poly(y.mean(axis=1), 1, sr // 24000)
sr = 24000
# A short envelope lets us check the timing, rather than merely accepting the
# beat tracker's smoothed tempo estimate. Zero-phase filtering adds no delay.
low = sosfiltfilt(butter(4, [35, 160], fs=sr, btype="bandpass", output="sos"), mono)
env = np.sqrt(gaussian_filter1d(low * low, sr * .004))
flux = np.maximum(0, env - np.roll(env, int(.008 * sr)))
flux[:int(.008 * sr)] = 0
peaks, props = find_peaks(flux, distance=int(.22 * sr), prominence=.003)
times = peaks / sr
strength = props["prominences"]
grid = np.array([b["t"] for b in original["beats"]], float)
matches = []
for i, t in enumerate(grid):
    if not (54.5 <= t <= 124):
        continue
    choices = np.flatnonzero(np.abs(times - t) < .045)
    if not len(choices):
        continue
    k = choices[np.argmax(strength[choices])]
    if strength[k] < .012:
        continue
    matches.append(dict(beat=i, grid_s=float(t), transient_s=float(times[k]),
                        residual_ms=round(float(1000 * (times[k] - t)), 3),
                        strength=round(float(strength[k]), 5)))
# Envelope-rise peaks are a few ms after the waveform attack. Report that
# residual honestly; do not shift the grid to the maxima of a kick envelope.
residual = np.array([m["residual_ms"] for m in matches])
archived_kicks = [min(abs(grid-t))*1000 for t, strength in original["kicks"]
                  if t > 54 and min(abs(grid-t)) < .06]
anchors = list(range(0, len(grid), 4))
anchor_times = grid[anchors]
bpms = 240 / np.diff(anchor_times)
bpms = np.r_[bpms, bpms[-1]]
bar_grid = np.interp(np.arange(len(grid)), anchors, anchor_times)
# The last incomplete measure uses the last complete measure's tempo.
last = anchors[-1]
bar_grid[last:] = grid[last] + (np.arange(last, len(grid)) - last) * 60 / bpms[-1]
data = dict(
    source=str(SOURCE.relative_to(PROJECT)),
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    duration_s=len(y) / 48000,
    beat_zero_s=float(grid[0]),
    offset=-float(grid[0]),
    method="Existing instrumental beat grid; constant BPM per measure fitted to consecutive bar anchors; independently checked against low-band transients in original MP3.",
    bpms=[dict(beat=int(b), bpm=round(float(v), 9)) for b, v in zip(anchors, bpms)],
    beats=[dict(beat=i, time_s=round(float(t), 7)) for i, t in enumerate(bar_grid)],
    bpm_range=[round(float(min(bpms)), 3), round(float(max(bpms)), 3)],
    bar_interpolation_max_error_ms=round(float(max(abs(bar_grid-grid))*1000), 4),
    transient_check=dict(matched_beats=len(matches),
                         median_envelope_peak_delay_ms=round(float(np.median(residual)), 3),
                         p95_absolute_residual_ms=round(float(np.percentile(abs(residual),95)), 3),
                         max_absolute_residual_ms=round(float(max(abs(residual))), 3)),
    archived_kick_onset_check=dict(
        method="Post-drop archived kick onsets matched to nearest instrumental beat within 60 ms.",
        matched_onsets=len(archived_kicks),
        median_absolute_residual_ms=round(float(np.median(archived_kicks)),3),
        p95_absolute_residual_ms=round(float(np.percentile(archived_kicks,95)),3),
        max_absolute_residual_ms=round(float(max(archived_kicks)),3)),
    transient_matches=matches,
    sections=original["sections"],
)
(OUT / "timing.json").write_text(json.dumps(data, indent=2)+"\n")
print(json.dumps({k:data[k] for k in ["duration_s", "beat_zero_s", "bpm_range", "bar_interpolation_max_error_ms", "transient_check"]}, indent=2))
print("Measure anchors:")
for b, t in zip(anchors, anchor_times):
    print(f"{b//4:2d}: beat {b:3d}, {t:8.4f} s")
