"""Re-shoot a lip-sync spot with Seedance 2.5, the way the alt-pop cut was made: one short take per sung line, started
on the shot's own first drawing (image-to-video, so the new take continues the old one's pose, framing and background)
and driven by the vocal cut to start exactly where the shot starts in the song, so clip time 0 = shot start and no lag
or re-timing is needed. The renderer then paints the new take like any other.

  python3 pipeline/reshoot.py submit blink vision care2 [--takes 3]
  python3 pipeline/reshoot.py collect               # downloads finished takes to pipeline/base_clips/reshoot/
"""
import json
import os
import subprocess
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen  # noqa: E402
from seedance_shots import SHOTS, STYLE, SING, GREEN  # noqa: E402

CLIPS = os.path.join(HERE, 'base_clips')
OUT = os.path.join(CLIPS, 'reshoot')
WORK = '/tmp/work/reshoot'
LOG = os.path.join(OUT, 'jobs.json')
SEL = json.load(open(os.path.join(HERE, 'selects.json')))
SPEC = {s['id'][:4]: s for s in SHOTS}
# spot: (take, song time the shot starts, the text sung, whether the take is keyed)
SPOTS = {
    'blink': ('sd06', 25.30, 'The beating blinking of a star', False),
    'vision': ('sd10', 71.14, '-sion. Our science', True),
    'care2': ('sd11', 75.36, 'Do you still care', True),
}


def first_frame(take, t0):
    s = SEL[take]
    i = int(round((t0 - s['start'] + s['lag']) * 24))
    src = os.path.join(CLIPS, s['file'].replace('_lips', '').replace('_sync', ''))
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, i))
    ok, f = cap.read()
    p = f'{WORK}/{take}_first.png'
    cv2.imwrite(p, f)
    return p


def audio(t0, dur):
    p = f'{WORK}/voc_{t0:.2f}_{dur}.mp3'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{t0}', '-t', f'{dur}', '-i', '/tmp/work/vocals.wav',
                    '-ac', '2', '-ar', '44100', '-b:a', '192k', p], check=True)
    return p


def submit(spots, takes):
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    log = json.load(open(LOG)) if os.path.exists(LOG) else []
    for name in spots:
        take, t0, words, keyed = SPOTS[name]
        spec = SPEC[take]
        prompt = (spec['prompt'] + SING + ' Her mouth moves from the very first frame, exactly in time with the reference'
                  f' audio, which starts mid-phrase ("{words}"); no pause or idle before singing.' + STYLE)
        inp = {'prompt': prompt, 'image': gen.data_uri(first_frame(take, t0)),
               'reference_audios': [gen.data_uri(audio(t0, 4))], 'duration': 4, 'resolution': '720p',
               'aspect_ratio': 'adaptive', 'fps': 24, 'generate_audio': False, 'watermark': False, 'output_format': 'mp4'}
        for k in range(takes):
            jid = gen.submit_cron('bytedance/seedance-2.5', inp, tag=f'reshoot-{name}', delay_min=2 + k)
            log.append({'spot': name, 'take': take, 't0': t0, 'job': jid})
            print('queued', name, jid, flush=True)
    json.dump(log, open(LOG, 'w'), indent=1)


def collect():
    log = json.load(open(LOG))
    for j in log:
        dst = f"{OUT}/{j['spot']}__{j['job'].split('-')[-1]}.mp4"
        if os.path.exists(dst): continue
        rec = gen.poll(j['job'])
        if rec is None: print('waiting', j['job']); continue
        if rec.get('state') == 'error': print('error', j['job'], str(rec.get('error'))[:200]); continue
        try: print('got', gen.fetch_media(j['job'], rec, dst[:-4]))
        except Exception as e: print('lost', j['job'], str(e)[:80])   # the relay's mirror failed; re-submit


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'submit':
        n = int(sys.argv[sys.argv.index('--takes') + 1]) if '--takes' in sys.argv else 3
        submit([a for a in sys.argv[2:] if a in SPOTS], n)
    else:
        collect()
