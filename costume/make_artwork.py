"""Print/cut-ready artwork for DOT's jacket graphics (stage costume), set exactly as the video sets them.

Source of truth for the lettering: pipeline/plate_fixes/fix_lettering.py (PATCH_LINES, PATCH_BOLD, BACK_FONT,
BACK_TEXT) and pipeline/plate_fixes/lettering.py (set_lines: how lines are scaled, centred and tracked). The
settings are imported from there, so a change to the video's lettering carries over on the next run.

All lettering is converted to outlines (no font needed to open the files). Physical sizes live in SIZES below
(inches); edit and re-run:

    python3 costume/make_artwork.py

Writes
  costume/artwork/   SVGs at true size (viewBox in inches) + 600-dpi PNGs (transparent background)
  costume/spec/      dimensioned spec sheets (SVG, PNG, PDF; letter landscape)
  costume/templates/ actual-size tiled templates on letter paper (PDF + page PNGs), 1-in calibration square
  costume/fonts/     Archivo VF + OFL, and static instances at the exact settings
Needs: fonttools, skia-pathops, shapely, cairosvg, pypdf, numpy (+ Pillow/opencv to read the video's own track).
"""
import math
import os
import re
import shutil
import sys

import numpy as np

# ------------------------------------------------------------------------------------------------------------------
# CONFIG (inches). Change and re-run. One size for both jackets (M and XL).
SIZES = {
    'patch_ring_outer_diameter': 4.0,  # sleeve patch: black ring, outer edge (10.2 cm)
    'patch_ring_thickness': 0.25,      # black ring width (6 mm)
    'patch_field_margin': 0.14,        # white field beyond the ring's outer edge (sheet: 0.035 x ring outer Ø a side)
    'patch_edge_line': 0.02,           # hairline round the field's edge, as drawn on the sheet; 0 = none
    'back_dot_diameter': 7.75,         # pale-blue dot on the back (19.7 cm)
    'back_line_length': 7.5,           # RARE EARTH ink length; cap height = this / 10.7 (the video's proportion)
    'back_gap_dot_to_caps': 1.0,       # dot's bottom edge to the top of the caps
    'chest_dot_diameter': 2.0,         # pale-blue dot on the left chest
}
COLOURS = {
    'pale_blue': '#94BEE4',            # dots (sheet palette swatch)
    'ink': '#272729',                  # ring + all lettering (ink black)
    'field': '#E7E4E2',                # sleeve patch field (white)
    'orange': '#EF8953',               # sleeve/body stripes - reference only, not in any artwork
}
PLACEMENT = {
    'back': ['dot top 2.1 in (M) / 2.5 in (XL) below the collar seam,', 'horizontally centred on the back'],
    'chest': ['wearer\'s left; dot centre 3 5/8 in from the zip edge,', 'about 4 3/4 in below the shoulder-neck point'],
    'patch': ['centred on the outer left upper arm,', 'patch centre 4 3/4 in below the shoulder seam'],
}
PNG_DPI = 600
SPEC_DPI = 200
TEMPLATE_DPI = 150
TEMPLATE_MARGIN = 0.35                 # paper round a single cutting template's dashed line

# Measured on design/dot_character_sheet.jpg (JACKET DETAILS > LEFT SLEEVE, opencv ellipse fit), for reference:
SHEET_RING_T_OVER_OUTER_D = 0.072      # ring thickness / ring outer Ø (0.073 across, 0.071 down) = 0.156 r
SHEET_FIELD_OVER_RING_D = 1.07         # white field Ø / ring outer Ø
# ------------------------------------------------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FONT_DIR = os.path.join(REPO, 'render', 'assets', 'fonts')
VF_PATH = os.path.join(FONT_DIR, 'Archivo-VF.ttf')
OUT_ART = os.path.join(HERE, 'artwork')
OUT_SPEC = os.path.join(HERE, 'spec')
OUT_TPL = os.path.join(HERE, 'templates')
OUT_FONTS = os.path.join(HERE, 'fonts')

# the video's settings, read from the pipeline (copies as fallback if its imports are unavailable)
sys.path.insert(0, os.path.join(REPO, 'pipeline', 'plate_fixes'))
try:
    from fix_lettering import PATCH_LINES, PATCH_BOLD, BACK_FONT, BACK_TEXT
except Exception:
    PATCH_LINES = [('1420', 800, 74, 0.42, -0.25, 0.02), ('MHz', 800, 96, 0.38, 0.29, 0.02)]
    PATCH_BOLD = 0.006
    BACK_FONT = ('Archivo-VF.ttf', 720, 112)
    BACK_TEXT = 'RARE EARTH'
P_VIDEO = 256                          # lettering.P: design-space pixels per unit
# set_lines draws the bold as a PIL stroke of int(round(bold * P)) pixels, i.e. this many units per side:
PATCH_BOLD_EFFECTIVE = int(round(PATCH_BOLD * P_VIDEO)) / P_VIDEO
BACK_LINE_CAPS = 10.7                  # fix_back: line length = 10.7 cap heights
LABEL_AXES = (500, 100)                # Archivo instance for spec/template labels

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from shapely.geometry import Polygon
from shapely.ops import unary_union


def f5(v):
    s = f'{v:.5f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def circle_d(cx, cy, r):
    """A circle as four cubic Beziers (radial error 0.03%), drawn the same by every renderer and cutter."""
    q = 0.5522847498 * r
    return (f'M{f5(cx + r)} {f5(cy)} '
            f'C{f5(cx + r)} {f5(cy + q)} {f5(cx + q)} {f5(cy + r)} {f5(cx)} {f5(cy + r)} '
            f'C{f5(cx - q)} {f5(cy + r)} {f5(cx - r)} {f5(cy + q)} {f5(cx - r)} {f5(cy)} '
            f'C{f5(cx - r)} {f5(cy - q)} {f5(cx - q)} {f5(cy - r)} {f5(cx)} {f5(cy - r)} '
            f'C{f5(cx + q)} {f5(cy - r)} {f5(cx + r)} {f5(cy - q)} {f5(cx + r)} {f5(cy)} Z')


def circle(cx, cy, r, attrs):
    return '<path d="%s" %s/>' % (circle_d(cx, cy, r), attrs)


def cm(v):
    return v * 2.54


def dimtxt(v):
    return f'{v:.3f} in  ({cm(v):.2f} cm)'


# ---------------------------------------------------------------------------------------------------------- fonts
_INST = {}


def instance(wght, wdth):
    """Static Archivo at (wght, wdth), overlaps removed (clean outlines for cutters)."""
    key = (wght, wdth)
    if key not in _INST:
        vf = TTFont(VF_PATH)
        f = instancer.instantiateVariableFont(vf, {'wght': wght, 'wdth': wdth},
                                              overlap=instancer.OverlapMode.REMOVE)
        _INST[key] = f
    return _INST[key]


def cap_units(f):
    gs = f.getGlyphSet()
    bp = BoundsPen(gs)
    gs[f.getBestCmap()[ord('H')]].draw(bp)
    return bp.bounds[3] - bp.bounds[1]


def glyph_info(f, ch):
    cmap = f.getBestCmap()
    name = cmap.get(ord(ch)) or cmap.get(ord('?'))
    gs = f.getGlyphSet()
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    return name, f['hmtx'][name][0], bp.bounds


def layout(f, text, cap, track):
    """Per-char placement as lettering.set_lines does it: each glyph at its advance, plus `track` (same units as
    cap) between glyphs, no kerning. Returns [(glyph name, x offset)], scale, advance-based total width, ink x0, x1."""
    s = cap / cap_units(f)
    x, out, ink0, ink1 = 0.0, [], None, None
    for i, ch in enumerate(text):
        name, adv, b = glyph_info(f, ch)
        out.append((name, x))
        if b is not None:
            ink0 = x + b[0] * s if ink0 is None else min(ink0, x + b[0] * s)
            ink1 = x + b[2] * s if ink1 is None else max(ink1, x + b[2] * s)
        x += adv * s + (track if i < len(text) - 1 else 0)
    return out, s, x, ink0, ink1


def text_path(f, text, cap, x0, baseline, track=0.0, anchor='start'):
    """SVG path data (curves) for `text` with cap height `cap`; anchor start/middle/end on the advance width."""
    glyphs, s, total, _, _ = layout(f, text, cap, track)
    if anchor == 'middle': x0 -= total / 2
    elif anchor == 'end': x0 -= total
    gs = f.getGlyphSet()
    pen = SVGPathPen(gs, ntos=f5)
    for name, gx in glyphs:
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x0 + gx, baseline)))
    return pen.getCommands(), total


class FlattenPen(BasePen):
    def __init__(self, gs, steps=24):
        super().__init__(gs)
        self.contours, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        for k in range(1, self.steps + 1):
            t = k / self.steps
            mt = 1 - t
            self.cur.append(tuple(mt ** 3 * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t ** 3 * d
                                  for a, b, c, d in zip(p0, p1, p2, p3)))

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        for k in range(1, self.steps + 1):
            t = k / self.steps
            mt = 1 - t
            self.cur.append(tuple(mt * mt * a + 2 * mt * t * b + t * t * c for a, b, c in zip(p0, p1, p2)))

    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def glyph_geometry(f, name, transform):
    gs = f.getGlyphSet()
    fp = FlattenPen(gs)
    gs[name].draw(TransformPen(fp, transform))
    polys = [Polygon(c).buffer(0) for c in fp.contours]
    if not polys: return None
    signed = [Polygon(c).exterior.is_ccw for c in fp.contours]
    big = int(np.argmax([p.area for p in polys]))
    fills = [p for p, o in zip(polys, signed) if o == signed[big]]
    holes = [p for p, o in zip(polys, signed) if o != signed[big]]
    g = unary_union(fills)
    if holes: g = g.difference(unary_union(holes))
    return g


def geom_path(g):
    def ring(coords):
        pts = list(coords)[:-1]
        return 'M' + ' L'.join(f'{f5(x)} {f5(y)}' for x, y in pts) + ' Z'
    parts = []
    for poly in getattr(g, 'geoms', [g]):
        parts.append(ring(poly.exterior.coords))
        parts += [ring(i.coords) for i in poly.interiors]
    return ' '.join(parts)


def bold_text_path(f, text, cap, x0, baseline, track, offset):
    """Outlines of `text` thickened by `offset` per side (round joins, like PIL/FreeType's stroker), as one path."""
    glyphs, s, total, _, _ = layout(f, text, cap, track)
    geoms = []
    for name, gx in glyphs:
        g = glyph_geometry(f, name, (s, 0, 0, -s, x0 + gx, baseline))
        if g is not None: geoms.append(g.buffer(offset, quad_segs=16, join_style='round'))
    u = unary_union(geoms)
    return geom_path(u), u.bounds


# -------------------------------------------------------------------------------------------------------- artwork
def patch_art():
    """Sleeve patch in its own coordinates (inches, origin top-left of the field's bounding square). The video's
    design unit r is the ring's centre-line radius; the lettering is set in r exactly as set_lines sets it."""
    ro = SIZES['patch_ring_outer_diameter'] / 2
    t = SIZES['patch_ring_thickness']
    ri = ro - t
    k = ro - t / 2                               # inches per r
    R = ro + SIZES['patch_field_margin']
    D = 2 * R
    c = R
    off = PATCH_BOLD_EFFECTIVE * k
    ink, field = COLOURS['ink'], COLOURS['field']
    el = ['<g id="field">%s</g>' % circle(c, c, R, f'fill="{field}"')]
    w = SIZES['patch_edge_line']
    if w > 0:
        el.append('<g id="edge_line">%s</g>' % circle(c, c, R - w / 2, f'fill="none" stroke="{ink}" stroke-width="{f5(w)}"'))
    el.append(f'<g id="ring"><path fill="{ink}" fill-rule="evenodd" d="{circle_d(c, c, ro)} {circle_d(c, c, ri)}"/></g>')
    meta = {'D': D, 'R': R, 'k': k, 'c': c, 'ro': ro, 'ri': ri, 'off': off, 'lines': []}
    for text, wght, wdth, cap_r, cv_r, tr_r in PATCH_LINES:
        f = instance(wght, wdth)
        cap, track = cap_r * k, tr_r * k
        glyphs, s, total, ink0, ink1 = layout(f, text, cap, track)
        x0 = c - total / 2                       # set_lines: centred on the advance width
        base = c + cv_r * k + cap / 2            # cap height centred on cv
        d, b = bold_text_path(f, text, cap, x0, base, track, off)
        el.append(f'<g id="line_{text}"><path fill="{ink}" d="{d}"/></g>')
        meta['lines'].append(dict(text=text, wght=wght, wdth=wdth, cap_r=cap_r, cv_r=cv_r, tr_r=tr_r, cap=cap,
                                  track=track, base=base, x0=x0, adv=total, bounds=b, upm=f['head'].unitsPerEm,
                                  capu=cap_units(f)))
    return '\n'.join(el), D, D, meta


def back_track():
    """fix_back's tracking: natural ink width of the line at cap 1 and no tracking, then
    track = (10.7 - natural) / (n - 1) in cap units, so the ink line is exactly 10.7 cap heights. Measured here on the
    exact outlines; the video measures the same thing on a PIL raster (font size rounded to whole pixels), which
    reads the natural width ~0.5% short. That value is returned third, for reference."""
    f = instance(BACK_FONT[1], BACK_FONT[2])
    _, _, _, a, b = layout(f, BACK_TEXT, 1.0, 0.0)
    natural = b - a
    raster = None
    try:
        import lettering as L
        g = L.font(BACK_FONT[0], 200, weight=BACK_FONT[1], width=BACK_FONT[2])
        probe, _ = L.set_lines([(BACK_TEXT, g, 1.0, 0.0, 0.0)], half=8)
        xs = np.nonzero(probe.max(0) > 0.5)[0]
        raster = (BACK_LINE_CAPS - (xs.max() - xs.min()) / L.P) / (len(BACK_TEXT) - 1)
    except Exception:
        pass
    return (BACK_LINE_CAPS - natural) / (len(BACK_TEXT) - 1), natural, raster


BACK_TRACK, BACK_NATURAL, BACK_TRACK_RASTER = back_track()


def lettering_art():
    """RARE EARTH alone, tight to the ink (inches, origin top-left of the ink box)."""
    f = instance(BACK_FONT[1], BACK_FONT[2])
    cap = SIZES['back_line_length'] / BACK_LINE_CAPS
    track = BACK_TRACK * cap
    glyphs, s, total, ink0, ink1 = layout(f, BACK_TEXT, cap, track)
    d, _ = text_path(f, BACK_TEXT, cap, -ink0, cap, track)
    # ink box vertically: cap top .. baseline (no descenders, flat tops and bottoms in these letters)
    W, H = ink1 - ink0, cap
    meta = dict(cap=cap, track=track, adv=total, ink=W, upm=f['head'].unitsPerEm, capu=cap_units(f))
    return d, W, H, meta


def back_art():
    """Dot + lettering composed: the lettering's ink centred on the dot's vertical axis."""
    d, W, H, lm = lettering_art()
    Dd = SIZES['back_dot_diameter']
    gap = SIZES['back_gap_dot_to_caps']
    width = max(Dd, W)
    cx = width / 2
    ly = Dd + gap
    el = ['<g id="back_dot">%s</g>' % circle(cx, Dd / 2, Dd / 2, f'fill="{COLOURS["pale_blue"]}"'),
          f'<g id="rare_earth" transform="translate({f5(cx - W / 2)} {f5(ly)})"><path fill="{COLOURS["ink"]}" d="{d}"/></g>']
    meta = dict(lm, Dd=Dd, gap=gap, W=W, width=width, height=ly + H, cx=cx, ly=ly)
    return '\n'.join(el), width, ly + H, meta


def dot_art(D):
    return circle(D / 2, D / 2, D / 2, f'fill="{COLOURS["pale_blue"]}"'), D, D


def label(text, cap, x, base, anchor='start', fill='#222222', weight=None):
    f = instance(*(weight or LABEL_AXES))
    d, w = text_path(f, text, cap, x, base, anchor=anchor)
    return f'<path fill="{fill}" d="{d}"/>', w


def template_art(name, D):
    m = TEMPLATE_MARGIN
    W = D + 2 * m
    lab_h = 0.62
    H = D + 2 * m + lab_h
    c = (W / 2, m + D / 2)
    lw = 0.012
    el = [f'<rect width="{f5(W)}" height="{f5(H)}" fill="#FFFFFF"/>',
          circle(c[0], c[1], D / 2, f'fill="{COLOURS["pale_blue"]}" fill-opacity="0.35" stroke="#111111" '
                                    f'stroke-width="{lw}" stroke-dasharray="0.09 0.06"'),
          f'<path d="M{f5(c[0] - 0.15)} {f5(c[1])} H{f5(c[0] + 0.15)} M{f5(c[0])} {f5(c[1] - 0.15)} V{f5(c[1] + 0.15)}" '
          f'stroke="#111111" stroke-width="{lw}"/>']
    y = D + 2 * m + 0.08
    for txt, cap, dy, wt, col in ((f'{name}  -  CUT ON DASHED LINE', 0.085, 0.085, (700, 100), '#222222'),
                                  (f'Ø {D:.3f} in  /  {cm(D):.2f} cm   fill {COLOURS["pale_blue"]}', 0.075, 0.26, None, '#222222'),
                                  ('print at 100% - check: this line is 1.000 in', 0.06, 0.42, None, '#555555')):
        p, _ = label(txt, cap, W / 2, y + dy, 'middle', fill=col, weight=wt)
        el.append(p)
    el.append(f'<path d="M{f5(W / 2 - 0.5)} {f5(y + 0.52)} h1" stroke="#555555" stroke-width="{lw}"/>')
    return '\n'.join(el), W, H


def svg_doc(body, W, H, title, extra=''):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{f5(W)}in" height="{f5(H)}in" '
            f'viewBox="0 0 {f5(W)} {f5(H)}">\n<title>{title}</title>\n'
            f'<!-- units: inches (1 viewBox unit = 1 in). Lettering is outlines; font: Archivo (SIL OFL 1.1). -->\n'
            f'{extra}{body}\n</svg>\n')


def write_svg(path, body, W, H, title, dpi=PNG_DPI):
    import cairosvg
    s = svg_doc(body, W, H, title)
    with open(path, 'w') as fh: fh.write(s)
    cairosvg.svg2png(bytestring=s.encode(), write_to=path[:-4] + '.png', dpi=dpi)


# ---------------------------------------------------------------------------------------------------- spec sheets
PAGE_W, PAGE_H = 11.0, 8.5
DIM = '#1F3A93'                       # dimension lines: dark blue, distinct from the black artwork


class Sheet:
    def __init__(self, title, subtitle, w=PAGE_W, h=PAGE_H):
        self.w, self.h = w, h
        self.el = [f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>']
        p, _ = label(title, 0.2, 0.5, 0.75, weight=(800, 100), fill='#111111'); self.el.append(p)
        p, _ = label(subtitle, 0.085, 0.5, 1.0, fill='#555555'); self.el.append(p)
        self.el.append(f'<path d="M0.5 1.15 H{w - 0.5}" stroke="#BBBBBB" stroke-width="0.01"/>')

    def place(self, body, W, H, box):
        """Artwork into box (x, y, w, h) on the page, scaled to fit (never enlarged); returns the mapping."""
        x, y, w, h = box
        s = min(w / W, h / H, 1.0)
        ox, oy = x + (w - W * s) / 2, y + (h - H * s) / 2
        self.el.append(f'<g transform="translate({f5(ox)} {f5(oy)}) scale({f5(s)})">{body}</g>')
        self.s = s
        return lambda px, py: (ox + px * s, oy + py * s)

    def text(self, t, x, y, cap=0.075, anchor='start', fill='#222222', weight=None, bg=False):
        p, w = label(t, cap, x, y, anchor, fill=fill, weight=weight)
        if bg:
            x0 = x - (w / 2 if anchor == 'middle' else w if anchor == 'end' else 0)
            self.el.append(f'<rect x="{f5(x0 - 0.04)}" y="{f5(y - cap - 0.05)}" width="{f5(w + 0.08)}" '
                           f'height="{f5(cap + 0.1)}" fill="#FFFFFF"/>')
        self.el.append(p)
        return w

    def line(self, x0, y0, x1, y1, w=0.008, col=DIM, dash=None):
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.el.append(f'<path d="M{f5(x0)} {f5(y0)} L{f5(x1)} {f5(y1)}" stroke="{col}" stroke-width="{w}"{da} fill="none"/>')

    def arrow(self, x, y, ang):
        a = 0.07; h = 0.025
        c, s = math.cos(ang), math.sin(ang)
        pts = [(x, y), (x - a * c + h * s, y - a * s - h * c), (x - a * c - h * s, y - a * s + h * c)]
        self.el.append('<path fill="%s" d="M%s Z"/>' % (DIM, ' L'.join(f'{f5(px)} {f5(py)}' for px, py in pts)))

    def hdim(self, x0, x1, y, txt, ext=None, above=True, outside=False):
        """Horizontal dimension between x0 and x1 at height y; ext = (y_from0, y_from1) for extension lines."""
        if ext:
            for xx, yy in ((x0, ext[0]), (x1, ext[1])):
                self.line(xx, yy, xx, y + (-0.06 if yy > y else 0.06), w=0.006)
        if outside:
            self.line(x0 - 0.25, y, x1 + 0.25, y)
            self.arrow(x0, y, 0); self.arrow(x1, y, math.pi)
        else:
            self.line(x0, y, x1, y)
            self.arrow(x0, y, math.pi); self.arrow(x1, y, 0)
        if txt: self.text(txt, (x0 + x1) / 2, y - 0.07 if above else y + 0.16, anchor='middle', fill=DIM, bg=True)

    def vdim(self, y0, y1, x, txt, ext=None, side='right', outside=False):
        if ext:
            for xx, yy in ((ext[0], y0), (ext[1], y1)):
                self.line(xx, yy, x + (0.06 if x > xx else -0.06), yy, w=0.006)
        if outside:
            self.line(x, y0 - 0.25, x, y1 + 0.25)
            self.arrow(x, y0, math.pi / 2); self.arrow(x, y1, -math.pi / 2)
        else:
            self.line(x, y0, x, y1)
            self.arrow(x, y0, -math.pi / 2); self.arrow(x, y1, math.pi / 2)
        ym = (y0 + y1) / 2 + 0.035
        self.text(txt, x + 0.1 if side == 'right' else x - 0.1, ym, anchor='start' if side == 'right' else 'end',
                  fill=DIM, bg=True)

    def table(self, x, y, rows, w=4.0, col2=1.45):
        """rows: (key, value or [values]) or ('#', heading) or ('swatch', hex, text)."""
        for r in rows:
            if r[0] == '#':
                y += 0.08
                self.text(r[1], x, y, cap=0.08, weight=(800, 100), fill='#111111')
                self.line(x, y + 0.06, x + w, y + 0.06, w=0.006, col='#BBBBBB')
                y += 0.23
            elif r[0] == 'swatch':
                self.el.append(f'<rect x="{f5(x)}" y="{f5(y - 0.13)}" width="0.3" height="0.17" fill="{r[1]}" '
                               f'stroke="#888888" stroke-width="0.006"/>')
                self.text(f'{r[1]}   {r[2]}', x + 0.4, y, cap=0.068)
                y += 0.23
            else:
                vals = r[1] if isinstance(r[1], (list, tuple)) else [r[1]]
                self.text(r[0], x, y, cap=0.068, fill='#666666')
                for i, v in enumerate(vals):
                    self.text(v, x + col2, y + 0.175 * i, cap=0.068, fill='#111111')
                y += 0.175 * len(vals) + 0.06
        return y

    def save(self, stem, outdir=None):
        import cairosvg
        outdir = outdir or OUT_SPEC
        s = svg_doc('\n'.join(self.el), self.w, self.h, stem)
        with open(os.path.join(outdir, stem + '.svg'), 'w') as fh: fh.write(s)
        cairosvg.svg2png(bytestring=s.encode(), write_to=os.path.join(outdir, stem + '.png'), dpi=SPEC_DPI)
        cairosvg.svg2pdf(bytestring=s.encode(), write_to=os.path.join(outdir, stem + '.pdf'))


SUB = 'Rare Earth music video - DOT\'s jacket, stage-costume reproduction - lettering set exactly as in the video'


def em_tracking(track_caps, cap_u, upm):
    """A gap given in cap heights, as Illustrator tracking (1/1000 em)."""
    return 1000 * track_caps * cap_u / upm


def colour_rows(*keys):
    names = {'pale_blue': 'pale blue (dots)', 'ink': 'ink black (ring, lettering)', 'field': 'patch field (white)',
             'orange': 'orange stripes (reference only)'}
    return [('#', 'COLOURS')] + [('swatch', COLOURS[k], names[k]) for k in keys]


def spec_patch(body, W, H, m):
    sh = Sheet('SLEEVE PATCH  -  1420 / MHz', SUB + '. Not to scale: print the SVG at 100%.')
    P = sh.place(body, W, H, (1.1, 1.8, 4.9, 4.9))
    c, k = m['c'], m['k']
    cx, cy = P(c, c)
    sh.hdim(P(0, 0)[0], P(W, 0)[0], P(0, H)[1] + 0.35, 'patch field Ø ' + dimtxt(W), ext=(cy, cy), above=False)
    sh.hdim(P(c - m['ro'], 0)[0], P(c + m['ro'], 0)[0], P(0, 0)[1] - 0.2, 'ring outer Ø ' + dimtxt(2 * m['ro']),
            ext=(cy, cy))
    # ring thickness across the ring at 45 deg, lower right, with a leader out to clear paper
    u = (math.sqrt(0.5), math.sqrt(0.5))
    pi = P(c + m['ri'] * u[0], c + m['ri'] * u[1])
    po = P(c + m['ro'] * u[0], c + m['ro'] * u[1])
    ang = math.atan2(u[1], u[0])
    sh.line(pi[0] - 0.1 * u[0], pi[1] - 0.1 * u[1], po[0] + 0.45 * u[0], po[1] + 0.45 * u[1])
    sh.arrow(pi[0], pi[1], ang); sh.arrow(po[0], po[1], ang + math.pi)
    ex, ey = po[0] + 0.45 * u[0], po[1] + 0.45 * u[1]
    sh.line(ex, ey, ex + 0.25, ey)
    sh.text('ring thickness ' + dimtxt(m['ro'] - m['ri']), ex + 0.3, ey + 0.035, fill=DIM, bg=True)
    for i, L in enumerate(m['lines']):
        b = L['bounds']
        top, base = L['base'] - L['cap'], L['base']
        xl = P(b[0], 0)[0] - 0.2
        sh.vdim(P(0, top)[1], P(0, base)[1], xl, f'cap {L["cap"]:.3f} in ({cm(L["cap"]):.2f} cm)', side='left',
                ext=(P(b[0], 0)[0] - 0.03, P(b[0], 0)[0] - 0.03))
        yl = P(0, base)[1] + 0.2 if i == 1 else P(0, top)[1] - 0.14
        sh.hdim(P(b[0], 0)[0], P(b[2], 0)[0], yl, f'{L["text"]} ink width {dimtxt(b[2] - b[0])}', above=(i == 0))
    l0, l1 = m['lines']
    xg = P(max(l0['bounds'][2], l1['bounds'][2]), 0)[0] + 0.12
    sh.vdim(P(0, l0['base'])[1], P(0, l1['base'] - l1['cap'])[1], xg, f'gap {l1["base"] - l1["cap"] - l0["base"]:.3f} in',
            side='right', outside=True, ext=(P(l0['bounds'][2], 0)[0], P(l1['bounds'][2], 0)[0]))
    rows = [('#', 'SIZES'),
            ('patch field', f'Ø {dimtxt(W)}  (cut edge)'),
            ('ring outer / inner', [f'Ø {dimtxt(2 * m["ro"])}', f'Ø {dimtxt(2 * m["ri"])}']),
            ('ring thickness', f'{dimtxt(m["ro"] - m["ri"])}'),
            ('edge hairline', f'{SIZES["patch_edge_line"]:.3f} in, at the field edge'),
            ('design unit r', f'{dimtxt(k)}  (ring centre-line radius)'),
            ('#', 'LETTERING  (outlined; font Archivo, SIL OFL)')]
    for L in m['lines']:
        ptsz = L['cap'] * 72 * L['upm'] / L['capu']
        ctr = -L['cv_r'] * k
        rows += [(f'"{L["text"]}"', [f'Archivo  wght {L["wght"]}, wdth {L["wdth"]}  ({ptsz:.1f} pt)',
                                    f'cap {dimtxt(L["cap"])} = {L["cap_r"]} r',
                                    f'cap centre {abs(ctr):.3f} in {"above" if ctr > 0 else "below"} patch centre',
                                    f'tracking {L["tr_r"]} r = {L["track"]:.4f} in '
                                    f'(= {em_tracking(L["tr_r"] / L["cap_r"], L["capu"], L["upm"]):.0f}/1000 em)'])]
    rows += [('bold', [f'+{m["off"]:.4f} in per side, round joins (baked in).',
                       f'If typed: stroke {2 * m["off"] * 72:.2f} pt, same colour, round join']),
             ('kerning / centring', 'kerning 0; each line centred on the patch'),
             ('#', 'PLACEMENT'), ('', PLACEMENT['patch'])]
    rows += colour_rows('ink', 'field')
    sh.table(6.55, 1.5, rows)
    sh.save('spec_sleeve_patch_1420MHz')


def spec_back(body, W, H, m):
    sh = Sheet('BACK  -  PALE-BLUE DOT + RARE EARTH', SUB + '. Not to scale: print the SVGs at 100%.')
    P = sh.place(body, W, H, (1.3, 1.8, 4.5, 5.8))
    x0, y0 = P(0, 0); x1, y1 = P(W, H)
    cxp = P(m['cx'], 0)[0]
    lx0, lx1 = P(m['cx'] - m['W'] / 2, 0)[0], P(m['cx'] + m['W'] / 2, 0)[0]
    sh.hdim(P(m['cx'] - m['Dd'] / 2, 0)[0], P(m['cx'] + m['Dd'] / 2, 0)[0], y0 - 0.2, 'dot Ø ' + dimtxt(m['Dd']),
            ext=(P(0, m['Dd'] / 2)[1], P(0, m['Dd'] / 2)[1]))
    sh.hdim(lx0, lx1, y1 + 0.3, 'line length ' + dimtxt(m['W']), ext=(y1, y1), above=False)
    xr = max(lx1, P(m['cx'] + m['Dd'] / 2, 0)[0]) + 0.25
    sh.vdim(P(0, m['Dd'])[1], P(0, m['ly'])[1], xr, 'gap ' + dimtxt(m['gap']), outside=True, ext=(cxp, lx1))
    sh.vdim(P(0, m['ly'])[1], y1, xr, 'cap ' + dimtxt(m['cap']), outside=True, ext=(lx1, lx1))
    sh.vdim(y0, y1, x0 - 0.3, 'overall ' + f'{H:.3f} in', side='left', ext=(cxp, lx0))
    sh.line(cxp, y0 - 0.1, cxp, y1 + 0.1, w=0.006, dash='0.08 0.04 0.02 0.04')
    sh.text('CL', cxp + 0.07, y0 + 0.25, fill=DIM)
    em = em_tracking(BACK_TRACK, m['capu'], m['upm'])
    ptsz = m['cap'] * 72 * m['upm'] / m['capu']
    rows = [('#', 'SIZES'),
            ('dot', f'Ø {dimtxt(m["Dd"])}'),
            ('gap dot - caps', dimtxt(m['gap'])),
            ('cap height', [dimtxt(m['cap']), f'(= line length / {BACK_LINE_CAPS})']),
            ('line length (ink)', dimtxt(m['W'])),
            ('dot centre - cap top', dimtxt(m['Dd'] / 2 + m['gap'])),
            ('overall height', dimtxt(H)),
            ('alignment', 'lettering ink centred on the dot axis (CL)'),
            ('#', 'LETTERING  (outlined; font Archivo, SIL OFL)'),
            ('"RARE EARTH"', [f'Archivo  wght {BACK_FONT[1]}, wdth {BACK_FONT[2]}  ({ptsz:.1f} pt)',
                              'all caps, no bold, kerning 0',
                              f'tracking {BACK_TRACK:+.4f} cap = {m["track"]:+.4f} in per gap',
                              f'(= {em:+.1f}/1000 em): line = {BACK_LINE_CAPS} cap heights']),
            ('#', 'PLACEMENT'), ('', PLACEMENT['back'])]
    rows += colour_rows('pale_blue', 'ink', 'orange')
    sh.table(6.55, 1.5, rows)
    sh.save('spec_back_dot_rare_earth')


def spec_chest(body, W, H):
    D = SIZES['chest_dot_diameter']
    sh = Sheet('LEFT CHEST  -  PALE-BLUE DOT', SUB + '. The dot is drawn 1:1 when this PDF is printed at 100%.')
    P = sh.place(body, W, H, (1.2, 2.2, 4.0, 4.0))
    x0, y0 = P(0, 0); x1, y1 = P(W, H)
    note = '' if sh.s == 1 else f' (drawn at {sh.s:.0%})'
    sh.hdim(x0, x1, y1 + 0.35, 'Ø ' + dimtxt(D) + note, ext=((y0 + y1) / 2, (y0 + y1) / 2), above=False)
    sh.vdim(y0, y1, x1 + 0.3, 'Ø ' + dimtxt(D), ext=((x0 + x1) / 2, (x0 + x1) / 2))
    rows = [('#', 'SIZES'), ('dot', f'Ø {dimtxt(D)}'), ('shape', 'solid circle, no outline'),
            ('#', 'PLACEMENT'), ('', PLACEMENT['chest'])]
    rows += colour_rows('pale_blue', 'orange')
    sh.table(6.55, 1.5, rows)
    sh.save('spec_chest_dot')


# --------------------------------------------------------------------------------------- actual-size templates
LETTER = (8.5, 11.0)
T_MARGIN, T_HEAD, T_FOOT, T_OVERLAP = 0.4, 0.55, 1.45, 0.5


def outline_body(body, w=0.012):
    """The artwork as cut/trace lines: every filled shape drawn as a thin black outline."""
    return re.sub(r'fill="#[0-9A-Fa-f]{6}"', f'fill="none" stroke="#000000" stroke-width="{w}"', body)


def tiled_pages(key, title, body, W, H):
    """Artwork at 1:1 on letter pages, tiled with T_OVERLAP when it does not fit; each page has a 1-in calibration
    square, a 1-in grid in artwork coordinates (to line tiles up) and its tile name. Returns page SVG strings."""
    best = None
    for pw, ph in (LETTER, LETTER[::-1]):
        aw, ah = pw - 2 * T_MARGIN, ph - T_MARGIN - T_HEAD - T_FOOT
        cols = 1 if W <= aw else math.ceil((W - T_OVERLAP) / (aw - T_OVERLAP))
        rows = 1 if H <= ah else math.ceil((H - T_OVERLAP) / (ah - T_OVERLAP))
        if best is None or cols * rows < best[0]: best = (cols * rows, pw, ph, aw, ah, cols, rows)
    _, pw, ph, aw, ah, cols, rows = best
    sx, sy = aw - T_OVERLAP, ah - T_OVERLAP
    spanx = W if cols == 1 else cols * sx + T_OVERLAP
    spany = H if rows == 1 else rows * sy + T_OVERLAP
    offx, offy = (spanx - W) / 2, (spany - H) / 2
    tint = body.replace('<g id=', '<g opacity="0.28" id=') if '<g id=' in body else f'<g opacity="0.28">{body}</g>'
    pages = []
    for j in range(rows):
        for i in range(cols):
            ax, ay = T_MARGIN, T_MARGIN + T_HEAD
            if cols == 1: ax += (aw - W) / 2
            if rows == 1: ay += (ah - H) / 2
            # artwork coordinate shown at the content area's top-left
            ux, uy = (i * sx - offx, j * sy - offy) if cols * rows > 1 else (0, 0)
            el = [f'<rect width="{pw}" height="{ph}" fill="#FFFFFF"/>',
                  f'<clipPath id="clip"><rect x="{T_MARGIN}" y="{T_MARGIN + T_HEAD}" width="{f5(aw)}" height="{f5(ah)}"/></clipPath>',
                  f'<g clip-path="url(#clip)"><g transform="translate({f5(ax - ux)} {f5(ay - uy)})">']
            if cols * rows > 1:
                g = []
                for gx in range(int(math.floor(-offx)) - 1, int(math.ceil(W + offx)) + 2):
                    g.append(f'M{gx} {f5(-offy - 1)} V{f5(H + offy + 1)}')
                for gy in range(int(math.floor(-offy)) - 1, int(math.ceil(H + offy)) + 2):
                    g.append(f'M{f5(-offx - 1)} {gy} H{f5(W + offx + 1)}')
                el.append(f'<path d="{" ".join(g)}" stroke="#C8C8C8" stroke-width="0.008" fill="none"/>')
                # neighbours' edges: where to overlap
                for ii in range(cols if cols > 1 else 0):
                    for e in (ii * sx - offx, ii * sx - offx + aw):
                        el.append(f'<path d="M{f5(e)} {f5(-offy - 1)} V{f5(H + offy + 1)}" stroke="#E0457B" '
                                  f'stroke-width="0.01" stroke-dasharray="0.1 0.06"/>')
                for jj in range(rows if rows > 1 else 0):
                    for e in (jj * sy - offy, jj * sy - offy + ah):
                        el.append(f'<path d="M{f5(-offx - 1)} {f5(e)} H{f5(W + offx + 1)}" stroke="#E0457B" '
                                  f'stroke-width="0.01" stroke-dasharray="0.1 0.06"/>')
            el.append(tint)
            el.append(outline_body(body))
            el.append('</g></g>')
            el.append(f'<rect x="{T_MARGIN}" y="{T_MARGIN + T_HEAD}" width="{f5(aw)}" height="{f5(ah)}" fill="none" '
                      f'stroke="#999999" stroke-width="0.008"/>')
            name = f'{key}{j * cols + i + 1}'
            head = title if cols * rows == 1 else f'{title}  -  page {name} of {cols * rows} (row {j + 1}, col {i + 1})'
            p, _ = label(head, 0.12, T_MARGIN, T_MARGIN + 0.17, weight=(800, 100), fill='#111111'); el.append(p)
            sub = 'ACTUAL SIZE - print at 100% / "actual size" (no fit-to-page). Check the 1-in square first.'
            if cols * rows > 1:
                sub += f'  Tiles overlap {T_OVERLAP} in: line up the grey 1-in grid; pink dashes = neighbouring page edges.'
            p, _ = label(sub, 0.06, T_MARGIN, T_MARGIN + 0.38, fill='#444444'); el.append(p)
            # calibration square
            qy = ph - T_FOOT + 0.1
            el.append(f'<rect x="{T_MARGIN}" y="{f5(qy)}" width="1" height="1" fill="none" stroke="#000000" stroke-width="0.01"/>')
            p, _ = label('1 in', 0.09, T_MARGIN + 0.5, qy + 0.55, 'middle', weight=(700, 100)); el.append(p)
            el.append(f'<path d="M{T_MARGIN + 1.3} {f5(qy + 1)} h{f5(2 / 2.54 * 2.5)}" stroke="#000000" stroke-width="0.01"/>')
            el.append(f'<path d="M{T_MARGIN + 1.3} {f5(qy + 0.9)} v0.1 M{f5(T_MARGIN + 1.3 + 5 / 2.54)} {f5(qy + 0.9)} v0.1" '
                      f'stroke="#000000" stroke-width="0.01"/>')
            p, _ = label('5 cm', 0.07, T_MARGIN + 1.3 + 2.5 / 2.54, qy + 0.85, 'middle'); el.append(p)
            info = f'artwork {W:.3f} x {H:.3f} in ({cm(W):.1f} x {cm(H):.1f} cm)'
            p, _ = label(info, 0.065, pw - T_MARGIN, qy + 0.35, 'end', fill='#444444'); el.append(p)
            p, _ = label('outline = cut/trace line; tint = fill', 0.065, pw - T_MARGIN, qy + 0.55, 'end', fill='#444444'); el.append(p)
            pages.append((svg_doc('\n'.join(el), pw, ph, head), name))
    return pages


def write_templates(items):
    import cairosvg
    from pypdf import PdfWriter, PdfReader
    import io
    os.makedirs(OUT_TPL, exist_ok=True)
    for f in os.listdir(OUT_TPL):
        if f.startswith('page_'): os.remove(os.path.join(OUT_TPL, f))
    writer = PdfWriter()
    n = 0
    for key, title, body, W, H in items:
        for svg, name in tiled_pages(key, title, body, W, H):
            n += 1
            cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT_TPL, f'page_{n:02d}_{name}.png'), dpi=TEMPLATE_DPI)
            for pg in PdfReader(io.BytesIO(cairosvg.svg2pdf(bytestring=svg.encode()))).pages: writer.add_page(pg)
    with open(os.path.join(OUT_TPL, 'actual_size_templates_letter.pdf'), 'wb') as fh: writer.write(fh)
    return n


# ------------------------------------------------------------------------------------------------------- fonts out
def write_fonts():
    os.makedirs(OUT_FONTS, exist_ok=True)
    shutil.copy(VF_PATH, OUT_FONTS)
    shutil.copy(os.path.join(FONT_DIR, 'OFL-archivo.txt'), OUT_FONTS)
    jobs = [(f'Patch{t}', w, d) for t, w, d, *_ in PATCH_LINES] + [('BackRareEarth', BACK_FONT[1], BACK_FONT[2])]
    for tag, w, d in jobs:
        f = instancer.instantiateVariableFont(TTFont(VF_PATH), {'wght': w, 'wdth': d},
                                              overlap=instancer.OverlapMode.REMOVE)
        fam = f'Archivo {tag} w{w} wd{d}'
        ps = f'Archivo{tag}-w{w}wd{d}'
        nt = f['name']
        for nid in (16, 17, 21, 22, 25): nt.removeNames(nameID=nid)
        for nid, val in ((1, fam), (2, 'Regular'), (3, f'{ps};costume-instance'), (4, fam), (6, ps)):
            nt.setName(val, nid, 3, 1, 0x409)
            nt.setName(val, nid, 1, 0, 0)
        f['OS/2'].usWeightClass = 400
        f['OS/2'].fsSelection = (f['OS/2'].fsSelection & ~0b1100001) | 0b1000000   # Regular
        f['head'].macStyle = 0
        f.save(os.path.join(OUT_FONTS, f'Archivo-{tag}-w{w}-wd{d}.ttf'))


# ------------------------------------------------------------------------------------------------------------ main
def main():
    for d in (OUT_ART, OUT_SPEC): os.makedirs(d, exist_ok=True)
    pb, pw, ph, pm = patch_art()
    write_svg(os.path.join(OUT_ART, 'sleeve_patch_1420MHz.svg'), pb, pw, ph, 'Sleeve patch 1420 MHz')

    ld, lw, lh, lmeta = lettering_art()
    lb = f'<g id="rare_earth"><path fill="{COLOURS["ink"]}" d="{ld}"/></g>'
    write_svg(os.path.join(OUT_ART, 'back_rare_earth_lettering.svg'), lb, lw, lh, 'RARE EARTH back lettering')

    bb, bw, bh, bm = back_art()
    write_svg(os.path.join(OUT_ART, 'back_dot_and_lettering.svg'), bb, bw, bh, 'Back dot and RARE EARTH')

    for name, key in (('chest_dot', 'chest_dot_diameter'), ('back_dot', 'back_dot_diameter')):
        D = SIZES[key]
        b, w, h = dot_art(D)
        write_svg(os.path.join(OUT_ART, f'{name}.svg'), f'<g id="{name}">{b}</g>', w, h, name.replace('_', ' '))
        tb, tw, th = template_art(name.upper().replace('_', ' '), D)
        write_svg(os.path.join(OUT_ART, f'{name}_template.svg'), tb, tw, th, name.replace('_', ' ') + ' template', dpi=150)

    spec_patch(pb, pw, ph, pm)
    spec_back(bb, bw, bh, bm)
    cb, cw, ch = dot_art(SIZES['chest_dot_diameter'])
    spec_chest(cb, cw, ch)

    n = write_templates([('P', 'SLEEVE PATCH 1420 / MHz', pb, pw, ph),
                         ('C', 'LEFT CHEST DOT', f'<g id="chest_dot">{cb}</g>', cw, ch),
                         ('B', 'BACK DOT + RARE EARTH', bb, bw, bh)])
    write_fonts()

    print(f'patch: field Ø {pw:.4f} in, r = {pm["k"]:.4f} in, ring {pm["ro"] - pm["ri"]:.4f} in '
          f'(= {(pm["ro"] - pm["ri"]) / pm["k"]:.4f} r, {(pm["ro"] - pm["ri"]) / (2 * pm["ro"]):.4f} of ring outer Ø; '
          f'sheet {SHEET_RING_T_OVER_OUTER_D}), bold +{pm["off"]:.4f} in/side')
    for L in pm['lines']:
        b = L['bounds']
        print(f'  {L["text"]}: cap {L["cap"]:.4f} in, ink {b[2] - b[0]:.4f} x {b[3] - b[1]:.4f} in, '
              f'ink centre offset {((b[0] + b[2]) / 2 - pm["c"]):+.4f} in')
    print(f'back: cap {bm["cap"]:.4f} in, track {BACK_TRACK:+.5f} cap = {bm["track"]:+.5f} in (natural {BACK_NATURAL:.4f} cap; '
          f'the video\'s raster measure gives {BACK_TRACK_RASTER}), line {bm["W"]:.4f} in = {bm["W"] / bm["cap"]:.3f} caps, '
          f'overall {bw:.3f} x {bh:.3f} in')
    print(f'templates: {n} letter pages')


if __name__ == '__main__':
    main()
