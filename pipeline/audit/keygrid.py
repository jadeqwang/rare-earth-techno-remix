"""Keyframe annotation sheets: plate frames cropped around the face with a labelled pixel grid (plate coords)."""
import sys, cv2, numpy as np
CL = '/home/user/rare-earth-techno-remix/pipeline/base_clips/'
def read(p):
    cap = cv2.VideoCapture(p); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(f)
    return fr
def sheet(src, frames, box, step=20, scale=1.0, out=None, cols=3):
    fr = read(CL + src)
    x0, y0, x1, y1 = box
    cells = []
    for i in frames:
        c = fr[i][y0:y1, x0:x1].copy()
        c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        for x in range((x0 // step + 1) * step, x1, step):
            X = int((x - x0) * scale); major = x % (step * 5) == 0
            cv2.line(c, (X, 0), (X, c.shape[0]), (0, 255, 255) if major else (0, 160, 160), 1)
            if major: cv2.putText(c, str(x), (X + 2, 12), 0, 0.4, (0, 255, 255), 1)
        for y in range((y0 // step + 1) * step, y1, step):
            Y = int((y - y0) * scale); major = y % (step * 5) == 0
            cv2.line(c, (0, Y), (c.shape[1], Y), (0, 255, 255) if major else (0, 160, 160), 1)
            if major: cv2.putText(c, str(y), (2, Y - 2), 0, 0.4, (0, 255, 255), 1)
        cv2.rectangle(c, (0, c.shape[0] - 18), (60, c.shape[0]), (0, 0, 0), -1)
        cv2.putText(c, f'f{i}', (3, c.shape[0] - 4), 0, 0.5, (255, 255, 255), 1)
        cells.append(c)
    while len(cells) % cols: cells.append(np.zeros_like(cells[0]))
    rows = [np.concatenate(cells[k:k + cols], 1) for k in range(0, len(cells), cols)]
    cv2.imwrite(out, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out
if __name__ == '__main__':
    src = sys.argv[1]; frames = list(map(int, sys.argv[2].split(','))); box = tuple(map(int, sys.argv[3].split(',')))
    scale = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0; step = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    print(sheet(src, frames, box, step, scale, sys.argv[6] if len(sys.argv) > 6 else '/tmp/work/audit/keys.jpg'))
