"""Check rendered and encoded hit boundaries, then decode both full previews."""
from pathlib import Path
import hashlib
import json
import math
import runpy
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[1]
out = root/'preview'
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
song = root/'Songs/Rare Earth Pack/Rare Earth (Techno Remix)'
baseline = {p:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root/'Rare_Earth_DDR_Step_Pack.zip',*song.glob('*')] if p.is_file()}
checks = []
render_checks = []
for mode in ['single','double']:
    sys.argv = ['preview.py','--mode',mode,'--stills']
    module = runpy.run_path(str(root/'tools/preview.py'),run_name='preview_qa')
    p = module['PANELS'][0]
    tap = min(p['taps'])
    hold = min(p['holds'])
    indices = []
    for t in [tap[0],hold[1]]:
        first = math.ceil(t*module['FPS'])
        indices.extend([first-1,first])
    video = out/f'Rare_Earth_DDR_{mode}_preview.mp4'
    selected = "select='"+'+'.join(f'eq(n,{i})' for i in indices)+"'"
    pattern = out/f'hit-qa-{mode}-%02d.png'
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(video),
                    '-vf',selected,'-fps_mode','passthrough','-frames:v','4',str(pattern)],check=True)
    for event_index,(event,t,col) in enumerate([('tap hit',tap[0],tap[1]),('hold release',hold[1],hold[2])]):
        cx = p['columns'][col]
        cy = module['RECEPTOR']
        half = module['SPRITE_SIZE']//2
        box = (cx-half,cy-half,cx+half,cy+half)
        reference = np.asarray(module['BASE'].crop(box))
        differences = [int(np.count_nonzero(np.any(np.asarray(module['render'](at).crop(box))!=reference,axis=2)))
                       for at in [t-.001,t,t+1/module['FPS']]]
        assert differences[0]>30 and differences[1:]==[0,0],(mode,event,differences)
        render_checks.append(dict(mode=mode,event=event,event_time_s=t,
                                  arrow_pixels_before_at_after=differences))
        pixels = []
        for sequence in [event_index*2+1,event_index*2+2]:
            frame = Image.open(out/f'hit-qa-{mode}-{sequence:02d}.png')
            rgb = np.asarray(frame.crop(box)).astype(float)
            red = (rgb[:,:,0]>180)&(rgb[:,:,1]<175)&(rgb[:,:,2]<195)&(rgb[:,:,0]>rgb[:,:,1]*1.25)
            pixels.append(int(red.sum()))
        assert pixels[0]>80,(mode,event,pixels)
        assert pixels[1]==0,(mode,event,pixels)
        checks.append(dict(mode=mode,event=event,time_s=t,
                           checked_video_frames=indices[event_index*2:event_index*2+2],
                           red_arrow_pixels_before_and_after=pixels))
    decoded = subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(video),
                              '-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode == 0,decoded.stderr
for path,sha in baseline.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,path
report_path = root/'analysis/preview-hit-check.json'
report = dict(status='passed',checks=render_checks,encoded_video_checks=checks,
              full_video_decodes='passed',step_pack_and_song_files_unchanged=True)
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
