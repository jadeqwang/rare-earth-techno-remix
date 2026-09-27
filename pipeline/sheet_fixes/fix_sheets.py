"""Pass 3 corrections to the generated design sheets (docs/PROCESS.md §3c).

Every sheet is read as it was generated (git commit 74a292a) and the corrected version is written to design/,
so this can be re-run. Labels are painted out and set again in matching lettering, or rebuilt from the sheet's
own glyphs. The artwork is untouched except for the two Earth sheets' array panels, which are replaced by a new
picture of the Allen Telescope Array (design/sources/ata_hat_creek_gpt_image_2_5.jpg; GPT Image 2.5, prompt in
pipeline/prompts/world_earth_ata_v1.txt).

    python3 pipeline/sheet_fixes/fix_sheets.py        # from anywhere; needs numpy, opencv, pillow
"""
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet_patch as P  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BASE = '74a292a'
ATA = os.path.join(ROOT, 'design', 'sources', 'ata_hat_creek_gpt_image_2_5.jpg')
MONO = 'JetBrainsMono-VF.ttf'
TYPEWRITER = '/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf'


def original(name):
    data = subprocess.run(['git', '-C', ROOT, 'show', f'{BASE}:design/{name}'], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(data)).convert('RGB')


def save(im, name):
    im.save(os.path.join(ROOT, 'design', name), quality=93, optimize=True)
    print('wrote design/' + name)


def tracking_for(s, target, fontname, cap, **ax):
    """Tracking that makes s set in this font as wide as the original lettering was."""
    return (target - P.text_width(P.cap_font(fontname, cap, **ax), s)) / (len(s) - 1)


def echo_sheet():
    # "ETZ-1715 b" read like a real catalogue name (1,715 is Kaltenegger & Faherty's star count): the world is Echo.
    im = original('world_etz1715b_sheet.jpg')
    P.fill(im, (18, 10, 312, 52), (17, 23, 33))
    P.draw_hq(im, 23, 48, 'ECHO', 'Archivo-VF.ttf', 34, (228, 230, 236), tracking=9, wght=250, wdth=100)
    # "KX-209 (coral giant)": a giant is a poor host for a living world; Echo orbits an orange dwarf, 217 ly away
    P.fill(im, (960, 16, 1166, 27), P.ring_color(im, (960, 16, 1165, 25)))
    P.draw_hq(im, 962, 25, 'STAR: ORANGE DWARF, 217 LY', 'Archivo-VF.ttf', 6, (170, 175, 188), tracking=0.95, wght=480, wdth=112)
    # sky study: at 217 ly the Sun is about magnitude 8.9, invisible to the naked eye, so the star isn't labelled Sol
    P.inpaint(im, (1486, 721, 1508, 737), light=True, thr=25, grow=2, radius=3)
    P.fill(im, (20, 988, 118, 1004), P.ring_color(im, (20, 988, 118, 1004)))
    P.draw_hq(im, 24, 1000, 'ECHO', 'Archivo-VF.ttf', 8, (206, 210, 218), tracking=5.2, wght=450, wdth=112)
    save(im, 'world_echo_sheet.jpg')


def earth_sheet(ata):
    im = original('world_earth_sheet.jpg')
    # THE ARRAY was labelled Owens Valley and drawn with big centre-fed dishes. The array in the video is the Allen
    # Telescope Array: 42 offset-Gregorian 6.1 m dishes at Hat Creek, under Lassen Peak. New panel, 1085x434 at 451,0.
    im.paste(ata.crop((0, 150, 1536, 150 + 614)).resize((1085, 434), Image.LANCZOS), (451, 0))
    # the sheet's labels are a narrow geometric sans with wide tracking: titles ~2.8 px, subtitles ~1.9 px
    ax = dict(wght=540, wdth=92)
    P.draw_hq(im, 466, 24, 'THE ARRAY', 'Archivo-VF.ttf', 10, (242, 246, 255),
              tracking=tracking_for('THE ARRAY', 97, 'Archivo-VF.ttf', 10, **ax), **ax)
    ax2 = dict(wght=450, wdth=80)
    sub = tracking_for('OWENS VALLEY, CA', 119, 'Archivo-VF.ttf', 8, **ax2)
    P.draw_hq(im, 466, 43, 'HAT CREEK, CA', 'Archivo-VF.ttf', 8, (184, 191, 209), tracking=sub, **ax2)
    # the panel shows Starship and its chopstick tower, which launch from Starbase, Texas
    P.inpaint(im, (1056, 471, 1170, 485), light=True, thr=35, grow=2, radius=4)
    P.draw_hq(im, 1060, 482, 'STARBASE, TX', 'Archivo-VF.ttf', 8, (182, 204, 244), tracking=sub, **ax2)
    save(im, 'world_earth_sheet.jpg')


def earth_sheet_alt(ata):
    im = original('world_earth_sheet_alt.jpg')
    ink, bg = (17, 17, 20), (232, 232, 232)

    def fit_wdth(s, target, cap, wght, lo=62, hi=125):
        for _ in range(18):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if P.text_width(P.cap_font('Archivo-VF.ttf', cap, wght=wght, wdth=mid), s) < target else (lo, mid)
        return (lo + hi) / 2

    # the title named a video that doesn't exist ('Celestial Harmony')
    wd = fit_wdth('ENVIRONMENT DESIGN SHEET: ‘CELESTIAL HARMONY’ - EARTH LOCATIONS (ANIME SCI-FI MUSIC VIDEO)', 2510, 45, 600)
    P.fill(im, (48, 26, 2600, 100), bg)
    P.draw_hq(im, 55, 81, 'ENVIRONMENT DESIGN SHEET: ‘RARE EARTH’ - EARTH LOCATIONS (ANIME SCI-FI MUSIC VIDEO)',
              'Archivo-VF.ttf', 45, ink, tracking=0, k=2, wght=600, wdth=wd)
    # panel 2 (inner image 893x603 at 55,822) and its caption: the Allen Telescope Array at Hat Creek
    im.paste(ata.crop((10, 0, 1526, 1024)).resize((893, 603), Image.LANCZOS), (55, 822))
    P.fill(im, (50, 1434, 960, 1522), bg)
    x = P.draw_hq(im, 59, 1469, '2) THE ARRAY', 'Archivo-VF.ttf', 26, ink, k=2, wght=680, wdth=wd)
    P.draw_hq(im, x, 1469, ' — The Allen Telescope Array’s 42 dishes at Hat Creek,', 'Archivo-VF.ttf', 26, ink, k=2, wght=420, wdth=wd)
    P.draw_hq(im, 59, 1507, 'California, under the Milky Way.', 'Archivo-VF.ttf', 26, ink, k=2, wght=420, wdth=wd)
    save(im, 'world_earth_sheet_alt.jpg')


def dot_sheet(name):
    """The 1420 MHz patch is drawn on DOT's LEFT arm in every view, and the Yagi drawn in the detail box has 4
    elements. Both fixes reuse the sheet's own lettering: LEFT from "LEFT CHEST", SLEEVE from "RIGHT SLEEVE",
    the 4 from "(1420 MHz)"."""
    im = original(name)
    L = np.asarray(im.convert('L')).astype(int)

    def words(x0, x1, y0=192, y1=202, gap=6):
        xs = np.where((L[y0:y1, x0:x1] < 150).any(0))[0]
        out, s, p = [], xs[0], xs[0]
        for x in xs[1:]:
            if x - p > gap:
                out.append((x0 + s, x0 + p))
                s = x
            p = x
        out.append((x0 + s, x0 + p))
        return out

    (l0, l1), _ = words(1190, 1296)          # LEFT | CHEST
    (r0, r1), (s0, s1) = words(1296, 1400)   # RIGHT | SLEEVE
    gap = s0 - r1 - 1
    left, sleeve = im.crop((l0 - 1, 189, l1 + 2, 205)), im.crop((s0 - 1, 189, s1 + 2, 205))
    paper = tuple(int(v) for v in np.median(np.asarray(im.crop((r0 - 6, 189, s1 + 6, 205))).reshape(-1, 3), 0))
    im.paste(Image.new('RGB', (s1 - r0 + 13, 16), paper), (r0 - 6, 189))
    w = (l1 - l0 + 1) + gap + (s1 - s0 + 1)
    x = round((r0 + s1) / 2 - w / 2)
    im.paste(left, (x - 1, 189))
    im.paste(sleeve, (x + (l1 - l0 + 1) + gap - 1, 189))

    a = np.asarray(im).astype(float)
    ink = np.percentile(a[677:686, 1202:1260].reshape(-1, 3), 4, axis=0)      # the ELEMENTS line's ink
    blank = a[676:688, 1350:1357].copy()
    a[676:688, 1190:1197] = blank                                              # remove the 5
    pbg = float(np.median(blank.mean(2)))
    src = a[204:216, 1322:1330].copy()                                         # the 4 of (1420 MHz)
    lum = src.mean(2)
    alpha = np.clip((pbg - 8 - lum) / (pbg - 8 - lum.min()), 0, 1)[..., None] ** 0.8
    y0, x0 = 204 + (685 - 213), 1322 + (1191 - 1323)                           # baseline and left edge of the 5
    a[y0:y0 + 12, x0:x0 + 8] = a[y0:y0 + 12, x0:x0 + 8] * (1 - alpha) + np.broadcast_to(ink, src.shape) * alpha
    save(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), name)


def style_board():
    im = original('style_board_signal_print.jpg')

    def mono(x, y, s, pitch, color, wght=420, cap=None):
        # JetBrains Mono advances 0.6 em, capitals 0.73 em; a taller original passes cap and keeps its pitch
        cap = cap or 0.73 / 0.6 * pitch
        return P.draw_hq(im, x, y, s, MONO, cap, color, tracking=pitch - 0.6 * cap / 0.73, wght=wght)

    # the version stamp and the readout were dated 2024; the board was made in September 2026
    P.erase_dark(im, (1434, 35, 1512, 48))
    mono(1437, 46, '2026.09.25', 7.0, (44, 41, 36))
    P.erase_dark(im, (1368, 327, 1428, 339))
    mono(1371, 337, '2026.09.25', 5.62, (26, 24, 19), wght=640, cap=7.7)
    # target: our fictional world, not a random real Kepler star (KIC 6923187)
    P.erase_dark(im, (1412, 340, 1492, 352))
    mono(1416, 350, 'ECHO', 5.62, (28, 25, 20), wght=640, cap=7.7)
    # 6EQUJ5 is the Wow! signal's intensity code, not a target
    P.erase_dark(im, (1392, 506, 1427, 518))
    mono(1395, 516, 'SIGNAL', 5.1, (40, 37, 30), wght=600, cap=7.2)
    # a beacon, not a reply
    P.erase_dark(im, (1449, 564, 1506, 576))
    mono(1452, 574, 'SIGNAL.', 5.8, (28, 26, 21), wght=560, cap=7.6)
    # the coordinates were Tokyo Tower's; the dish silhouette is the Allen Telescope Array at Hat Creek
    P.erase_dark(im, (1430, 934, 1506, 962), thr=30)
    mono(1433, 946, '40.8178° N', 6.35, (94, 89, 83))
    mono(1433, 960, '121.4730° W', 6.35, (90, 85, 79))
    # title-card specimens: the video's cards are Chinese and Russian (commit 66e5a8f), set in the fonts it uses
    P.erase_dark(im, (728, 758, 928, 806), thr=60, grow=2, radius=4)
    P.erase_dark(im, (970, 758, 1358, 806), thr=60, grow=2, radius=4)
    P.erase_dark(im, (728, 807, 845, 821), thr=35)
    P.erase_dark(im, (972, 807, 1100, 821), thr=35)
    P.cjk(im, 733, 763, '稀有地球', 39, (12, 11, 10))
    P.draw_hq(im, 976, 793, 'Уникальная Земля', 'Unbounded-VF.ttf', 22, (12, 11, 10), wght=800)
    mono(733, 817, '04 Chinese / Display', 6.0, (86, 82, 74))
    mono(977, 817, '05 Russian / Display', 6.0, (90, 86, 79))
    save(im, 'style_board_signal_print.jpg')


def style_board_flat():
    orig = original('style_board_signal_print_flat.jpg')
    im = orig.copy()

    def paper(dst_box, src_xy):
        x0, y0, x1, y1 = dst_box
        im.paste(orig.crop((src_xy[0], src_xy[1], src_xy[0] + x1 - x0, src_xy[1] + y1 - y0)), (x0, y0))

    # palette: Klein Blue is #1F2BD1 (not #1F2DD1) and Pale Blue Dot #9CCBFF (not #8CCBFF). The B is the one
    # in #8CCBFF; the 9 is the 6 of #F3EFE6 turned 180 degrees.
    paper((188, 363, 202, 387), (228, 363))
    P.transplant(im, orig, (590, 363, 604, 386), (188, 363))
    paper((554, 362, 567, 388), (636, 362))
    P.transplant(im, orig, (1620, 362, 1633, 387), (554, 362), rotate=True)
    # "monspace UI line": shift "space UI line" one cell right and copy in the o from "mon"
    region = orig.crop((1789, 684, 1954, 715))
    P.erase_dark(im, (1789, 684, 1970, 715), thr=40)
    P.transplant(im, region, (0, 0, region.width, region.height), (1801, 684))
    P.transplant(im, orig, (1764, 684, 1779, 715), (1789, 684))
    # specimens: Chinese and Russian title cards instead of Korean and Japanese
    P.erase_dark(im, (1745, 786, 1975, 818), thr=40)
    P.erase_dark(im, (1745, 816, 2665, 1000), thr=50, grow=2, radius=5)
    P.erase_dark(im, (1745, 1002, 1925, 1034), thr=40)
    P.erase_dark(im, (1745, 1034, 2665, 1130), thr=50, grow=2, radius=5)
    P.cjk(im, 1751, 821, '稀有地球', 172, (20, 19, 18), k=2)
    P.draw_hq(im, 1756, 1105, 'Уникальная Земля', 'Unbounded-VF.ttf', 52, (20, 19, 18), wght=800, k=2)
    P.draw_hq_x(im, 1754, 811, 'Chinese title card', MONO, 17.5, (38, 36, 33), pitch=12.4, wght=560)
    P.draw_hq_x(im, 1754, 1027, 'Russian title card', MONO, 17.5, (38, 36, 33), pitch=12.4, wght=560)
    # the printout's gibberish -> listening metadata; bullets kept, and the rows beside the red circle stay short
    P.erase_dark(im, (1008, 1080, 1152, 1146), thr=35, grow=2)
    P.erase_dark(im, (1008, 1147, 1350, 1214), thr=35, grow=2)
    for base, s in zip([1098, 1120, 1143, 1165, 1188, 1210],
                       ['SNR 23.4', 'INT 3600s', 'POL LCP', 'RX 1420.40575 MHz', 'TARGET ECHO', '2026.09.25 03:27:41 UTC']):
        P.draw_hq_x(im, 1014, base, s, TYPEWRITER, 13.2, (46, 44, 42), pitch=13.9)
    # caption c): light mode is mint and yellow neon on black, not the Earth inks
    P.erase_dark(im, (95, 1456, 775, 1491), thr=40)
    P.draw_hq_x(im, 101, 1482, 'c) LIGHT MODE - Mint Signal and Signal Yellow on black', MONO, 19, (18, 18, 18), pitch=12.05, wght=760)
    save(im, 'style_board_signal_print_flat.jpg')


if __name__ == '__main__':
    ata = Image.open(ATA).convert('RGB')
    echo_sheet()
    earth_sheet(ata)
    earth_sheet_alt(ata)
    dot_sheet('dot_character_sheet.jpg')
    dot_sheet('dot_character_sheet_v2_hime.jpg')
    style_board()
    style_board_flat()
