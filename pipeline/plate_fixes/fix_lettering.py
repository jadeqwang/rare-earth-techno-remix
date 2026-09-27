"""Set the character sheet's lettering on DOT's jacket in the base clips (docs/PROCESS.md §3d).

The Seedance takes invented their own lettering. The sheet (design/dot_character_sheet.jpg) has RARE EARTH on
the back of the jacket and a 1420 / MHz patch on the left sleeve; the plates read "PACE EARTH" (sd04) and
"D20 IHz" or "TA20 DIIz" on the patch (sd04, sd05, sd13). For each affected clip this script
  1. tracks the lettering through every frame: a patch by fitting an ellipse to its dark ring (ringtrack.py) and
     registering the in-plane rotation of its contents against a reference frame; the back lettering by
     fitting the pale-blue dot above it as a circle and measuring the old line under it,
  2. paints the old letters out (Telea inpainting of the dark strokes only, so fabric shading survives),
  3. sets the new lettering in Archivo, mapped into the plate through the tracked ellipse or line,
and writes <clip>_lettering.mp4 next to the original in pipeline/base_clips/. selects.json points the shots at
the fixed clips; extract_selects.py rebuilds their rotoscope guides. The renderer redraws the lettering as ink
like everything else in the plate.

  python3 pipeline/plate_fixes/fix_lettering.py [sd04 sd05 sd13] [--preview DIR]
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lettering import (font, set_lines, warp_layer, composite, paint_out, paint_out_specks, fill_patch, stroke_ink,
                       ellipse_region, patch_matrix, canonical_disc, disc_rotation)
from ringtrack import track as track_ring

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HERE, '..', 'base_clips')

# the patch lettering, as on the sheet: 1420 over MHz, heavy grotesque, centred in the ring.
# (text, Archivo weight, Archivo width, cap height, centre, tracking); the last three in ring radii. MHz is set
# wider so the M keeps its V once the renderer traces the plate's edges.
PATCH_LINES = [('1420', 800, 74, 0.42, -0.25, 0.02), ('MHz', 800, 96, 0.38, 0.29, 0.02)]
PATCH_BOLD = 0.006
# the back, as on the sheet: RARE EARTH in spaced, medium-weight caps under the pale-blue dot
BACK_FONT = ('Archivo-VF.ttf', 720, 112)
BACK_TEXT = 'RARE EARTH'

FIXES = {
    # sd04 (pullback): seen from behind; the lettering under the dot, and the patch on her left sleeve (image right).
    # Both shrink to a few pixels as the camera pulls out, so the fixes stop once they are sub-pixel.
    'sd04': {'src': 'sd04_wide_pullback__3dd548770f.mp4',
             'back': [{'frames': (0, 34)}],
             'patches': [{'ref': 0, 'init': [783.6, 457.5, 17.5, 28.5, 2.899], 'beta': 0.0, 'hw': 3.0, 'scale': 0.86,
                          'frames': (0, 26), 'dot_after': 20, 'fill': True, 'ink': 'ring', 'bold': 0.02}]},
    # sd13 (caught2): the patch faces the camera, lettering level at frame 0. Under the beam the plate washes the
    # lettering out to mid-grey, and this patch is small: heavier, darker, wider-set lettering prints as ink
    'sd13': {'src': 'sd13_caught_reply__935323d481.mp4',
             'patches': [{'ref': 0, 'init': [885, 544, 29.5, 37.5, 2.778], 'beta': 0.0, 'ink': 'ring', 'ink_scale': 0.35,
                          'bold': 0.01, 'lines': [('1420', 850, 66, 0.45, -0.26, 0.02), ('MHz', 750, 108, 0.39, 0.30, 0.03)]}]},
    # sd05 (caught): the arm is raised to the headphones; the patch is tilted with it
    'sd05': {'src': 'sd05_console_caught__ba8af2ae02.mp4',
             'patches': [{'ref': 40, 'init': [1095.8, 475.3, 26.6, 42.2, 2.255], 'beta': 20.0, 'fill': True}]},
}


def read_clip(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok: break
        frames.append(f)
    return frames


def write_clip(frames, path, fps=24):
    h, w = frames[0].shape[:2]
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                          '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'slow',
                          '-crf', '16', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError('ffmpeg failed for ' + path)


def smooth_track(vals, sigma=1.5):
    v = np.array(vals, float)
    return gaussian_filter1d(median_filter(v, size=5, mode='nearest'), sigma, mode='nearest')


def fix_patch(frames, spec, log):
    lo, hi = spec.get('frames', (0, len(frames)))
    out = list(frames)
    out[lo:hi] = fix_patch_range(frames[lo:hi], {**spec, 'ref': spec['ref'] - lo}, log, lo)
    return out


def fix_patch_range(frames, spec, log, first=0):
    n = len(frames)
    hw = spec.get('hw', 2.5)
    k_dot = spec.get('dot_after', first + n) - first
    res = track_ring({i: f for i, f in enumerate(frames[:k_dot + 1])}, spec['init'], spec['ref'], hw=hw)
    P = np.array([res[i][0] for i in range(min(n, k_dot + 1))])
    if k_dot + 1 < n:
        # once the patch is too small to fit, it moves with the jacket: follow the pale-blue dot on her back,
        # keeping the patch's position and size relative to it from the last tracked frames
        dots, prev = [], np.array([636.0, 428.0, 50.0])
        for f in frames:
            prev = blue_dot(f, prev)
            dots.append(prev)
        dots = np.array(dots)
        cal = range(k_dot - 6, k_dot + 1)
        rel = np.median([[(P[i, 0] - dots[i, 0]) / dots[i, 2], (P[i, 1] - dots[i, 1]) / dots[i, 2],
                          P[i, 2] / dots[i, 2], P[i, 3] / dots[i, 2], P[i, 4]] for i in cal], 0)
        ext = [[d[0] + rel[0] * d[2], d[1] + rel[1] * d[2], rel[2] * d[2], rel[3] * d[2], rel[4]] for d in dots[k_dot + 1:]]
        P = np.vstack([P, ext])
    # in-plane rotation of the patch's contents relative to the reference frame
    r = spec['ref']
    ref, m = canonical_disc(frames[r], *P[r])
    rot = [disc_rotation(ref, canonical_disc(frames[i], *P[i])[0], m)[0] for i in range(min(n, k_dot + 1))]
    rot += [rot[-1]] * (n - len(rot))
    Ps = np.stack([smooth_track(P[:, k]) for k in range(5)], 1)
    rot = smooth_track(rot, 3.0)
    k = spec.get('scale', 1.0)      # a smaller patch with a heavier ring has less room inside
    layer = set_lines([(t, font('Archivo-VF.ttf', 200, weight=wt, width=wd), cap * k, cv * k, tr)
                       for t, wt, wd, cap, cv, tr in spec.get('lines', PATCH_LINES)], bold=spec.get('bold', PATCH_BOLD) * k)
    # psi at the reference frame from the lettering's baseline angle there; later frames rotate with the patch
    Mref = patch_matrix(*Ps[r, 2:5], np.deg2rad(spec['beta']))
    c, s = np.cos(Ps[r, 4]), np.sin(Ps[r, 4])
    Eref = np.array([[c, -s], [s, c]]) @ np.diag(Ps[r, 2:4])
    Q = np.linalg.solve(Eref, Mref)
    psi_ref = np.arctan2(Q[1, 0], Q[0, 0])
    # paint out first, collecting the old lettering's ink colour per frame (smoothed: it follows the lighting)
    cleaned, inks = [], []
    for i in range(n):
        cx, cy, a, b, th = Ps[i]
        hwi = hw * min(1.0, min(a, b) / min(Ps[r, 2], Ps[r, 3]))     # the ring thins as the patch shrinks
        region = ellipse_region(frames[i].shape, cx, cy, a, b, th, inset=hwi + 1.8)   # clear of the ring
        clean, strokes = paint_out(frames[i], region)
        # the old letters' tails can reach into the strip between that region and the ring
        band = ellipse_region(frames[i].shape, cx, cy, a, b, th, inset=hwi + 0.3) & (1 - region)
        clean = paint_out_specks(clean, band)
        if spec.get('fill'): clean, _ = fill_patch(frames[i], cx, cy, a, b, th, hwi)
        cleaned.append(clean)
        inks.append(ring_dark(frames[i], cx, cy, a, b, th) if spec.get('ink') == 'ring' else stroke_ink(frames[i], strokes))
    known = [i for i in range(n) if inks[i] is not None]
    ink = np.stack([np.interp(range(n), known, [inks[i][k] for i in known]) for k in range(3)], 1)
    ink = np.stack([smooth_track(ink[:, k], 2.0) for k in range(3)], 1)
    # printed lettering is black ink: where the plate's lighting washes it out, set it darker than it measures so
    # the renderer draws it as ink (the ring is thick enough to survive that; thin glyph strokes are not)
    ink = ink * spec.get('ink_scale', 1.0)
    out = []
    for i in range(n):
        cx, cy, a, b, th = Ps[i]
        fr = frames[i]
        clean = cleaned[i]
        c, s = np.cos(th), np.sin(th)
        E = np.array([[c, -s], [s, c]]) @ np.diag([a, b])
        psi = psi_ref + np.deg2rad(rot[i] - rot[r])
        M = E @ np.array([[np.cos(psi), -np.sin(psi)], [np.sin(psi), np.cos(psi)]])
        alpha, box = warp_layer(layer, M, np.array([cx, cy]), fr.shape)
        if alpha is not None: composite(clean, alpha, box, ink[i])
        out.append(clean)
        log.append({'frame': first + i, 'ellipse': [round(float(v), 3) for v in Ps[i]], 'rot': round(float(rot[i]), 2)})
    return out


def ring_dark(frame, cx, cy, a, b, th):
    """The ring's ink: median of the darker half of its centre line (for lettering too small to sample)."""
    t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    x = cx + a * np.cos(t) * c - b * np.sin(t) * s
    y = cy + a * np.cos(t) * s + b * np.sin(t) * c
    ok = (x >= 0) & (x < frame.shape[1] - 1) & (y >= 0) & (y < frame.shape[0] - 1)
    px = frame[np.round(y[ok]).astype(int), np.round(x[ok]).astype(int)].astype(float)
    lum = px.mean(1)
    return np.median(px[lum <= np.median(lum)], 0)


def blue_dot(frame, prev):
    """The pale-blue dot on the back of the jacket: a circle fitted to its edge where it meets the jacket
    (hair covers part of it, so edge points with hair outside them are dropped). Returns cx, cy, r."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] > 95) & (hsv[..., 0] < 118) & (hsv[..., 1] > 70) & (hsv[..., 2] > 120)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    cand = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] > 20]
    k = min(cand, key=lambda k: np.hypot(*(cen[k] - prev[:2])) - 0.02 * st[k, cv2.CC_STAT_AREA])
    cnts = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
    cnt = max(cnts, key=len)[:, 0, :].astype(float)
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(float)
    c0 = cnt.mean(0)
    keep = []
    for x, y in cnt:
        v = np.array([x, y]) - c0
        v /= np.linalg.norm(v) + 1e-6
        ox, oy = int(round(x + 3 * v[0])), int(round(y + 3 * v[1]))
        if 0 <= ox < frame.shape[1] and 0 <= oy < frame.shape[0] and g[oy, ox] > 110: keep.append((x, y))
    Pt = np.array(keep if len(keep) > 12 else cnt)
    A = np.c_[2 * Pt[:, 0], 2 * Pt[:, 1], np.ones(len(Pt))]
    cx, cy, c = np.linalg.lstsq(A, (Pt ** 2).sum(1), rcond=None)[0]
    return np.array([cx, cy, np.sqrt(c + cx * cx + cy * cy)])


def old_line(frame, dot):
    """The old lettering under the dot: centre, length and angle of its strokes (None when too small to find)."""
    cx, cy, r = dot
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.GaussianBlur(cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))), (0, 0), 1.5)
    zone = np.zeros(g.shape, np.uint8)
    cv2.rectangle(zone, (int(cx - 1.35 * r), int(cy + 1.12 * r)), (int(cx + 1.35 * r), int(cy + 1.64 * r)), 1, -1)
    ys, xs = np.nonzero(((bg - g) > 14) & (zone > 0))
    if r < 16 or len(xs) < 15: return None
    (tx, ty), (rw, rh), ang = cv2.minAreaRect(np.c_[xs, ys].astype(np.float32))
    if rw < rh: rw, rh, ang = rh, rw, ang - 90
    ang = (ang + 45) % 90 - 45
    return [tx, ty, rw, ang]


def fix_back(frames, spec, log):
    lo, hi = spec['frames']
    dots, lines = [], []
    prev = None
    for i in range(lo, hi):
        prev = blue_dot(frames[i], prev if prev is not None else np.array([636.0, 428.0, 50.0]))
        dots.append(prev)
        lines.append(old_line(frames[i], prev))
    dots = np.array(dots)
    # where the lettering is too small to measure, it sits where it did relative to the dot
    rel = np.array([[(l[0] - d[0]) / d[2], (l[1] - d[1]) / d[2], l[2] / d[2]] for l, d in zip(lines, dots) if l])
    ox, oy, kl = np.median(rel[-8:], 0)
    T = np.array([l if l else [d[0] + ox * d[2], d[1] + oy * d[2], kl * d[2], 0.0] for l, d in zip(lines, dots)])
    T = np.stack([smooth_track(T[:, k], 1.5) for k in range(4)], 1)
    f = font(BACK_FONT[0], 200, weight=BACK_FONT[1], width=BACK_FONT[2])
    # track the letters out so the line keeps the old one's proportions (length = 10.7 cap heights)
    probe, half = set_lines([(BACK_TEXT, f, 1.0, 0.0, 0.0)], half=8)
    xs = np.nonzero(probe.max(0) > 0.5)[0]
    natural = (xs.max() - xs.min()) / 256
    track = (10.7 - natural) / (len(BACK_TEXT) - 1)
    layer = set_lines([(BACK_TEXT, f, 1.0, 0.0, track)], half=8)
    out = list(frames)
    for j, i in enumerate(range(lo, hi)):
        tx, ty, L, ang = T[j]
        cap = L / 10.7
        a = np.deg2rad(ang)
        Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        # paint out the old line: its box, grown by a cap height at each end and 0.9 cap heights above and below
        box = cv2.boxPoints(((tx, ty), (L + 2 * cap, 2.8 * cap), ang)).astype(np.int32)
        region = np.zeros(frames[i].shape[:2], np.uint8)
        cv2.fillPoly(region, [box], 1)
        clean, strokes = paint_out(frames[i], region, thr=12, grow=1)
        ink = stroke_ink(frames[i], strokes)
        if ink is None: ink = np.array([60, 45, 45], float)
        alpha, bx = warp_layer(layer, cap * Rm, np.array([tx, ty]), clean.shape, soften=0.5)
        if alpha is not None: composite(clean, alpha, bx, ink)
        out[i] = clean
        log.append({'frame': i, 'back': [round(float(v), 3) for v in T[j]], 'dot': [round(float(v), 2) for v in dots[j]]})
    return out


def run(key, preview=None):
    spec = FIXES[key]
    frames = read_clip(os.path.join(CLIPS, spec['src']))
    log = []
    for p in spec.get('patches', []): frames = fix_patch(frames, p, log)
    for b in spec.get('back', []): frames = fix_back(frames, b, log)
    dst = os.path.join(CLIPS, spec['src'].replace('.mp4', '_lettering.mp4'))
    write_clip(frames, dst)
    if preview:
        os.makedirs(preview, exist_ok=True)
        for i in range(0, len(frames), 2): cv2.imwrite(f'{preview}/{key}_{i:04d}.jpg', frames[i])
        json.dump(log, open(f'{preview}/{key}_track.json', 'w'))
    return dst


if __name__ == '__main__':
    keys = [a for a in sys.argv[1:] if not a.startswith('--') and a in FIXES] or list(FIXES)
    prev = sys.argv[sys.argv.index('--preview') + 1] if '--preview' in sys.argv else None
    for k in keys: print(k, '->', run(k, prev), flush=True)
