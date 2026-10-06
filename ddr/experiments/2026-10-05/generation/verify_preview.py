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
import soundfile as sf
from PIL import Image
from scipy.signal import correlate, correlation_lags

experiment = Path(__file__).resolve().parents[1]
root = experiment/'release'
out = root/'preview'
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
song = root/'Songs/Rare Earth Model Pack/Rare Earth (Techno Remix - Model Edition)'
simpath = song/'Rare Earth (Techno Remix - Model Edition).ssc'
baseline = {p:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root/'Rare_Earth_Model_Edition_Step_Pack.zip',*song.glob('*')] if p.is_file()}
checks = []
render_checks = []
alignment_checks = []
audio_checks = []
source_audio, sample_rate = sf.read(song/'Rare_Earth_DDR.mp3', dtype='float32', always_2d=True)
source_audio = source_audio.mean(axis=1)
for mode in ['single','double']:
    sys.argv = ['render_preview.py','--mode',mode,'--stills','--simfile',str(simpath),'--out',str(out)]
    module = runpy.run_path(str(experiment/'generation/render_preview.py'),run_name='preview_qa')
    # Isolate each column and compare the approaching arrow's visible bounds
    # with the stationary target's silhouette, including all four rotations.
    panels = module['PANELS'][:]
    probe = dict(panels[0], taps=[], holds=[])
    module['PANELS'][:] = [probe]
    for col,cx in enumerate(probe['columns']):
        probe['taps'] = [(2.0,col,module['COLORS'][0])]
        half = module['SPRITE_SIZE']//2
        cy = module['RECEPTOR']
        box = (cx-half,cy-half,cx+half,cy+half)
        rgb = np.asarray(module['render'](2.0-1e-6).crop(box)).astype(float)
        red = (rgb[:,:,0]>180)&(rgb[:,:,1]<175)&(rgb[:,:,2]<195)&(rgb[:,:,0]>rgb[:,:,1]*1.25)
        silhouette = np.asarray(module['RECEPTORS'][col%4])[:,:,3] > 32
        observed_y,observed_x = np.nonzero(red)
        target_y,target_x = np.nonzero(silhouette)
        assert len(observed_y)>50,(mode,col)
        center_error = [float((observed_x.min()+observed_x.max()-target_x.min()-target_x.max())/2),
                        float((observed_y.min()+observed_y.max()-target_y.min()-target_y.max())/2)]
        outside = int(np.count_nonzero(red & ~silhouette))
        assert max(abs(v) for v in center_error)<=1,(mode,col,center_error)
        assert outside==0,(mode,col,outside)
        alignment_checks.append(dict(mode=mode,column=col,center_error_pixels=center_error,
                                     colored_pixels_outside_target=outside))
    module['PANELS'][:] = panels
    p = module['PANELS'][0]
    tap = min(p['taps'])
    hold = min(p['holds'])
    indices = []
    for t in [tap[0],hold[1]]:
        first = math.ceil(t*module['FPS'])
        indices.extend([first-1,first])
    video = out/f'Rare_Earth_Model_Edition_{mode}_preview.mp4'
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
        # H.264 may leave isolated colored pixels after the arrow is gone.
        # Two pixels are below 1.5% of even the smaller double arrow.
        assert pixels[1]<=2,(mode,event,pixels)
        checks.append(dict(mode=mode,event=event,time_s=t,
                           checked_video_frames=indices[event_index*2:event_index*2+2],
                           disappearance_delay_ms=round((indices[event_index*2+1]/module['FPS']-t)*1000,6),
                           red_arrow_pixels_before_and_after=pixels))
    audio_result = subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(video),
                                   '-map','0:a:0','-ac','1','-ar',str(sample_rate),'-f','f32le','-'],
                                  capture_output=True,check=True)
    encoded_audio = np.frombuffer(audio_result.stdout,dtype='<f4')
    for start in [5,55,110]:
        lo,hi = int(start*sample_rate),int((start+2)*sample_rate)
        reference,actual = source_audio[lo:hi],encoded_audio[lo:hi]
        correlation = correlate(actual,reference,mode='full',method='fft')
        lags = correlation_lags(len(actual),len(reference),mode='full')
        valid = abs(lags)<=int(.1*sample_rate)
        lag = int(lags[valid][np.argmax(correlation[valid])])
        similarity = float(np.corrcoef(actual,reference)[0,1])
        assert abs(lag)<=1 and similarity>.98,(mode,start,lag,similarity)
        audio_checks.append(dict(mode=mode,window_start_s=start,audio_lag_samples=lag,
                                 audio_lag_ms=lag*1000/sample_rate,correlation=similarity))
    decoded = subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(video),
                              '-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode == 0,decoded.stderr
for path,sha in baseline.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,path
report_path = root/'preview-validation.json'
report = dict(status='passed',checks=render_checks,encoded_video_checks=checks,
              frames_per_second=module['FPS'],maximum_frame_delay_ms=1000/module['FPS'],
              arrow_alignment_checks=alignment_checks,encoded_audio_checks=audio_checks,
              full_video_decodes='passed',step_pack_and_song_files_unchanged=True)
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
