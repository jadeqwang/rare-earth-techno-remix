"""Render four levels of single or double from the exported SSC file."""
from pathlib import Path
import argparse
import json
import math
import subprocess
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="fs")
import imageio_ffmpeg
import simfile
from simfile.notes import NoteData, NoteType
from simfile.timing import Beat, TimingData
from simfile.timing.engine import TimingEngine
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--simfile',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--mode',choices=['single','double'],default='single')
parser.add_argument('--stills',action='store_true')
OPTIONS=parser.parse_args()
SONG=OPTIONS.simfile.parent
OUT=OPTIONS.out
OUT.mkdir(parents=True,exist_ok=True)
with OPTIONS.simfile.open() as f:
    SIM=simfile.load(f,strict=True)
ENGINE=TimingEngine(TimingData(SIM))
TIMING=json.loads((ROOT/'analysis/timing.json').read_text())
MODE=OPTIONS.mode
VIDEO=OUT/f'Rare_Earth_Model_Edition_{MODE}_preview.mp4'
W,H,FPS = 1280,720,60
RECEPTOR = 191
BOTTOM = 608
SPEED = 150
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
fonts = {n:ImageFont.truetype(FONT,n) for n in [13,15,17,19]}
bold = {n:ImageFont.truetype(BOLD,n) for n in [18,22,28,32]}
mono = ImageFont.truetype(MONO,14)
COLORS = ["#ff7f8b","#75bfff","#ffd266"]


def arrow(direction,color,outline=False):
    # These are code-native graphics; each sprite is drawn at 3x and reduced
    # for smooth edges. Orientation order matches SM's L,D,U,R columns.
    s = 3
    im = Image.new("RGBA",(44*s,44*s))
    d = ImageDraw.Draw(im)
    points = [(22*s+x*s,22*s+y*s) for x,y in [(-6,15),(6,15),(6,0),(16,0),(0,-17),(-16,0),(-6,0)]]
    if outline:
        d.polygon(points,fill="#111b31",outline=color,width=2*s)
    else:
        d.polygon(points,fill=color,outline="#101727",width=s)
        d.line([(22*s,9*s),(31*s,19*s)],fill="#ffffff80",width=s)
    rotations = [90,180,0,-90]
    return im.rotate(rotations[direction]).resize((44,44),Image.Resampling.LANCZOS)


SPRITE_SIZE = 32 if MODE == "double" else 44
SPRITES = {(direction,c):arrow(direction,c).resize((SPRITE_SIZE,SPRITE_SIZE),Image.Resampling.LANCZOS)
           for direction in range(4) for c in COLORS}
RECEPTORS = [arrow(d,"#8190ad",True).resize((SPRITE_SIZE,SPRITE_SIZE),Image.Resampling.LANCZOS)
            for d in range(4)]
PANELS = []
layout = [(24,296),(336,296),(648,296),(960,296)]
titles = ["BEGINNER","EASY","STANDARD","HEAVY"]
charts = [c for c in SIM.charts if c["STEPSTYPE"] == f"dance-{MODE}"]
assert len(charts) == 4
for i,chart in enumerate(charts):
    x,width = layout[i]
    ncols = 8 if chart["STEPSTYPE"] == "dance-double" else 4
    if ncols == 4:
        columns = [x+64+c*56 for c in range(4)]
    else:
        columns = [x+32+c*30+(20 if c>=4 else 0) for c in range(8)]
    nd = list(NoteData(chart))
    active = {}
    taps = []
    holds = []
    for n in nd:
        t = float(ENGINE.time_at(n.beat))
        beat = float(n.beat)
        frac = beat%1
        color = COLORS[0 if abs(frac)<1e-5 else 1 if abs(frac-.5)<1e-5 else 2]
        if n.note_type == NoteType.TAIL:
            start,b,c = active.pop(n.column)
            holds.append((start,t,n.column,c))
        else:
            if n.note_type == NoteType.HOLD_HEAD:
                active[n.column] = (t,beat,color)
            else:
                taps.append((t,n.column,color))
    PANELS.append(dict(x=x,width=width,columns=columns,taps=taps,holds=holds,
                       title=titles[i],meter=chart["METER"],ncols=ncols))

BASE = Image.new("RGB",(W,H),"#080e20")
draw = ImageDraw.Draw(BASE)
draw.text((24,20),"RARE EARTH",font=bold[32],fill="#f6f2e9")
draw.text((285,31),"TECHNO REMIX · MODEL EDITION",font=fonts[19],fill="#70ded7")
draw.text((24,66),f"Robot Ninja Apocalypse  /  ITGPT + GrooveAuthor  /  {MODE.upper()}",font=fonts[15],fill="#aebad0")
draw.text((1033,37),"129–136 BPM",font=bold[18],fill="#e1e7f0")
for p in PANELS:
    x,w = p["x"],p["width"]
    draw.rounded_rectangle((x,103,x+w,622),radius=12,fill="#10192d",outline="#263450",width=1)
    draw.text((x+16,115),p["title"],font=bold[22],fill="#f4f1e9")
    subtitle = f"{'8-panel' if p['ncols']==8 else '4-panel'}  /  meter {p['meter']}"
    draw.text((x+16,148),subtitle,font=fonts[15],fill="#a5b6d1")
    for c,cx in enumerate(p["columns"]):
        draw.line((cx,RECEPTOR+27,cx,BOTTOM),fill="#1e2941",width=1)
        BASE.paste(RECEPTORS[c%4],(int(cx-SPRITE_SIZE/2),int(RECEPTOR-SPRITE_SIZE/2)),RECEPTORS[c%4])
    if p["ncols"] == 8:
        sep = (p["columns"][3]+p["columns"][4])/2
        draw.line((sep,RECEPTOR-27,sep,BOTTOM),fill="#40516e",width=2)
        draw.text((x+51,584),"PAD 1",font=mono,fill="#788da9")
        draw.text((x+205,584),"PAD 2",font=mono,fill="#788da9")
draw.text((24,666),"Red: quarter notes     Blue: eighths     Gold: sixteenths     Teal bars: holds",font=fonts[13],fill="#a0b2cc")
draw.text((24,689),"Provisional classic DDR-style meters  /  pad playtest pending",font=fonts[13],fill="#7589a8")
bar_times = [float(ENGINE.time_at(Beat(s["beat"]))) for s in TIMING["bpms"]]


def render(t):
    im = BASE.copy()
    for p in PANELS:
        x,w = p["x"],p["width"]
        layer = Image.new("RGBA",(W,H))
        d = ImageDraw.Draw(layer)
        for bt in bar_times:
            yy = RECEPTOR+(bt-t)*SPEED
            if RECEPTOR+24 < yy < BOTTOM:
                d.line((x+14,yy,x+w-14,yy),fill="#2a395280",width=1)
        for start,end,col,color in p["holds"]:
            if end <= t or start > t+3.1:
                continue
            cx = p["columns"][col]
            y0 = max(RECEPTOR,RECEPTOR+(start-t)*SPEED)
            y1 = RECEPTOR+(end-t)*SPEED
            d.rounded_rectangle((cx-7,y0,cx+7,max(y0+1,y1)),radius=6,fill="#58cbbb",outline="#b0ffea",width=1)
            sprite = SPRITES[(col%4,color)]
            layer.paste(sprite,(int(cx-SPRITE_SIZE/2),int(y0-SPRITE_SIZE/2)),sprite)
            d.line((cx-10,y1,cx+10,y1),fill="#c1ffe9",width=3)
        for nt,col,color in p["taps"]:
            # Autoplay consumes the tap when its center reaches the receptor.
            # No late travel or replacement arrow flash remains after the hit.
            if nt <= t or nt > t+3.1:
                continue
            cx = p["columns"][col]
            yy = RECEPTOR+(nt-t)*SPEED
            sprite = SPRITES[(col%4,color)]
            layer.paste(sprite,(int(cx-SPRITE_SIZE/2),int(yy-SPRITE_SIZE/2)),sprite)
        clip = (x+1,RECEPTOR-25,x+w-1,BOTTOM)
        crop = layer.crop(clip)
        im.paste(crop,clip[:2],crop)
    d = ImageDraw.Draw(im)
    d.rectangle((24,635,1256,640),fill="#25314a")
    d.rectangle((24,635,24+1232*min(1,t/TIMING["duration_s"]),640),fill="#71dbd4")
    beat = ENGINE.beat_at(t)
    bpm = float(ENGINE.bpm_at(beat))
    section = next((s["label"].split(" (")[0] for s in TIMING["sections"] if s["t"] <= t < s["end"]),"outro")
    d.text((24,645),f"{int(t)//60}:{int(t)%60:02d} / 2:08     {bpm:5.1f} BPM     {section.upper()}",font=fonts[13],fill="#dae4f1")
    return im


def main():
    for t in [18.8,54.9,112.5]:
        render(t).save(OUT / f"{MODE}-{t:.1f}s.png")
    if OPTIONS.stills:
        return
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-y","-f","rawvideo",
           "-vcodec","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
           "-i","-","-i",str(SONG/SIM["MUSIC"]),"-map","0:v:0","-map","1:a:0",
           "-c:v","libx264","-preset","veryfast","-crf","22","-threads","4",
           "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",
           "-t",str(TIMING["duration_s"]),str(VIDEO)]
    with (OUT/f"encode-{MODE}.log").open("w") as log:
        process = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
        try:
            for i in range(math.ceil(TIMING["duration_s"]*FPS)):
                process.stdin.write(render(i/FPS).tobytes())
                if i%900 == 0:
                    print(f"{MODE}: rendered {i/FPS:.0f}s",flush=True)
        finally:
            process.stdin.close()
        assert process.wait() == 0, f"Preview encoder failed; see preview/encode-{MODE}.log"
    print(VIDEO)


if __name__ == "__main__":
    main()
