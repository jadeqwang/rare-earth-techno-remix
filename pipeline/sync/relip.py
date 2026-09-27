"""Lip-sync pass 5 (docs/PROCESS.md §3e): every drawing's mouth checked against the vocal, and replaced where it's wrong.

The earlier passes corrected each take with a lag (§3) and then re-timed eight shots by transplanting mouths from
other frames of the same take (remouth.py, §3d). An audit of the release, drawing by drawing against the vocal stem's
spectrogram, still found the mouth wrong in many places: open through rests and breaths, late onto words, shut on
held vowels, missing the lip closures of "from my", and in the transit close-up two mouths at once, where a
transplant had left the take's own smile showing beside it.

This pass starts again from the takes as generated (the lettering fixes kept) and works drawing by drawing:

  1. The exposure sheet (lipsheet.json) says, for every sung syllable, how far the mouth should be open, read off the
     stem's spectrogram and envelope with forced-aligned phones as a first guess. Lip closures (m, b, p, v, f) are
     marked so that they show even when shorter than a drawing. Each drawing is timed a frame ahead of the sound, as
     cel animation times mouths.
  2. For every drawing the renderer shows (on twos, at the shot's lag), the take's own mouth is found and measured: the
     gap between the lips relative to the face's size, against how wide this take opens it when it sings out.
  3. Where the drawn mouth already says what the voice does, it is kept as drawn. Where it doesn't, a mouth that does
     is borrowed from another frame of the same take, chosen by dynamic programming: open as far as the sheet asks,
     from a head turned within 10 degrees (LivePortrait's pose estimate) and at the same scale, near in time and lit
     alike, moving forward the way the take moves. The donor's own drawing is registered onto this face (ECC on the
     lower face, both mouths masked out) and its mouth cloned in (Poisson) over both mouths, the old and the new, so no
     trace of the old one is left. Where the head has turned too far for registration, LivePortrait draws the donor's
     face in this frame's pose (liveportrait.py); where no frame of the take has the mouth needed, it opens or closes
     this frame's own lips.
  4. Every result is measured again and must say what the sheet asks, still look like the donor's mouth, leave the
     face around it unchanged, and be drawn in dark, crisp line. If nothing passes, the drawing stays as the take drew
     it: better slightly off than broken.

The body, the eyes and everything but the mouth stay exactly as the take drew them. Writes <take>_lips.mp4 into
pipeline/base_clips/ and, with --preview DIR, a log of every drawing and QA sheets (before above, after below).

  python3 pipeline/sync/relip.py [sd07 sd13 ...] [--preview DIR]
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import liveportrait as lp  # noqa: E402
import mouth  # noqa: E402

CLIPS = os.path.join(HERE, '..', 'base_clips')
SHEET = json.load(open(os.path.join(HERE, 'lipsheet.json')))['windows']
FPS = 24
LEAD = 1.0 / FPS          # each drawing shows the mouth for the sound a frame ahead

# One entry per take; 'shots' are the edit's uses of it: (name in lipsheet.json, song window, the take's song start,
# lag), exactly as render/src/timeline.js plays them. 'track' says how the face is found:
#   cascade: the anime face cascade, smoothed (its box gives the eyes' line, the face's size and a first guess at
#            the mouth, which is then found in the frame)
#   keys:    (frame, eyes' midpoint x, y, distance between the eyes, mouth x, y), read off the frames by hand and
#            interpolated; for the extreme close-ups, whose faces are too big for the cascade
# 'frames' limits the take to the frames where her face is seen; 'crop' is LivePortrait's crop scale (smaller for the
# close-ups, so that the 512 px it draws are spent on the face).
PLATES = {
    'sd02': {'src': 'sd02_cu_yearning__c8b3647c99.mp4', 'track': 'cascade',
             'shots': [('yearning', (5.70, 8.86), 5.2, -0.041667)]},
    'sd03': {'src': 'sd03_mcu_listen__17fad81acf.mp4', 'track': 'cascade',
             'shots': [('listen', (10.88, 12.73), 10.4, -0.25)]},
    'sd05': {'src': 'sd05_console_caught__ba8af2ae02_lettering.mp4', 'track': 'cascade',
             'shots': [('caught', (23.17, 24.79), 21.5, -0.291667)]},
    'sd06': {'src': 'sd06_blink__a30f474b95.mp4', 'track': 'cascade',
             'shots': [('blink', (25.30, 27.82), 25.0, 0.333333)]},
    'sd07': {'src': 'sd07_transit__9681e0518b.mp4', 'track': 'keys', 'crop': 1.1,
             'keys': [(0, 662, 305, 250, 660, 488), (22, 662, 305, 250, 660, 490), (34, 660, 305, 255, 662, 499),
                      (46, 665, 300, 255, 652, 497), (70, 653, 300, 268, 654, 506), (94, 650, 293, 283, 649, 505),
                      (110, 654, 296, 290, 646, 507), (118, 658, 306, 296, 652, 515), (124, 656, 316, 298, 642, 520),
                      (130, 661, 318, 296, 644, 526), (136, 657, 319, 315, 645, 533), (144, 662, 320, 306, 644, 534)],
             'shots': [('transit_eye', (30.98, 35.94), 30.0, 0.0)]},
    'sd09': {'src': 'sd09_keep_looking__c6c9c8b95f.mp4', 'track': 'cascade',
             'shots': [('keep_yagi', (62.42, 63.23), 61.4, -0.083333)]},
    'sd10': {'src': 'sd10_vision__1368eb119a.mp4', 'track': 'cascade',
             'shots': [('vision', (71.14, 72.54), 71.0, 0.0), ('vision2', (73.999, 75.36), 71.0, 0.125)]},
    'sd11': {'src': 'sd11_care__03ce0c9203.mp4', 'track': 'cascade', 'crop': 1.2,
             'shots': [('care2', (75.36, 77.66), 75.0, 0.125)]},
    'sd12': {'src': 'sd12_search_listen__58e3680064.mp4', 'track': 'cascade', 'frames': (48, 97),
             'shots': [('listen2', (83.10, 84.60), 81.0, -0.208333)]},
    'sd13': {'src': 'sd13_caught_reply__935323d481_lettering.mp4', 'track': 'cascade',
             'shots': [('caught2', (94.61, 97.45), 93.3, -0.333333)]},
    'sd14': {'src': 'sd14_blink_dance__bd2b906427.mp4', 'track': 'cascade',
             'shots': [('blinkdance', (99.76, 100.75), 97.2, -0.083333)]},
    'sd15': {'src': 'sd15_own_ecu__3eb552a647.mp4', 'track': 'keys', 'crop': 1.1,
             'keys': [(0, 645, 275, 275, 648, 485), (34, 645, 275, 275, 648, 485), (56, 650, 262, 300, 636, 495),
                      (78, 662, 272, 323, 644, 503), (96, 656, 258, 324, 641, 520), (106, 652, 256, 340, 641, 527),
                      (116, 652, 250, 352, 635, 523), (120, 652, 250, 352, 635, 523)],
             'shots': [('own', (104.34, 107.79), 102.8, -0.083333)]},
}


def read_clip(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(f)
    return out


def write_clip(frames, path):
    h, w = frames[0].shape[:2]
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                          '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                          '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError('ffmpeg failed: ' + path)


# ------------------------------------------------------------------------------------------------ the face
def track(spec, frames):
    """Per frame: eyes' midpoint (x, y), distance between the eyes, and a first guess at the mouth (x, y)."""
    n = len(frames)
    if spec['track'] == 'keys':
        k = np.array(spec['keys'], float)
        return np.stack([np.interp(np.arange(n), k[:, 0], k[:, c]) for c in range(1, 6)], 1)
    fb, _ = mouth.detect_faces(frames)
    fb = median_filter(fb, size=(7, 1), mode='nearest')
    x, y, w, h = fb.T
    return np.stack([x + 0.5 * w, y + 0.40 * h, 0.36 * w, x + 0.5 * w, y + 0.655 * h], 1)


def mouth_mask(img, cx, cy, fw, sx=0.30, sy=0.14):
    """The drawn mouth nearest (cx, cy); fw = the face's width. The mouth is what is clearly darker or redder than the
    skin around it (the line, the inside of the mouth) plus what that encloses (teeth, tongue). Shapes that reach the
    edge of the search area are the face's outline, the jaw or hair. A closed mouth's thin line, or a small mouth split
    by its teeth, often comes in pieces: pieces level with the mouth and close beside it are joined."""
    H, W = img.shape[:2]
    sw, sh = sx * fw, sy * fw
    x0, x1 = int(max(0, cx - sw)), int(min(W, cx + sw))
    y0, y1 = int(max(0, cy - sh)), int(min(H, cy + sh))
    crop = img[y0:y1, x0:x1]
    out = np.zeros((H, W), np.uint8)
    if crop.size == 0: return out, None
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A = lab[..., 0], lab[..., 1]
    Lr, Ar = np.median(L), np.median(A)                     # the window is mostly skin
    dark = L < Lr - max(14.0, 0.08 * Lr)
    red = (A > Ar + 12) & (L < Lr - 5)
    ell = np.zeros(crop.shape[:2], np.uint8)
    cv2.ellipse(ell, ((cx - x0, cy - y0), (2 * sw, 2 * sh), 0), 1, -1)
    m = ((dark | red) & (ell > 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, max(3, int(fw * 0.03)) | 1), np.uint8))
    n, labl, st, cen = cv2.connectedComponentsWithStats(m, 8)
    edge = ell - cv2.erode(ell, np.ones((5, 5), np.uint8))
    touching = set(np.unique(labl[edge > 0]).tolist())
    best, bs = 0, -1e9
    for k in range(1, n):
        a, w, h = st[k, cv2.CC_STAT_AREA], st[k, cv2.CC_STAT_WIDTH], st[k, cv2.CC_STAT_HEIGHT]
        if a < 10 or w < 0.04 * fw or w > 0.6 * fw or h > 0.35 * fw or k in touching: continue
        d = np.hypot((cen[k][0] - (cx - x0)) / fw, (cen[k][1] - (cy - y0)) / fw * 2.0)
        score = np.log(a) - 25 * d
        if score > bs: best, bs = k, score
    if best == 0: return out, None
    keep = labl == best
    bx, by, bw, bh = st[best, :4]
    for k in range(1, n):
        if k == best or bh > 0.15 * fw or k in touching: continue
        x, y, w, h, a = st[k]
        if a < 6 or h > max(0.05 * fw, 1.5 * bh + 4): continue
        if not (by - 0.02 * fw <= y + h / 2 <= by + bh + 0.02 * fw): continue
        gap = max(x - (bx + bw), bx - (x + w))
        if -0.25 * w <= gap <= 0.10 * fw and max(x + w, bx + bw) - min(x, bx) <= 0.6 * fw: keep = keep | (labl == k)
    keep = keep.astype(np.uint8)
    cnts, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(keep)
    cv2.drawContours(filled, cnts, -1, 1, -1)
    x, y, w, h = cv2.boundingRect(cv2.findNonZero(filled))
    out[y0:y1, x0:x1] = filled
    return out, (x0 + x, y0 + y, w, h)


def find_mouth(img, cx, cy, fw):
    """mouth_mask, and if nothing is found, again with a taller search: a mouth opened wider than the first one."""
    m, bb = mouth_mask(img, cx, cy, fw)
    if bb is None: m, bb = mouth_mask(img, cx, cy, fw, sy=0.24)
    return m, bb


def geometry(img, cx, cy, fw):
    """(mouth x, y, width, gap): the gap between the lips in px, 0 with the lips together. None where no mouth is
    found (a hand over it, the face turned away)."""
    m, bb = find_mouth(img, cx, cy, fw)
    if bb is None: return None
    x, y, w, h = bb
    cols = m[y:y + h, x + w // 4: x + w - w // 4].sum(0)
    gap = float(np.percentile(cols, 90)) if len(cols) else float(h)
    line = max(2.0, 0.014 * fw)
    return (x + w / 2, y + h / 2, float(w), max(0.0, gap - line))


# ------------------------------------------------------------------------------------------------ the sheet
def display_units(win, start, lag, n):
    """The drawings the renderer shows in the window (even frames, on twos): (frame, song time it comes on)."""
    ts = np.arange(win[0], win[1], 1 / 240)
    f = np.floor((ts - start + lag) * FPS + 1e-3).astype(int)
    f = np.clip(f - f % 2, 0, n - 1)
    return sorted(((int(e), float(ts[f == e].min())) for e in np.unique(f)), key=lambda u: u[1])


def target(name, t_on):
    """How open the mouth should be (0 shut .. 1 as wide as the take sings) in the drawing that comes on at t_on and
    holds for two frames."""
    spans = SHEET[name]
    lv = []
    for t in t_on + LEAD + np.linspace(0, 2 / FPS, 9):
        v = 0.0
        for s in spans:
            if s[0] <= t < s[1]: v = s[2]; break
        lv.append(v)
    v = float(np.mean(lv))
    target.flag = None
    for s in spans:                    # 'small' / 'round' spans in force for most of the drawing
        if len(s) > 4 and s[4] in ('small', 'round', 'hold', 'roundhold') and s[0] <= t_on + LEAD + 1 / FPS < s[1]: target.flag = s[4]
    for s in spans:                    # a lip closure shows on the drawing whose time holds the closure's middle
        if len(s) > 4 and s[4] == 'hard':
            mid = (s[0] + s[1]) / 2
            if t_on + LEAD - 1 / FPS <= mid < t_on + LEAD + 1 / FPS: v = min(v, s[2])
    return v


def shaped(flag, o, w):
    """A 'small' span caps the opening (an uh, not an ah); a 'round' span wants a rounded mouth, narrow for the face
    (w = mouth width / eye distance, against this take's roundest open mouths, Plate.wround)."""
    if flag == 'small': return o is None or o <= 0.6
    if flag in ('round', 'roundhold'): return w is None or w <= shaped.wround
    return True


def fits(want, o):
    """Does a mouth open o (its gap for the face's size, 1 = as wide as the take sings) say what the sheet asks? Only
    what reads as wrong is: open through a rest or a lip closure, open wide on a consonant, shut on a sung vowel.
    Anything between is how the take chose to sing it, and is kept."""
    if o is None: return True                                # no mouth to see
    if want <= 0.05: return o <= 0.25                        # a rest or a lip closure: shut, or nearly
    if want <= 0.2: return o <= 0.6                          # a consonant: not wide open
    if want >= 0.5: return o >= 0.25                         # a sung vowel: open
    if want >= 0.35: return o >= 0.1                         # a vowel: not shut
    return True


# ------------------------------------------------------------------------------------------------ re-drawing mouths
def landmarks(tr, geo):
    ex, ey, d, mx, my = tr
    if geo is not None: mx, my = geo[0], geo[1]
    return [(ex - d / 2, ey), (ex + d / 2, ey), (0.45 * ex + 0.55 * mx, 0.45 * ey + 0.55 * my),
            (mx - 0.28 * d, my), (mx + 0.28 * d, my)]


def surround(frame, cx, cy, d):
    """Median luminance of the face around the mouth, and how much of that surround is like it (a hand or a shadow in
    front of the face lowers it)."""
    ring = np.zeros(frame.shape[:2], np.uint8)
    cv2.ellipse(ring, ((float(cx), float(cy)), (float(1.2 * d), float(0.7 * d)), 0), 1, -1)
    cv2.ellipse(ring, ((float(cx), float(cy)), (float(0.6 * d), float(0.3 * d)), 0), 0, -1)
    L = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)[..., 0][ring > 0].astype(np.float32)
    if len(L) < 20: return 0.0, 0.0
    med = float(np.median(L))
    return med, float((np.abs(L - med) < 18).mean())


class Plate:
    """A take's frames with its face track, its mouths measured, and LivePortrait's view of each face."""

    def __init__(self, spec):
        self.spec = spec
        self.frames = read_clip(os.path.join(CLIPS, spec['src']))
        self.n = len(self.frames)
        self.tr = track(spec, self.frames)
        self.lo, self.hi = spec.get('frames', (0, self.n))
        # the mouth: found near the track's guess, then again near where it was found, smoothed over time (the guess
        # from a face box is off by a consistent amount in a turned head)
        g1 = [geometry(f, t[3], t[4], 2.2 * t[2]) for f, t in zip(self.frames, self.tr)]
        off = np.array([[g[0] - t[3], g[1] - t[4]] if g is not None else [np.nan, np.nan] for g, t in zip(g1, self.tr)])
        for c in range(2):
            v = off[:, c]
            ok = np.isfinite(v)
            off[:, c] = median_filter(np.interp(np.arange(self.n), np.flatnonzero(ok), v[ok]), size=9, mode='nearest') \
                if ok.sum() >= 3 else 0.0
        self.tr[:, 3:5] += off
        self.geo = [geometry(f, t[3], t[4], 2.2 * t[2]) for f, t in zip(self.frames, self.tr)]
        sur = [surround(f, *(g[:2] if g is not None else t[3:5]), t[2]) for f, t, g in zip(self.frames, self.tr, self.geo)]
        self.lum = np.array([s[0] for s in sur])
        self.clear = np.array([s[1] for s in sur])
        gap_d = np.array([g[3] / t[2] if g is not None else np.nan for g, t in zip(self.geo, self.tr)])
        # how wide this take opens her mouth when it sings out: openness is measured against it
        r = gap_d[self.lo:self.hi]
        self.wide = float(np.clip(np.nanpercentile(r, 95), 0.08, 0.6)) if np.isfinite(r).any() else 0.3
        self.open = gap_d / self.wide
        wd = np.array([g[2] / t[2] if g is not None else np.nan for g, t in zip(self.geo, self.tr)])
        self.wd = wd
        op = (self.open > 0.3) & np.isfinite(wd)
        self.wround = float(1.2 * np.percentile(wd[op], 5)) if op.any() else 1.0
        self.crop_scale = spec.get('crop', 1.5)
        # how crisply this take draws its mouths (a smudge from the generator is well below it)
        self.crisp = float(np.median([sharpness(self.frames[j], self.mouth_at(j), self.tr[j][2])
                                      for j in range(self.lo, self.hi, 3) if self.geo[j] is not None] or [0.0]))
        self._faces = {}

    def openness(self, img, e):
        g = geometry(img, *self.mouth_at(e), 2.2 * self.tr[e][2])
        return None if g is None else g[3] / self.tr[e][2] / self.wide

    def mouth_at(self, e):
        g = self.geo[e]
        return (g[0], g[1]) if g is not None else (self.tr[e][3], self.tr[e][4])

    def face(self, i):
        if i not in self._faces:
            crop, M = lp.crop_face(self.frames[i], landmarks(self.tr[i], self.geo[i]), scale=self.crop_scale)
            self._faces[i] = (lp.Face(crop), M)
        return self._faces[i]

    def pose_diff(self, i, j):
        """Degrees between the two frames' head rotations, as LivePortrait reads them."""
        Ri, Rj = self.face(i)[0].R, self.face(j)[0].R
        c = (np.trace(Ri.T @ Rj) - 1) / 2
        return float(np.degrees(np.arccos(np.clip(c, -1, 1))))

    def usable(self, i):
        """A frame whose mouth can be lent to another: found, and with the face around it clear."""
        return self.geo[i] is not None and self.clear[i] >= 0.8 * np.median(self.clear[self.lo:self.hi])


def choose_donors(P, run):
    """For a run of drawings whose mouths are wrong, frames of the same take to borrow each mouth from, best first.
    Dynamic programming picks the first choice for the whole run: the mouth open as far as the sheet asks, from near in
    time (so the head and the light match), moving forward the way the take moves. An empty list: no frame has it."""
    C = np.array([j for j in range(P.lo, P.hi) if P.usable(j)])
    if len(C) == 0: return [[] for _ in run]
    INF, NONE = 1e9, 7.0
    oj = P.open[C]
    unary = []
    for e, want, flag in run:
        if want <= 0.05:
            ok, co = oj <= 0.08, 0.2 * (oj / 0.08) ** 2
        elif want <= 0.2:
            ok, co = oj <= 0.35, ((oj - want) / 0.15) ** 2
        elif want >= 0.5:
            ok, co = oj >= max(0.4, 0.6 * want), ((np.minimum(oj, 1.2 * want) - want) / 0.15) ** 2
        else:
            ok, co = np.abs(oj - want) <= max(0.15, 0.35 * want), ((oj - want) / 0.15) ** 2
        # the borrowed face is moved into this frame's head pose; a pose too far off and LivePortrait's warp mangles
        # the mouth, so the donor must be turned and tilted within 10 degrees of this frame and at the same scale
        if flag == 'small': ok = ok & (oj <= 0.6)
        if flag in ('round', 'roundhold'): ok = ok & (P.wd[C] <= P.wround)
        dp = np.array([P.pose_diff(e, j) for j in C])
        ok = ok & (dp <= 10.0) & (np.abs(np.log(P.tr[C, 2] / P.tr[e, 2])) <= 0.12)
        ct = ((C - e) / 18.0) ** 2
        cl = ((P.lum[C] - P.lum[e]) / 12.0) ** 2
        unary.append(np.append(np.where(ok & (C != e), co + 0.5 * ct + 0.6 * cl + (dp / 4.0) ** 2, INF), NONE))
    K, J = len(run), len(C) + 1
    cost = np.full((K, J), INF)
    back = np.zeros((K, J), int)
    cost[0] = unary[0]
    for k in range(1, K):
        dj = C[None, :] - C[:, None] - (run[k][0] - run[k - 1][0])
        pair = np.zeros((J, J))
        pair[:-1, :-1] = 0.15 * np.minimum((dj / 2.0) ** 2, 9.0)
        tot = cost[k - 1][:, None] + pair
        back[k] = np.argmin(tot, 0)
        cost[k] = tot[back[k], np.arange(J)] + unary[k]
    path = [int(np.argmin(cost[-1]))]
    for k in range(K - 1, 0, -1): path.append(int(back[k][path[-1]]))
    out = []
    for k, p in enumerate(path[::-1]):
        alts = [int(C[j]) for j in np.argsort(unary[k][:-1])[:4] if unary[k][j] < INF and j != p]
        out.append(([int(C[p])] if p < len(C) else []) + alts[:2])
    return out


def skin(img):
    """DOT's skin, as the rest of the pipeline tests it (mouth.openness): hands, hair and lines are not skin."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    return ((h < 40) | (h > 340)) & (s > 0.06) & (s < 0.45) & (v > 0.55)


def blend(frame, back, mc, d):
    """back (LivePortrait's drawing of the face, in frame coordinates) cloned into frame over both mouths, the frame's
    own and the new one, and the lower lip's shading below them, with a margin of skin. The region covers every pixel of
    the old mouth, so no trace of its line is left, but stays in the lower face and never takes in anything of the frame
    that isn't skin (a hand, hair). Poisson cloning makes the borrowed skin take on the frame's own light at the border,
    so a shadow on the frame's cheek that the donor didn't have leaves no pale patch."""
    H, W = frame.shape[:2]
    cx, cy = mc
    fw = 2.2 * d
    m1, _ = find_mouth(frame, cx, cy, fw)
    m2, _ = find_mouth(back, cx, cy, fw)
    m = (m1 | m2).astype(np.uint8)
    pts = cv2.findNonZero(m)
    if pts is None: cv2.ellipse(m, ((float(cx), float(cy)), (float(0.5 * d), float(0.25 * d)), 0), 1, -1)
    else: cv2.fillConvexPoly(m, cv2.convexHull(pts), 1)
    down = max(3, int(0.08 * d))
    core = cv2.dilate(m, np.ones((down, 1), np.uint8), anchor=(0, down - 1))
    # a margin of skin around both mouths, kept to the lower face; the mouths themselves are always covered whole,
    # however wide open (a tall mouth reaches further than the margin's cap)
    k = max(3, int(0.10 * d)) | 1
    m = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.4 * k) | 1, k)))
    cap = np.zeros_like(m)
    cv2.ellipse(cap, ((float(cx), float(cy + 0.03 * d)), (float(0.95 * d), float(0.55 * d)), 0), 1, -1)
    m = (m & cap) | cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    # what isn't skin stays as the frame has it (a hand's line, hair), except near the old mouth, where it is the
    # mouth's own teeth and tongue, and must go with it
    hull1 = np.zeros_like(m1)
    p1 = cv2.findNonZero(m1)
    if p1 is not None: cv2.fillConvexPoly(hull1, cv2.convexHull(p1), 1)
    kn = max(3, int(0.15 * d)) | 1
    near = cv2.dilate(hull1, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kn, kn))) > 0
    other = (~skin(frame)) & ~near
    keepout = cv2.dilate(other.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[keepout] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 2:                                                  # keep the part around the mouth
        keep = lab[int(np.clip(cy, 0, H - 1)), int(np.clip(cx, 0, W - 1))]
        if keep == 0: keep = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = (lab == keep).astype(np.uint8)
    # OpenCV's seamlessClone erodes the mask by 3 px and keeps the frame's own gradients outside that: grown by 5 px
    # first, so the whole of the old mouth's outline is inside what gets replaced
    mp = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    mp[keepout] = 0
    mp[:2] = 0; mp[-2:] = 0; mp[:, :2] = 0; mp[:, -2:] = 0
    x, y, w, h = cv2.boundingRect(mp)
    if w < 8 or h < 8: return frame.copy()
    cloned = cv2.seamlessClone(back, frame, mp * 255, (x + w // 2, y + h // 2), cv2.NORMAL_CLONE)
    a = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)
    return np.clip(frame * (1 - a[..., None]) + cloned * a[..., None], 0, 255).astype(np.uint8)


def remnant(orig, img, mc, d):
    """QA: pixels of the frame's own mouth still drawn (dark or red against the skin) outside the new mouth; a second
    mouth, or a leftover end of the old one, shows up here."""
    fw = 2.2 * d
    old, _ = find_mouth(orig, mc[0], mc[1], fw)
    new, _ = find_mouth(img, mc[0], mc[1], fw)
    ring = old > 0
    if not ring.any(): return 0
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    near = cv2.dilate(old, np.ones((31, 31), np.uint8)) > 0
    L, A = lab[..., 0], lab[..., 1]
    Lr, Ar = np.median(L[near]), np.median(A[near])
    cand = (L < Lr - max(14.0, 0.08 * Lr)) | ((A > Ar + 12) & (L < Lr - 5)) | (~skin(img))
    return int((cand & ring & (cv2.dilate(new, np.ones((9, 9), np.uint8)) == 0)).sum())


def skin_kept(orig, img, mc, d):
    """QA: the face around the mouth (outside both mouths) is still as the take drew it. LivePortrait sometimes lights
    up the chin when it closes a wide mouth; such a result is not used."""
    fw = 2.2 * d
    both = find_mouth(orig, mc[0], mc[1], fw)[0] | find_mouth(img, mc[0], mc[1], fw)[0]
    ring = np.zeros(orig.shape[:2], np.uint8)
    cv2.ellipse(ring, ((float(mc[0]), float(mc[1] + 0.1 * d)), (float(1.1 * d), float(0.8 * d)), 0), 1, -1)
    ring[cv2.dilate(both, np.ones((7, 7), np.uint8)) > 0] = 0
    if ring.sum() < 50: return True
    diff = np.abs(cv2.GaussianBlur(orig, (0, 0), 2).astype(np.float32) - cv2.GaussianBlur(img, (0, 0), 2).astype(np.float32)).max(2)
    return float(np.percentile(diff[ring > 0], 98)) < 24


def inked(orig, img, mc, d, mc_new=None):
    """QA: the new mouth is drawn in line as dark as the mouth it comes from (a smudge from the generator isn't)."""
    fw = 2.2 * d
    mo, _ = find_mouth(orig, mc[0], mc[1], fw)
    mn, _ = find_mouth(img, *(mc_new or mc), fw)
    if not mn.any(): return True                  # a mouth closed to nothing is judged by the other checks
    Lo = cv2.cvtColor(orig, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    Ln = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    ref = np.percentile(Lo[mo > 0], 3) if mo.any() else np.percentile(Lo, 1)
    return float(np.percentile(Ln[mn > 0], 3)) <= ref + 25


def sharpness(img, mc, d):
    """How crisply the mouth is drawn: the 95th percentile of the gradient around its line."""
    m, _ = find_mouth(img, mc[0], mc[1], 2.2 * d)
    if not m.any(): return 0.0
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mag = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return float(np.percentile(mag[cv2.dilate(m, np.ones((5, 5), np.uint8)) > 0], 95))


def mouth_patch(img, mc, d, size=(64, 40)):
    x0, y0 = int(mc[0] - 0.5 * d), int(mc[1] - 0.3 * d)
    c = img[max(0, y0):y0 + int(0.6 * d), max(0, x0):x0 + int(d)]
    if c.size == 0: return None
    return cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), size, interpolation=cv2.INTER_AREA).astype(np.float32)


def likeness(P, out, e, donor):
    """How much the mouth now drawn in frame e looks like the donor's (normalised cross-correlation of the two mouths,
    each centred and scaled by its face). LivePortrait moves a mouth; when its warp mangles one, this drops."""
    g = geometry(out, *P.mouth_at(e), 2.2 * P.tr[e][2])
    if g is None or P.geo[donor] is None: return 0.0
    a = mouth_patch(out, g[:2], P.tr[e][2])
    b = mouth_patch(P.frames[donor], P.geo[donor][:2], P.tr[donor][2])
    if a is None or b is None: return 0.0
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))


def register(P, e, j):
    """Affine map from frame j onto frame e, fitted on the lower face with both mouths masked out (ECC), starting from
    the mouths' positions and the faces' sizes. None if it wanders far from that start."""
    body, src = P.frames[e], P.frames[j]
    H, W = body.shape[:2]
    (bx, by), (sx, sy) = P.mouth_at(e), P.mouth_at(j)
    d, dj = P.tr[e][2], P.tr[j][2]
    s = d / dj
    M0 = np.array([[s, 0, bx - s * sx], [0, s, by - s * sy]], np.float32)
    gb = cv2.GaussianBlur(cv2.cvtColor(body, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    gs = cv2.GaussianBlur(cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    mask = np.zeros((H, W), np.uint8)
    cv2.ellipse(mask, ((float(bx), float(by - 0.1 * d)), (float(1.8 * d), float(1.3 * d)), 0), 1, -1)
    for m in (find_mouth(body, bx, by, 2.2 * d)[0], cv2.warpAffine(find_mouth(src, sx, sy, 2.2 * dj)[0], M0, (W, H))):
        mask[cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0] = 0
    try:
        Winv = cv2.invertAffineTransform(M0).astype(np.float32)      # ECC solves body(x) ~ src(W x)
        _, Winv = cv2.findTransformECC(gb, gs, Winv, cv2.MOTION_AFFINE,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 150, 1e-6), mask, 5)
        M = cv2.invertAffineTransform(Winv)
    except cv2.error:
        return None
    c = M[:, :2] @ np.array([sx, sy]) + M[:, 2]
    sc = np.sqrt(abs(np.linalg.det(M[:, :2])))
    if np.hypot(c[0] - bx, c[1] - by) > 0.12 * d or abs(np.log(sc / s)) > 0.1: return None
    return M


def make(P, e, donor, want, redraw=False):
    """Drawing e with the mouth the sheet asks for: borrowed from frame `donor`, or (-1) its own lips opened or closed.
    A borrowed mouth is the donor's own drawing, registered onto this face; with redraw, LivePortrait draws the donor's
    face in this frame's pose instead (for a head turned a little further than registration can follow)."""
    body, Mb = P.face(e)
    H, W = P.frames[e].shape[:2]
    d = P.tr[e][2]
    if donor >= 0 and not redraw:
        M = register(P, e, donor)
        if M is None: return P.frames[e], None, 'no registration'
        back = cv2.warpAffine(P.frames[donor], M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        out = blend(P.frames[e], back, P.mouth_at(e), d)
        return out, P.openness(out, e), f'from {donor}'
    if donor >= 0:
        img = lp.transfer(body, P.face(donor)[0])
        how = f'from {donor}, redrawn'
    else:
        g = P.geo[e]
        w = g[2] if g is not None else 0.5 * d
        now = 0.0 if g is None else g[3] / w
        goal = 0.0 if want <= 0.12 else min(1.0, want * P.wide * d / w)
        img = lp.lips(body, now, goal)
        how = 'own lips'
    back = cv2.warpAffine(img, cv2.invertAffineTransform(Mb), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    out = blend(P.frames[e], back, P.mouth_at(e), d)
    return out, P.openness(out, e), how


def run(key, preview=None):
    spec = PLATES[key]
    P = Plate(spec)
    out = list(P.frames)
    log = {'wide': P.wide, 'shots': {}}
    for name, win, start, lag in spec['shots']:
        units = [(e, t) for e, t in display_units(win, start, lag, P.n) if P.lo <= e < P.hi]
        wants, flags = [], []
        for _, t in units: wants.append(target(name, t)); flags.append(target.flag)
        shaped.wround = P.wround
        opens = [None if P.geo[e] is None else float(P.open[e]) for e, _ in units]
        good = [fits(w, o) and shaped(fl, o, None if P.geo[e] is None else P.wd[e])
                for (e, _), w, o, fl in zip(units, wants, opens, flags)]
        donors = [None] * len(units)
        k = 0
        while k < len(units):                                  # runs of consecutive wrong drawings
            if good[k]: k += 1; continue
            k1 = k
            while k1 < len(units) and not good[k1]: k1 += 1
            for i, dn in zip(range(k, k1), choose_donors(P, [(units[i][0], wants[i], flags[i]) for i in range(k, k1)])):
                donors[i] = dn
            k = k1
        rows = []
        for (e, t), want, fl, o, ok, dn in zip(units, wants, flags, opens, good, donors):
            row = {'frame': e, 't': round(t, 3), 'want': round(want, 2), 'open': None if o is None else round(o, 2),
                   'kept': bool(ok)}
            if not ok:
                # borrowed mouths first, then the drawing's own lips; a result is taken only if it says what the sheet
                # asks and is clean: a borrowed mouth still looks like the donor's, re-posed lips keep their width, the
                # face around the mouth is unchanged, and the mouth is drawn in dark, crisp line. If none is, the drawing
                # stays as the take drew it: better slightly off than broken
                done = None
                for cand, redraw in [(c, False) for c in dn] + [(c, True) for c in dn[:1]] + [(-1, False)]:
                    img, got, how = make(P, e, cand, want, redraw)
                    if how == 'no registration': continue
                    if cand >= 0: clean = likeness(P, img, e, cand) >= 0.6
                    else:
                        g2 = geometry(img, *P.mouth_at(e), 2.2 * P.tr[e][2])
                        clean = g2 is not None and (P.geo[e] is None or 0.7 <= g2[2] / P.geo[e][2] <= 1.4)
                    # the line should be as dark as the mouth it copies (the donor's), or the frame's own when re-posed
                    ref = P.frames[cand] if cand >= 0 else P.frames[e]
                    rmc = P.mouth_at(cand) if cand >= 0 else P.mouth_at(e)
                    clean = clean and skin_kept(P.frames[e], img, P.mouth_at(e), P.tr[e][2]) \
                        and inked(ref, img, rmc, P.tr[e][2], P.mouth_at(e)) \
                        and sharpness(img, P.mouth_at(e), P.tr[e][2]) >= 0.8 * P.crisp
                    g3 = geometry(img, *P.mouth_at(e), 2.2 * P.tr[e][2])
                    if clean and fits(want, got) and shaped(fl, got, None if g3 is None else g3[2] / P.tr[e][2]):
                        done = (img, got, how)
                        break
                if done:
                    img, got, how = done
                    out[e] = img
                    if e + 1 < P.n: out[e + 1] = img    # odd frames are not shown on twos; keep them consistent anyway
                    row.update({'got': None if got is None else round(got, 2), 'how': how, 'fits': True,
                                'remnant': remnant(P.frames[e], img, P.mouth_at(e), P.tr[e][2])})
                elif rows and rows[-1].get('fits') is not False and fits(want, rows[-1].get('got', rows[-1]['open'])):
                    # no clean mouth for this drawing, but the one before says the same: hold that drawing, as cel
                    # animation holds a pose
                    prev = rows[-1]['frame']
                    out[e] = out[prev]
                    if e + 1 < P.n: out[e + 1] = out[prev]
                    row.update({'how': f'held {prev}', 'fits': True, 'got': rows[-1].get('got', rows[-1]['open'])})
                else:
                    row.update({'how': 'no clean fix, kept', 'fits': False})
            rows.append(row)
        # 'hold' spans: one drawing's mouth for the whole span, no flapping (the first drawing in it, as fixed)
        first = None
        for (e, _), fl, row in zip(units, flags, rows):
            if fl not in ('hold', 'roundhold'): first = None; continue
            if first is None:
                first = e
                hold_src = e
                if fl == 'roundhold' and not row.get('fits', True):
                    # the roundest open mouth in the take, borrowed for the whole span
                    cand = [j for j in range(P.lo, P.hi) if P.usable(j) and P.open[j] > 0.3 and j != e]
                    j = min(cand, key=lambda j: P.wd[j])
                    img = make(P, e, j, 0.55)[0]
                    out[e] = img
                    if e + 1 < P.n: out[e + 1] = img
                    row.update({'how': f'from {j} (roundest)', 'fits': True})
                    hold_src = j
                elif row.get('how', '').startswith('from '):
                    hold_src = int(row['how'].split()[1].rstrip(','))
                continue
            # the mouth is held, the body keeps moving: the held mouth is cloned onto each drawing's own frame
            src = hold_src
            img, got, how = make(P, e, src, row['want']) if src != e else (P.frames[e], None, '')
            if how == 'no registration': img = out[first]
            out[e] = img
            if e + 1 < P.n: out[e + 1] = img
            row['how'] = f'mouth held from {src}'
        log['shots'][name] = rows
        changed = [r for r in rows if not r['kept']]
        print(f'  {name}: {len(rows)} drawings, {len(changed)} redrawn ({sum(r["how"] != "own lips" for r in changed)} '
              f'borrowed), {sum(not r["fits"] for r in changed)} still off', flush=True)
    dst = os.path.join(CLIPS, spec['src'].replace('.mp4', '_lips.mp4'))
    write_clip(out, dst)
    if preview:
        os.makedirs(preview, exist_ok=True)
        json.dump(log, open(f'{preview}/{key}_relip.json', 'w'), indent=1)
        for name, rows in log['shots'].items():
            cells = []
            for row in rows:
                e = row['frame']
                cx, cy = P.mouth_at(e)
                s = 0.9 * P.tr[e][2]
                x0, y0 = int(cx - s / 2), int(cy - s * 0.42)
                pair = [cv2.resize(img[max(0, y0):y0 + int(0.66 * s), max(0, x0):x0 + int(s)], (180, 132))
                        for img in (P.frames[e], out[e])]
                c = np.concatenate(pair, 0)
                col = (0, 200, 0) if row['kept'] else ((0, 0, 255) if row.get('fits') else (0, 140, 255))
                cv2.rectangle(c, (0, 0), (179, 263), col, 2)
                cv2.putText(c, f"{row['t']:.2f} w{row['want']:.2f}", (3, 13), 0, 0.42, (255, 255, 0), 1)
                cv2.putText(c, f"o{row['open']} {row.get('how', '')}", (3, 27), 0, 0.38, (255, 255, 0), 1)
                cells.append(c)
            while len(cells) % 10: cells.append(np.zeros_like(cells[0]))
            sheet = np.concatenate([np.concatenate(cells[k:k + 10], 1) for k in range(0, len(cells), 10)], 0)
            cv2.imwrite(f'{preview}/{key}_{name}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return dst


if __name__ == '__main__':
    keys = [a for a in sys.argv[1:] if a in PLATES] or list(PLATES)
    prev = sys.argv[sys.argv.index('--preview') + 1] if '--preview' in sys.argv else None
    for k in keys: print(k, '->', run(k, prev), flush=True)
