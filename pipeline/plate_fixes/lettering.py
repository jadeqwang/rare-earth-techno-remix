"""Lettering toolkit for the base clips: paint out the letters a generated take invented, set the sheet's own.

Design space is a small canvas the new lettering is set on, supersampled; an affine map per frame places it in
the plate. For a sleeve patch the unit circle is the patch ring's centre line, so the lettering is foreshortened
with the patch (a circle seen at an angle is an ellipse, and the map between them is affine).
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'render', 'assets', 'fonts') + os.sep
P = 256          # design-space pixels per unit
K = 4            # supersampling of the warped layer


def font(name, px, weight=None, width=None):
    f = ImageFont.truetype(FONTS + name, int(round(px)))
    f.axes = None
    if weight is not None or width is not None:
        axes = {a['name'].decode(): a['default'] for a in f.get_variation_axes()}
        if weight is not None: axes['Weight'] = weight
        if width is not None: axes['Width'] = width
        f.axes = [axes[a['name'].decode()] for a in f.get_variation_axes()]
        f.set_variation_by_axes(f.axes)
    return f


def resize(f, px):
    """font_variant() starts from the font file, so the variation axes have to be set again."""
    g = f.font_variant(size=int(round(px)))
    if getattr(f, 'axes', None): g.set_variation_by_axes(f.axes)
    return g


def set_lines(lines, half=1.6, bold=0.0):
    """lines: [(text, font, cap_units, centre_v_units, tracking_units)]. Returns a float32 coverage canvas covering
    design space [-half, half]^2. Each line is centred horizontally on u=0 and its cap height on v=centre.
    bold (units) thickens the strokes, for lettering heavier than the font's heaviest weight."""
    n = int(2 * half * P)
    im = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(im)
    for text, f, cap_u, cv_u, track_u in lines:
        cap_px = cap_u * P
        # scale the font so its cap height (H) is cap_px
        l, t, r, b = f.getbbox('H')
        f2 = resize(f, f.size * cap_px / (b - t))
        l, t, r, b = f2.getbbox('H')
        base = n / 2 + cv_u * P + (b - t) / 2          # baseline: cap height centred on cv
        widths = [f2.getlength(ch) for ch in text]
        tw = sum(widths) + track_u * P * (len(text) - 1)
        x = n / 2 - tw / 2
        for ch, w in zip(text, widths):
            d.text((x, base), ch, font=f2, fill=255, anchor='ls', stroke_width=int(round(bold * P)), stroke_fill=255)
            x += w + track_u * P
    return np.asarray(im, np.float32) / 255.0, half


def warp_layer(layer, M, C, shape, soften=0.55):
    """Place a design-space layer in the plate: plate = C + M @ uv. Returns (alpha ROI, (x0, y0, x1, y1))."""
    canvas, half = layer
    n = canvas.shape[0]
    # plate extent of the layer
    corners = np.array([[-half, -half], [half, -half], [half, half], [-half, half]]).T
    pc = (M @ corners).T + C
    H, W = shape[:2]
    x0, y0 = max(0, int(np.floor(pc[:, 0].min())) - 2), max(0, int(np.floor(pc[:, 1].min())) - 2)
    x1, y1 = min(W, int(np.ceil(pc[:, 0].max())) + 2), min(H, int(np.ceil(pc[:, 1].max())) + 2)
    if x1 <= x0 or y1 <= y0: return None, None
    # Canvas pixel i covers [i, i+1) of design space: uv = (i + 0.5 - n/2) / P. Plate coordinates are OpenCV's, where
    # pixel index x is the pixel's centre: plate = C + M uv. The supersampled layer's pixel j is plate coordinate
    # (j + 0.5) / K - 0.5 + origin, so j = K (plate - origin) + (K - 1) / 2.
    A = M / P
    t = C - A @ np.array([n / 2, n / 2])
    Ad = K * A
    td = K * (t - np.array([x0, y0])) + Ad @ np.array([0.5, 0.5]) + (K - 1) / 2
    Mat = np.hstack([Ad, td[:, None]]).astype(np.float32)
    big = cv2.warpAffine(canvas, Mat, (K * (x1 - x0), K * (y1 - y0)), flags=cv2.INTER_LINEAR, borderValue=0)
    a = cv2.resize(big, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    if soften > 0: a = cv2.GaussianBlur(a, (0, 0), soften)       # the plates are soft 720p; match their edges
    return np.clip(a, 0, 1), (x0, y0, x1, y1)


def composite(frame, alpha, box, ink):
    x0, y0, x1, y1 = box
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    a = alpha[..., None]
    frame[y0:y1, x0:x1] = np.clip(roi * (1 - a) + np.array(ink, np.float32) * a, 0, 255).astype(np.uint8)


def paint_out_specks(frame, band, thr=16, max_len=9, radius=2):
    """Inpaint compact dark blobs inside `band` (the strip just inside a patch's ring, where the old letters'
    tails can reach). The ring's own soft inner edge also darkens that strip, but as a long arc: only blobs no
    longer than max_len pixels are removed, so the ring is left alone."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.GaussianBlur(cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))), (0, 0), 2)
    dark = (((bg - g) > thr) & (band > 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
    m = np.zeros_like(dark)
    for k in range(1, n):
        if max(st[k, cv2.CC_STAT_WIDTH], st[k, cv2.CC_STAT_HEIGHT]) <= max_len: m[lab == k] = 1
    if not m.any(): return frame
    m = cv2.dilate(m, np.ones((3, 3), np.uint8)) & (band > 0)
    # fill with the fabric's own colour (a per-channel closing drops thin dark features, the ring included), not
    # by inpainting: next to the ring, inpainting would drag the ring's dark into the fill
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    fabric = cv2.GaussianBlur(cv2.morphologyEx(frame, cv2.MORPH_CLOSE, k), (0, 0), 1.5).astype(np.float32)
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7)[..., None]
    return np.clip(frame.astype(np.float32) * (1 - a) + fabric * a, 0, 255).astype(np.uint8)


def stroke_ink(frame, strokes):
    """Colour of the old lettering: median of its darkest pixels (BGR), or None if there are too few."""
    px = frame[strokes > 0].astype(np.float32)
    if len(px) < 12: return None
    lum = px.mean(1)
    return np.median(px[lum <= np.percentile(lum, 20)], 0)


def paint_out(frame, region, thr=18, grow=2, radius=3):
    """Inpaint the dark strokes inside region (uint8 mask): pixels darker than the local fabric by thr."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # local fabric level: a closing removes strokes thinner than the kernel
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    bg = cv2.GaussianBlur(bg, (0, 0), 2)
    strokes = ((bg - g) > thr).astype(np.uint8) & (region > 0)
    strokes = cv2.dilate(strokes, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    strokes &= (region > 0)
    out = cv2.inpaint(frame, strokes * 255, radius, cv2.INPAINT_TELEA)
    return out, strokes


def fill_patch(frame, cx, cy, a, b, th, hw):
    """Repaint a patch's whole interior, up to the ring's inner edge, in its own fabric colour (for a small patch
    whose old lettering runs into the ring, where stroke-by-stroke inpainting would leave the joins behind).
    The colour is the median of the interior's lighter pixels; the edge is feathered by a pixel."""
    inner = ellipse_mask(frame.shape, cx, cy, max(1.0, a - hw * 0.8), max(1.0, b - hw * 0.8), th)
    probe = ellipse_mask(frame.shape, cx, cy, max(1.0, a - hw - 1.5), max(1.0, b - hw - 1.5), th)
    px = frame[probe > 0].astype(np.float32)
    lum = px.mean(1)
    col = np.median(px[lum >= np.percentile(lum, 55)], 0)
    alpha = cv2.GaussianBlur(inner.astype(np.float32), (0, 0), 0.7)[..., None]
    out = frame.astype(np.float32) * (1 - alpha) + col * alpha
    return np.clip(out, 0, 255).astype(np.uint8), col


def ellipse_mask(shape, cx, cy, a, b, th):
    m = np.zeros(shape[:2], np.uint8)
    cv2.ellipse(m, ((float(cx), float(cy)), (float(2 * a), float(2 * b)), float(np.rad2deg(th))), 1, -1)
    return m


def patch_matrix(a, b, th, beta):
    """Affine map from the patch's design space (unit circle = ring centre line) to the plate, with the lettering's
    baseline at image angle beta. Any map of the unit circle onto the ellipse is E R(psi); psi sets the baseline."""
    c, s = np.cos(th), np.sin(th)
    E = np.array([[c, -s], [s, c]]) @ np.diag([a, b])
    u, v = np.array([[c, s], [-s, c]]) @ np.array([np.cos(beta), np.sin(beta)])
    psi = np.arctan2(v / b, u / a)
    return E @ np.array([[np.cos(psi), -np.sin(psi)], [np.sin(psi), np.cos(psi)]])


def ellipse_region(shape, cx, cy, a, b, th, inset):
    """The patch's fabric inside its ring: the ring ellipse pulled in by `inset` pixels on both axes."""
    return ellipse_mask(shape, cx, cy, max(1.0, a - inset), max(1.0, b - inset), th)


def canonical_disc(frame, cx, cy, a, b, th, n=96, r=0.8):
    """Resample the patch into its own unit disc (undoing the ellipse), grayscale, zero outside radius r."""
    c, s = np.cos(th), np.sin(th)
    u = (np.arange(n) + 0.5) / n * 2 - 1
    U, V = np.meshgrid(u, u)
    X = cx + c * a * U - s * b * V
    Y = cy + s * a * U + c * b * V
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    d = cv2.remap(g, X.astype(np.float32), Y.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    m = (U ** 2 + V ** 2) < r * r
    d = np.where(m, d - d[m].mean(), 0)
    return d / (np.sqrt((d[m] ** 2).mean()) + 1e-6), m


def disc_rotation(ref, cur, mask, lo=-30, hi=30, step=0.5):
    """In-plane rotation (degrees) that best maps the reference patch onto the current one."""
    n = ref.shape[0]
    best = None
    for deg in np.arange(lo, hi + 1e-9, step):
        R = cv2.getRotationMatrix2D((n / 2 - 0.5, n / 2 - 0.5), -deg, 1.0)
        rr = cv2.warpAffine(ref, R, (n, n), flags=cv2.INTER_LINEAR)
        sc = float((rr * cur)[mask].mean())
        if best is None or sc > best[0]: best = (sc, deg)
    return best[1], best[0]
