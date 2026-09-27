"""Lip-sync check, as played: every drawing the renderer shows in each singing shot, its mouth measured in the take
as released before this pass and in the re-lipped take, against the exposure sheet (lipsheet.json).

A drawing is counted wrong when it reads as wrong (relip.fits): open through a rest or a lip closure, open wide on a
consonant, or shut on a sung vowel. r is the correlation of the drawings' openness with the sheet.

  python3 pipeline/sync/lipcheck.py [--before FILE ...]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relip  # noqa: E402

SEL = json.load(open(os.path.join(HERE, '..', 'selects.json')))
# the takes the previous release played (docs/PROCESS.md §3d)
BEFORE = {'sd02': 'sd02_cu_yearning__c8b3647c99.mp4', 'sd03': 'sd03_mcu_listen__17fad81acf.mp4',
          'sd05': 'sd05_console_caught__ba8af2ae02_lettering.mp4', 'sd06': 'sd06_blink__a30f474b95_sync.mp4',
          'sd07': 'sd07_transit__9681e0518b_sync.mp4', 'sd09': 'sd09_keep_looking__c6c9c8b95f.mp4',
          'sd10': 'sd10_vision__1368eb119a_sync.mp4', 'sd11': 'sd11_care__03ce0c9203_sync.mp4',
          'sd12': 'sd12_search_listen__58e3680064.mp4', 'sd13': 'sd13_caught_reply__935323d481_lettering_sync.mp4',
          'sd14': 'sd14_blink_dance__bd2b906427.mp4', 'sd15': 'sd15_own_ecu__3eb552a647_sync.mp4'}


def measure(P, frames, e):
    g = relip.geometry(frames[e], *P.mouth_at(e), 2.2 * P.tr[e][2])
    return None if g is None else g[3] / P.tr[e][2] / P.wide


def main():
    rows = []
    for key, spec in relip.PLATES.items():
        P = relip.Plate(spec)                       # the take as generated: the face track and the openness scale
        before = relip.read_clip(os.path.join(relip.CLIPS, BEFORE[key]))
        after = relip.read_clip(os.path.join(relip.CLIPS, SEL[key]['file']))
        for name, win, start, lag in spec['shots']:
            units = [(e, t) for e, t in relip.display_units(win, start, lag, P.n) if P.lo <= e < P.hi]
            want = np.array([relip.target(name, t) for _, t in units])
            res = {}
            for tag, frames in (('before', before), ('after', after)):
                o = [measure(P, frames, e) for e, _ in units]
                bad = [t for (e, t), w, v in zip(units, want, o) if not relip.fits(w, v)]
                ok = np.array([v is not None for v in o])
                v = np.array([x if x is not None else np.nan for x in o])
                r = float(np.corrcoef(v[ok], want[ok])[0, 1]) if ok.sum() > 3 else float('nan')
                res[tag] = (len(bad), r, bad)
            rows.append((name, len(units), res))
            print(f"{name:12s} {len(units):3d} drawings  wrong {res['before'][0]:2d} -> {res['after'][0]:2d}   "
                  f"r {res['before'][1]:+.2f} -> {res['after'][1]:+.2f}   still wrong at {[round(t, 2) for t in res['after'][2]]}",
                  flush=True)
    tb = sum(r[2]['before'][0] for r in rows); ta = sum(r[2]['after'][0] for r in rows); n = sum(r[1] for r in rows)
    print(f'all: {n} drawings, wrong {tb} -> {ta}')


if __name__ == '__main__':
    main()
