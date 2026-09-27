"""Small toolkit for correcting labels on the design sheets without touching their artwork.

Coordinates are sheet pixels. Text is drawn supersampled (k x on a transparent layer, then downsampled), so
small labels land on sub-pixel positions like the original lettering does.
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'render', 'assets', 'fonts') + os.sep


def _path(name):
    return name if name.startswith('/') else FONTS + name


def ring_color(img, box, pad=4):
    """Median colour of a thin ring just outside box."""
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert('RGB')).astype(int)
    H, W = a.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    region = a[Y0:Y1, X0:X1].reshape(-1, 3)
    inner = np.zeros((Y1 - Y0, X1 - X0), bool)
    inner[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
    return tuple(int(v) for v in np.median(region[~inner.reshape(-1)], 0))


def fill(img, box, color=None):
    """Flat fill (for labels on flat backgrounds)."""
    color = color or ring_color(img, box)
    x0, y0, x1, y1 = box
    img.paste(Image.new('RGB', (x1 - x0, y1 - y0), color), (x0, y0))
    return color


def inpaint(img, box, light=True, thr=40, grow=2, radius=4):
    """Inpaint only the text pixels inside box (keeps gradients around them). light = light text on dark."""
    a = cv2.cvtColor(np.asarray(img.convert('RGB')), cv2.COLOR_RGB2BGR)
    x0, y0, x1, y1 = box
    g = cv2.cvtColor(a[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(int)
    bg = np.median(g)
    m = ((g > bg + thr) if light else (g < bg - thr)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=grow)
    mask = np.zeros(a.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = m
    out = cv2.inpaint(a, mask, radius, cv2.INPAINT_TELEA)
    img.paste(Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)))


def erase_dark(img, box, thr=45, grow=1, radius=3):
    """Inpaint dark ink inside box on paper, then put the paper grain back so the patch doesn't read as a blob."""
    a = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    x0, y0, x1, y1 = box
    g = cv2.cvtColor(a[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(int)
    bg = np.median(g)
    m = (g < bg - thr).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=grow)
    mask = np.zeros(a.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = m
    out = cv2.inpaint(a, mask, radius, cv2.INPAINT_TELEA).astype(float)
    ring = g[m == 0]
    sd = float(np.std(ring[np.abs(ring - bg) < 25])) if ring.size else 3.0
    n = np.random.default_rng(x0 * 7 + y0).normal(0, sd, out.shape[:2])
    out[mask > 0] += n[mask > 0][:, None]
    img.paste(Image.fromarray(cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)))


def transplant(img, src_img, src_box, dst_xy, rotate=False, paper=239):
    """Copy a glyph's ink (not its paper) from src_box of src_img to dst_xy in img, optionally turned 180 degrees."""
    g = src_img.crop(src_box)
    if rotate:
        g = g.rotate(180)
    ink = np.asarray(g.convert('RGB')).astype(float)
    alpha = np.clip((paper - 12 - ink.mean(2)) / (paper - 12 - 30), 0, 1)[..., None]
    base = np.asarray(img.crop((dst_xy[0], dst_xy[1], dst_xy[0] + g.width, dst_xy[1] + g.height))).astype(float)
    img.paste(Image.fromarray(np.clip(base * (1 - alpha) + ink * alpha, 0, 255).astype(np.uint8)), dst_xy)


def vfont(name, size, **axes):
    """Variable font with named axes, e.g. vfont('Archivo-VF.ttf', 30, wght=300, wdth=100)."""
    f = ImageFont.truetype(_path(name), size)
    tags = {'Weight': 'wght', 'Width': 'wdth'}
    vals = []
    for ax in f.get_variation_axes():
        n = ax['name'].decode() if isinstance(ax['name'], bytes) else ax['name']
        vals.append(axes.get(tags.get(n, ''), ax['default']))
    f.set_variation_by_axes(vals)
    return f


def cap_font(name, cap, **axes):
    """Font sized so its capital E is `cap` px tall."""
    s = cap * 1.4
    for _ in range(6):
        f = vfont(name, s, **axes) if axes else ImageFont.truetype(_path(name), s)
        b = f.getbbox('E')
        s *= cap / (b[3] - b[1])
    return vfont(name, s, **axes) if axes else ImageFont.truetype(_path(name), s)


def text_width(f, s, tracking=0):
    return sum(f.getlength(ch) for ch in s) + tracking * (len(s) - 1)


def draw_hq(img, x, y, s, fontname, cap, fill, tracking=0.0, k=4, **axes):
    """Supersampled text; (x, y) = left baseline, `cap` = capital height, tracking in output px."""
    f = cap_font(fontname, cap * k, **axes)
    w = int(text_width(f, s, tracking * k) + 8 * k)
    asc, desc = f.getmetrics()
    layer = Image.new('L', (w, asc + desc + 4 * k), 0)
    d = ImageDraw.Draw(layer)
    cx = 2 * k
    for ch in s:
        d.text((cx, 2 * k + asc), ch, font=f, fill=255, anchor='ls')
        cx += f.getlength(ch) + tracking * k
    ox, oy = x - 2, y - (2 * k + asc) / k
    fx, fy = ox - int(ox // 1), oy - int(oy // 1)
    big = Image.new('L', (w + k, layer.height + k), 0)
    big.paste(layer, (int(round(fx * k)), int(round(fy * k))))
    small = big.resize((big.width // k, big.height // k), Image.LANCZOS)
    img.paste(Image.new('RGB', small.size, fill), (int(ox // 1), int(oy // 1)), small)
    return x + text_width(f, s, tracking * k) / k


def draw_hq_x(img, x, y, s, fontname, cap, fill, pitch=None, k=4, **axes):
    """Monospace line whose cells are `pitch` px wide: the line is scaled horizontally (a synthetic condense
    for lettering narrower than any font we have)."""
    f = cap_font(fontname, cap * k, **axes)
    w = int(text_width(f, s) + 8 * k)
    asc, desc = f.getmetrics()
    layer = Image.new('L', (w, asc + desc + 4 * k), 0)
    ImageDraw.Draw(layer).text((2 * k, 2 * k + asc), s, font=f, fill=255, anchor='ls')
    nat = f.getlength('0') / k
    sx = (pitch / nat) if pitch else 1.0
    layer = layer.resize((max(1, int(layer.width * sx)), layer.height), Image.LANCZOS)
    ox, oy = x - 2 * sx, y - (2 * k + asc) / k
    small = layer.resize((max(1, layer.width // k), layer.height // k), Image.LANCZOS)
    img.paste(Image.new('RGB', small.size, fill), (int(round(ox)), int(round(oy))), small)
    return x + len(s) * (pitch or nat)


def cjk(img, x, top, s, size, color, k=4, fontname='NotoSansSC-Black-subset.ttf'):
    """CJK line placed by its top-left ink corner."""
    f = ImageFont.truetype(_path(fontname), size * k)
    b = f.getbbox(s)
    layer = Image.new('L', (b[2] + 4 * k, b[3] + 4 * k), 0)
    ImageDraw.Draw(layer).text((2 * k - b[0], 2 * k - b[1]), s, font=f, fill=255)
    small = layer.resize((layer.width // k, layer.height // k), Image.LANCZOS)
    img.paste(Image.new('RGB', small.size, color), (x - 2, top - 2), small)
