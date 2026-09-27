"""The pale-blue dot on the back of DOT's jacket, in the one take that drew it faintly (se03, "our planet waits", 1:07).

The character sheet and every other back view (the poster, the pull-back) show a big solid pale-blue dot on the back
of the white jacket. se03 drew only a faint teal ring there, under her hair. The ring's centre and radius were read off
the frames by hand at a few keys (the camera pulls back, so it shrinks) and interpolated; the dot is filled in pale
blue over the drawn ring, light enough for the renderer to ink it as its own patch, with a thin rim and the hair
left in front of it.

  python3 pipeline/plate_fixes/fix_backdot.py     # writes se03_..._dot.mp4 next to the take
"""
import os
import subprocess

import cv2
import numpy as np

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
    out = []
    for i, f in enumerate(frames):
        cx, cy, r = (np.interp(i, k[:, 0], k[:, c]) for c in (1, 2, 3))
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
        disc = np.zeros(f.shape[:2], np.float32)
        cv2.circle(disc, (int(round(cx * 4)), int(round(cy * 4))), int(round(r * 4)), 1, -1, cv2.LINE_AA, shift=2)
        disc = cv2.GaussianBlur(disc, (0, 0), 0.8)
        # everything in the disc but the hair (dark, or its saturated blue highlight) becomes the dot, the drawn ring
        # included; the dot's lightness is the jacket's around it, so it sits in the plate's light
        V, S = hsv[..., 2] / 255, hsv[..., 1] / 255
        hair = (V < 0.30) | ((S > 0.45) & (V > 0.5))
        keep = cv2.GaussianBlur((~hair).astype(np.float32), (0, 0), 0.7)
        a = disc * keep
        # lit like a printed patch: light enough that the renderer reads it as its own pale-blue ink, not the jacket's
        # night shadow (the jacket itself renders dark in this shot), with the plate's soft shading kept
        shade = cv2.GaussianBlur(hsv[..., 2], (0, 0), max(2.0, r * 0.6)) / 255
        dot = hsv.copy()
        dot[..., 0] = 105                                    # pale blue (#9CCBFF's hue, OpenCV scale)
        dot[..., 1] = 0.42 * 255
        dot[..., 2] = np.clip(0.97 * np.clip(shade / max(1e-3, np.median(shade[disc > 0.5])), 0.92, 1.03), 0, 1) * 255
        # a thin dark rim, drawn like the sheet's outline, so the ink redraw gives the dot an edge
        rim = np.zeros(f.shape[:2], np.float32)
        cv2.circle(rim, (int(round(cx * 4)), int(round(cy * 4))), int(round(r * 4)), 1, max(1, int(r / 18)), cv2.LINE_AA, shift=2)
        dot[..., 2] = dot[..., 2] * (1 - 0.55 * np.clip(rim, 0, 1))
        dot = cv2.cvtColor(dot.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        out.append(np.clip(f * (1 - a[..., None]) + dot * a[..., None], 0, 255).astype(np.uint8))
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
