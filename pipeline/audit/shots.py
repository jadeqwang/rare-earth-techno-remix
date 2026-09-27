"""The DOT shots of the edit, as render/src/timeline.js plays them."""
import json, numpy as np
A = json.load(open('/home/user/rare-earth-techno-remix/render/data/audio.json'))
SEL = json.load(open('/home/user/rare-earth-techno-remix/pipeline/selects.json'))
def W(i, j): return A['lines'][i]['words'][j]['t']
beats = [b['t'] for b in A['beats']]
fb = [b for b in beats if 112.0 <= b < 123.5]
def B2(i): return fb[i]
# id: (clip, t0, t1, rect, lag override, split-left)
SHOTS = {
 'poster':     ('sd01', 0.0, 5.70, 'poster', None, False),
 'yearning':   ('sd02', 5.70, 8.86, [0,0,1,1], None, False),
 'listen':     ('sd03', 10.88, 12.73, [0,-0.06,1.12,1.12], None, False),
 'pullback':   ('sd04', 12.73, 14.81, [0,0,1,1], None, False),
 'caught':     ('sd05', 23.17, 24.79, [0,0,1,1], None, False),
 'blink':      ('sd06', 25.30, 27.82, [0,0,1,1], None, False),
 'transit_eye':('sd07', 30.98, 35.94, [0,0,1,1], None, False),
 'alone':      ('sd08', 35.94, 39.95, [0,0,1,1], None, False),
 'keep_yagi':  ('sd09', 62.42, 63.23, [0,0,1,1], None, False),
 'vision':     ('sd10', 71.14, W(15,1), [0,0,1,1], None, False),
 'vision2':    ('sd10', W(15,4)-0.27, 75.36, [0,0,1,1], 3/24, False),
 'care2':      ('sd11', 75.36, 77.66, [0.17,0,1,1], None, False),
 'listen2':    ('sd12', 82.20, 84.60, [-0.15,0,1,1], None, False),
 'caught2':    ('sd13', W(22,2), 97.45, [-0.182,-0.298,1.35,1.35], None, False),
 'blinkdance': ('sd14', 99.76, 100.75, [0.1,0,0.8,0.8], None, False),
 'own':        ('sd15', 104.34, 107.79, [0,0,1,1], None, False),
 'alone2':     ('sd16', 107.79, 112.02, [0,0,1,1], None, True),
 'dance2':     ('sd17', B2(4), B2(6), [0,0,1,1], None, False),
 'dance3':     ('sd17', B2(8), B2(10), [0,0,1,1], None, False),
 'stillhere':  ('sd18', 120.90, 123.40, [0.25,0,0.88,0.88], None, False),
}
def smooth(x): x = min(1, max(0, x)); return x*x*(3-2*x)
def rect_at(shot, t):
    r = SHOTS[shot][3]
    if r == 'poster':
        pk = smooth(t/5.7); return [-0.04*pk, -0.03*pk, 1+0.08*pk, 1+0.08*pk]
    return r
def lag_of(shot):
    clip, *_ , lag_o, _s = SHOTS[shot][0], None, None, None, SHOTS[shot][4], None
    return SHOTS[shot][4] if SHOTS[shot][4] is not None else SEL[SHOTS[shot][0]]['lag']
def frame_index(clip_t, n, twos=True):
    f = int(np.floor(clip_t*24 + 1e-3))
    if twos: f -= f % 2
    return max(0, min(n-1, f))
def displayed(shot, n):
    """list of (release frame i, t, plate frame fi) for the shot"""
    clip, t0, t1 = SHOTS[shot][:3]
    start = SEL[clip]['start']; lag = lag_of(shot)
    out = []
    i0 = int(np.ceil(t0*24 - 1e-6)); i1 = int(np.ceil(t1*24 - 1e-6))
    for i in range(i0, i1):
        t = i/24
        out.append((i, t, frame_index(t - start + lag, n)))
    return out
def plate_to_screen(shot, t, px, py):
    r = rect_at(shot, t)
    u, v = px/1280, 1 - py/720
    X = (r[0] + u*r[2]); Y = (r[1] + v*r[3])
    if SHOTS[shot][5]: X = X - 0.25
    return X*1920, (1-Y)*1080, abs(r[2])*1920/1280
def word_at(t):
    for L in A['lines']:
        for w in L['words']:
            if w['t'] <= t < w['end']: return w['w']
    return ''
