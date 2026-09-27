"""The pale-blue dot on the back of DOT's jacket, in the one take that drew it faintly (se03, "our planet waits", 1:07).

The character sheet and every other back view (the poster, the pull-back) show a big solid pale-blue dot on the back
of the white jacket. se03 drew only a faint teal ring there, under her hair. The ring's centre and radius were read off
the frames by hand at a few keys (the camera pulls back, so it shrinks) and interpolated; the dot is filled in pale
in the drawn ring's own blue (the dot's colour in this shot's night light), with a thin rim and the hair left in
front of it. RARE EARTH is set under it, in the gap above the crop top's hem, until it is too small to print.

  python3 pipeline/plate_fixes/fix_backdot.py     # writes se03_..._dot.mp4 next to the take
"""
import os
import subprocess

import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lettering import font, set_lines, warp_layer, composite  # noqa: E402
from fix_lettering import BACK_FONT, BACK_TEXT  # noqa: E402

CLIPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'base_clips')
SRC = 'se03_crowd_lights__698eb06939.mp4'
KEYS = [(0, 630, 560, 57), (14, 638, 510, 46), (28, 640, 475, 34), (42, 640, 445, 24), (56, 638, 440, 18),
        (120, 600, 470, 6)]                                # (frame, centre x, y, radius), plate px


def main():
    cap = cv2.VideoCapture(os.path.join(CLIPS, SRC))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok: break
        frames.append(f)
    k = np.array(KEYS, float)
    # RARE EARTH under the dot, as on the sheet and in the pull-back (fix_lettering.py's face and tracking): here the
    # dot sits just above the crop top's hem, so the line is set in the gap between them, measured in every frame
    f_ = font(BACK_FONT[0], 200, weight=BACK_FONT[1], width=BACK_FONT[2])
    probe, _ = set_lines([(BACK_TEXT, f_, 1.0, 0.0, 0.0)], half=8)
    xs = np.nonzero(probe.max(0) > 0.5)[0]
    # set heavier than the pull-back's: here the jacket is small in frame, and the ink redraw would break thin strokes up
    layer = set_lines([(BACK_TEXT, f_, 1.0, 0.0, (10.7 - (xs.max() - xs.min()) / 256) / (len(BACK_TEXT) - 1))], half=8,
                      bold=0.015)
    out = []
    for i, f in enumerate(frames):
        cx, cy, r = (np.interp(i, k[:, 0], k[:, c]) for c in (1, 2, 3))
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
        # the take's ring sits low and off centre: paint it out, and place the dot as in the pull-back, centred on the
        # back between the jacket's edges and higher up, with RARE EARTH under it
        V0, S0 = hsv[..., 2] / 255, hsv[..., 1] / 255
        hair0 = (V0 < 0.30) | ((S0 > 0.45) & (V0 > 0.5))
        ann0 = np.zeros(f.shape[:2], np.uint8)
        cv2.circle(ann0, (int(cx), int(cy)), int(r), 1, -1)
        cv2.circle(ann0, (int(cx), int(cy)), int(r * 0.72), 0, -1)
        sel0 = (ann0 > 0) & ~hair0 & (S0 > 0.2)
        ring_hsv = np.median(hsv[sel0], 0) if sel0.sum() > 5 else np.array([102, 177, 101], np.float32)
        old = np.zeros(f.shape[:2], np.uint8)
        cv2.circle(old, (int(cx), int(cy)), int(r * 1.25) + 3, 1, -1)
        old[hair0] = 0
        f = cv2.inpaint(f, old, 5, cv2.INPAINT_TELEA)
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
        row = hsv[int(cy)]
        jk = (row[:, 2] > 0.38 * 255) & (row[:, 1] < 0.4 * 255)
        l = int(cx)
        while l > 0 and (jk[l - 1] or hair0[int(cy), l - 1]): l -= 1
        rr = int(cx)
        while rr < f.shape[1] - 1 and (jk[rr + 1] or hair0[int(cy), rr + 1]): rr += 1
        cx = 0.5 * (l + rr)
        cy = cy - 0.25 * r
        disc = np.zeros(f.shape[:2], np.float32)
        cv2.circle(disc, (int(round(cx * 4)), int(round(cy * 4))), int(round(r * 4)), 1, -1, cv2.LINE_AA, shift=2)
        disc = cv2.GaussianBlur(disc, (0, 0), 0.8)
        # everything in the disc but the hair (dark, or its saturated blue highlight) becomes the dot, the drawn ring
        # included; the dot's lightness is the jacket's around it, so it sits in the plate's light
        V, S = hsv[..., 2] / 255, hsv[..., 1] / 255
        hair = hair0
        keep = cv2.GaussianBlur((~hair).astype(np.float32), (0, 0), 0.7)
        a = disc * keep
        # the colour of the ring the take drew there: the dot's blue as it looks in this shot's night light (a lighter
        # fill reads as lit by a light of its own); the plate's soft shading is kept across it
        shade = cv2.GaussianBlur(hsv[..., 2], (0, 0), max(2.0, r * 0.6)) / 255
        dot = hsv.copy()
        dot[..., 0] = ring_hsv[0]
        dot[..., 1] = ring_hsv[1]
        dot[..., 2] = np.clip(ring_hsv[2] * np.clip(shade / max(1e-3, np.median(shade[disc > 0.5])), 0.92, 1.05), 0, 255)
        # a thin dark rim, drawn like the sheet's outline, so the ink redraw gives the dot an edge
        rim = np.zeros(f.shape[:2], np.float32)
        cv2.circle(rim, (int(round(cx * 4)), int(round(cy * 4))), int(round(r * 4)), 1, max(1, int(r / 18)), cv2.LINE_AA, shift=2)
        dot[..., 2] = dot[..., 2] * (1 - 0.55 * np.clip(rim, 0, 1))
        dot = cv2.cvtColor(dot.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        g = np.clip(f * (1 - a[..., None]) + dot * a[..., None], 0, 255).astype(np.uint8)
        cap = 0.2 * r
        if cap >= 2.5:
            ty = cy + r + 1.3 * cap
            alpha, bx = warp_layer(layer, cap * np.eye(2), np.array([cx, ty]), g.shape, soften=0.5)
            if alpha is not None:
                jacket = g[int(ty) - 2:int(ty) + 3, int(cx - 6 * cap):int(cx + 6 * cap)].reshape(-1, 3).astype(float)
                composite(g, alpha, bx, 0.22 * np.median(jacket, 0))          # dark ink, in the jacket's light
        out.append(g)
    h, w = out[0].shape[:2]
    dst = os.path.join(CLIPS, SRC.replace('.mp4', '_dot.mp4'))
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                          '-s', f'{w}x{h}', '-r', '24', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                          '-pix_fmt', 'yuv420p', dst], stdin=subprocess.PIPE)
    for f in out: p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    print(dst)


if __name__ == '__main__':
    main()
