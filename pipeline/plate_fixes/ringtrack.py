"""Active-ellipse tracker for a dark ring (a sleeve patch's outline) on lighter fabric.

An ellipse (cx, cy, a, b, theta) is fitted to the ring's centre line: the ring should be dark, the patch just
inside it light, and the sleeve just outside it light where it isn't covered by hair. Contrast rather than
brightness is scored, so it holds through lighting changes (sd13's beam), and each frame starts from the last
one's prediction with a weak smoothness prior.
"""
import cv2
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import minimize

TH = np.linspace(0, 2 * np.pi, 96, endpoint=False)


def ring_pts(p, d=0.0):
    """Points on the ellipse p, offset by d pixels along both semi-axes (d < 0: inside)."""
    cx, cy, a, b, th = p
    ca, sa = np.cos(th), np.sin(th)
    x = (a + d) * np.cos(TH)
    y = (b + d) * np.sin(TH)
    return cx + ca * x - sa * y, cy + sa * x + ca * y


def score(p, g, hw, prev=None, lam=0.0):
    cx, cy, a, b, th = p
    if min(a, b) < hw + 3: return 1e9
    I = lambda xy: map_coordinates(g, [xy[1], xy[0]], order=1, mode='nearest')
    # the ring is dark across its whole width: sampling three lines through it keeps the fit on its centre line
    # rather than its inner edge (a patch's lettering can come close to the ring and dim the inside samples)
    r = np.maximum.reduce([I(ring_pts(p, -0.6 * hw)), I(ring_pts(p)), I(ring_pts(p, 0.6 * hw))])
    i = I(ring_pts(p, -(hw + 1.5)))       # the patch fabric, just inside the ring
    o = I(ring_pts(p, hw + 1.5))          # the sleeve just outside (or hair)
    cin = np.clip(i - r, -40, 60)
    cout = np.clip(o - r, -20, 60)
    # inner contrast everywhere; outer contrast only where it exists (hair can sit outside the ring)
    s = -(np.mean(cin) + 0.35 * np.mean(np.sort(cout)[len(cout) // 3:]))
    if prev is not None:
        d = np.array(p) - np.array(prev)
        s += lam * (d[0] ** 2 + d[1] ** 2 + 2 * d[2] ** 2 + 2 * d[3] ** 2 + 400 * d[4] ** 2)
    return s


def fit(g, p0, hw, prev=None, lam=0.02):
    best = None
    # a few restarts around the prediction guard against locking onto a neighbouring edge
    for dx, dy in [(0, 0), (2, 0), (-2, 0), (0, 2), (0, -2)]:
        q0 = np.array(p0, float) + [dx, dy, 0, 0, 0]
        r = minimize(score, q0, args=(g, hw, prev, lam), method='Powell',
                     options={'xtol': 1e-2, 'ftol': 1e-3, 'maxfev': 4000})
        if best is None or r.fun < best.fun: best = r
    return best.x, -best.fun


def gray(f, blur=1.0):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), blur)


def track(frames, p_init, i0, hw=2.5, lam=0.02):
    """frames: {index: BGR frame}. Tracks forward and backward from i0; hw is about half the ring's width in
    pixels at the reference frame, and scales with the ring (it thins as a camera pulls back).
    Returns {index: (params, score)}."""
    res = {}
    p, s = fit(gray(frames[i0]), p_init, hw)
    res[i0] = (p, s)
    size0 = min(p[2], p[3])
    for direction in (1, -1):
        prev = res[i0][0]
        vel = np.zeros(5)
        i = i0 + direction
        while i in frames:
            pred = prev + vel
            p, s = fit(gray(frames[i]), pred, hw * min(1.0, min(pred[2], pred[3]) / size0), prev=pred, lam=lam)
            res[i] = (p, s)
            vel = 0.5 * (p - prev)
            prev = p
            i += direction
    return res
