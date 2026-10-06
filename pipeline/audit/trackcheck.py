"""Verification sheet for a plate's face track: every displayed frame, the eye points (yellow), the first-guess mouth
(red cross) and the mouth the detector finds (green box)."""
import sys, numpy as np, cv2
sys.path.insert(0, '/home/user/rare-earth-techno-remix/pipeline/sync')
import relip
def run(key, cols=8, cell=200):
    spec = relip.PLATES[key]
    P = relip.Plate(spec)
    used = set()
    for name, win, start, lag in spec['shots']:
        for e, t in relip.display_units(win, start, lag, P.n):
            if P.lo <= e < P.hi: used.add(e)
    cells = []
    for e in sorted(used):
        ex, ey, d, mx, my = P.tr[e]
        f = P.frames[e].copy()
        cv2.circle(f, (int(ex - d/2), int(ey)), 4, (0,255,255), -1); cv2.circle(f, (int(ex + d/2), int(ey)), 4, (0,255,255), -1)
        cv2.drawMarker(f, (int(mx), int(my)), (0,0,255), cv2.MARKER_CROSS, 14, 2)
        g = P.geo[e]
        if g is not None:
            cv2.rectangle(f, (int(g[0]-g[2]/2), int(g[1]-4)), (int(g[0]+g[2]/2), int(g[1]+4)), (0,255,0), 1)
        s = int(1.6 * d); cx, cy = int(ex), int((ey + my) / 2)
        c = f[max(0, cy - s//2):cy + s//2, max(0, cx - s//2):cx + s//2]
        c = cv2.resize(c, (cell, cell))
        cv2.putText(c, f'f{e} r={g[3]:.2f}' if g else f'f{e} none', (3, 14), 0, 0.45, (255,255,255), 1)
        cells.append(c)
    while len(cells) % cols: cells.append(np.zeros_like(cells[0]))
    out = f'/tmp/work/audit/track_{key}.jpg'
    cv2.imwrite(out, np.concatenate([np.concatenate(cells[k:k+cols], 1) for k in range(0, len(cells), cols)], 0), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return out
if __name__ == '__main__':
    for k in sys.argv[1:]: print(run(k))
