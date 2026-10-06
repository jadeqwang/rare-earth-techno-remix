"""Author four levels for single and double; export identical SM and SSC.

Rhythms are phrase templates, with deliberately placed accents and rests.
A two-foot planner selects panels while keeping a forward-facing stance;
double charts also limit stance width and travel between successive steps.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
PACK = ROOT / "Songs/Rare Earth Pack"
SONG = PACK / "Rare Earth (Techno Remix)"
SONG.mkdir(parents=True, exist_ok=True)
TIMING = json.loads((ROOT / "analysis/timing.json").read_text())
COORDS = [(-1,0), (0,-1), (0,1), (1,0), (2,0), (3,-1), (3,1), (4,0)]
SINGLE_MOTIFS = [
    [0,2,1,3,0,1,2,3],
    [0,1,0,2,1,3,2,3],
    [1,3,0,2,0,1,2,3],
    [0,3,2,3,0,1,0,2],
]


def time_at(beat):
    seg = TIMING["bpms"][min(int(beat//4), len(TIMING["bpms"])-1)]
    anchor = TIMING["beats"][seg["beat"]]["time_s"]
    return anchor + (beat-seg["beat"]) * 60 / seg["bpm"]


def rhythm(level, m, double=False):
    """Musical subdivisions within a four-beat measure, not onset spam."""
    if level == "standard":
        level = "double" if double else "intermediate"
    elif level == "heavy":
        level = "advanced"
    if m < 2:
        return []
    if m == 70:
        return [0] if level == "beginner" else [0,2] if level == "easy" else [0,1,2]
    if m == 69:
        return [0,2] if level != "advanced" else [0,1,2,3]
    if m == 68:
        return [0,2] if level == "beginner" else [0,1,2] if level == "easy" else [0,.5,1,2]
    if level == "beginner":
        if m in [9,20,21,24,25,33,40,41,49,60,61]:
            return [0]
        if m in [29,63,67]:
            return [0,1,2,3]
        return [0,2]
    if level == "easy":
        if m in [9,20,40,60]:
            return [0,3]
        if m in [33,38,39,49,58,59]:
            return [0,1,3]
        if 22 <= m < 30:
            return [[0,3],[0,2],[0,1,2],[0,1,2,3],
                    [0,1,2,3],[0,1,2],[0,1,2,3],[0,1,2,3]][m-22]
        if m >= 30:
            return [0,1,2] if m%4 == 3 else [0,1,2,3]
        return [[0,2],[0,1,2],[0,2,3],[0,1,2,3]][m%4]
    if m in [9,20,40,60]:
        return [0,3] if level != "advanced" else [0,1,2,3]
    if m in [21,41,61]:
        return [0,1,2,3] if level != "advanced" else [0,.5,1,1.5,2,2.5,3,3.5]
    if 22 <= m < 30:
        builds = {
            "intermediate": [[0,3],[0,2],[0,1,2,3],[0,1,2,3,3.5],
                             [0,1,2,2.5,3,3.5],[0,.5,1,2,2.5,3],
                             [0,1,2,3],[0,1,2,2.5,3,3.5]],
            "double": [[0,3],[0,2],[0,1,2,3],[0,1,2,3],
                       [0,1,2,3],[0,1,2,2.5,3],[0,1,2,3],[0,1,2,3,3.5]],
            "advanced": [[0,2,3],[0,1,2,3],[0,.5,1,2,2.5,3],
                         [0,.5,1,1.5,2,2.5,3,3.5],
                         [0,.5,1,1.5,2,2.5,3,3.5],
                         [0,.5,1,1.5,2,2.5,3,3.5],
                         [0,.5,1,1.5,2,2.5,3,3.5],
                         [0,.5,1,1.5,2,2.5,3,3.25,3.5,3.75]],
        }
        return builds[level][m-22]
    if m == 33:  # breathing space at the lyric's blank / turnaround
        return [0,1,3] if level != "advanced" else [0,.5,1,3,3.5]
    if m in [38,39,58,59]:
        return [0,1,2] if level != "advanced" else [0,.5,1,2,2.5,3]
    if m == 49:
        return [0,1,2] if level != "advanced" else [0,.5,1,1.5,2,2.5]
    if level == "double":
        if 62 <= m <= 67:
            return [[0,1,2,2.5,3,3.5], [0,.5,1,2,3]][m%2]
        if m >= 30:
            return [[0,1,2,3],[0,1,2,2.5,3],[0,1,2,3],[0,1,2,3,3.5]][m%4]
        return [[0,1,2,3],[0,1,3],[0,1,2,3],[0,1,2,3,3.5]][m%4]
    if level == "intermediate":
        if 62 <= m <= 67:
            return [[0,1,1.5,2,2.5,3,3.5], [0,.5,1,1.5,2,3,3.5]][m%2]
        if m >= 30:
            return [[0,1,1.5,2,3,3.5],[0,.5,1,2,2.5,3],
                    [0,1,2,2.5,3,3.5],[0,.5,1,1.5,2,3]][m%4]
        return [[0,1,2,2.5,3],[0,1,2,3],[0,1,1.5,2,3],[0,1,2,3,3.5]][m%4]
    if 62 <= m <= 67:
        if m in [63,65,67]:
            return [0,.5,1,1.5,2,2.5,3,3.25,3.5,3.75]
        return [0,.5,1,1.5,2,2.5,3,3.5]
    if m >= 30:
        if m in [31,35,43,47,51,55]:
            return [0,.5,1,1.5,2,2.25,2.5,2.75,3,3.5]
        return [[0,.5,1,1.5,2,2.5,3,3.5],
                [0,.5,1,1.5,2,3,3.5],
                [0,1,1.5,2,2.5,3,3.5]][m%3]
    return [[0,.5,1,2,2.5,3,3.5],
            [0,1,1.5,2,3,3.5],
            [0,.5,1,1.5,2,2.5,3,3.5],
            [0,.5,1,2,3,3.5]][m%4]


def target_center(beat, level="standard"):
    # A full left/right/left trip takes eight measures. Crossing speed varies
    # smoothly, so dense rhythmic figures don't introduce abrupt pad changes.
    divisor = 32 if level == "beginner" else 16
    center = 1.5-1.5*math.cos(math.pi*(beat-8)/divisor)
    if level == "heavy":
        measure = int(beat//4)
        if any(r%1 in [.25,.75] for r in rhythm("heavy",measure,True)):
            # Keep rapid sixteenth bursts on one pad. Travel resumes during
            # the surrounding eighth/quarter phrases.
            midpoint = 1.5-1.5*math.cos(math.pi*(measure*4+2-8)/16)
            center = 0 if midpoint < 1.5 else 3
    return center


class FootFlow:
    def __init__(self, double, level="standard"):
        self.double = double
        self.level = level
        self.feet = [0,3]
        self.next_foot = 0
        self.previous = set()
        self.previous_beat = -99
        self.index = 0
        self.records = []

    def jump(self, beat):
        center = target_center(beat,self.level) if self.double else 0
        if self.double:
            columns = [0,3] if center < .65 else [4,7] if center > 2.35 else [3,4]
        else:
            columns = [0,3] if int(beat/4)%2 == 0 else [1,2]
        self.feet = list(columns)
        self.next_foot = 0
        self.previous = set(columns)
        self.previous_beat = beat
        self.records.append(dict(beat=beat, feet=list(self.feet), jump=True))
        return columns

    def step(self, beat):
        foot = self.next_foot
        other = self.feet[1-foot]
        old = self.feet[foot]
        center = target_center(beat,self.level) if self.double else 0
        motif = SINGLE_MOTIFS[int(beat//16)%len(SINGLE_MOTIFS)]
        preferred = motif[self.index%8] + (4 if self.double and center > 1.5 else 0)
        desired_x = center + (-.6 if foot == 0 else .6)
        candidates = []
        for c in range(8 if self.double else 4):
            if c == other:
                continue
            state = list(self.feet)
            state[foot] = c
            left, right = [np.array(COORDS[k], float) for k in state]
            if left[0] > right[0] or np.linalg.norm(right-left) > 2.25:
                continue
            travel = np.linalg.norm(np.array(COORDS[c])-np.array(COORDS[old]))
            if self.double and travel > 2.83:
                continue
            if c in self.previous and beat-self.previous_beat < 1:
                continue
            cost = .85*abs(COORDS[c][0]-desired_x) + .24*travel
            cost += .9*(c != preferred) + .65*(c == old)
            if self.double:
                cost += .3*abs((left[0]+right[0])/2-center)
            candidates.append((cost,c))
        if not candidates:
            raise ValueError(f"No two-foot placement at beat {beat}, feet {self.feet}")
        _, column = min(candidates)
        self.feet[foot] = column
        self.records.append(dict(beat=beat, feet=list(self.feet), foot=foot, column=column, jump=False))
        self.next_foot = 1-foot
        self.previous = {column}
        self.previous_beat = beat
        self.index += 1
        return [column]


CHARTS = [
    dict(key="single_beginner", level="beginner", name="Beginner Single", type="dance-single", difficulty="Beginner", meter=3),
    dict(key="single_easy", level="easy", name="Easy Single", type="dance-single", difficulty="Easy", meter=4),
    dict(key="single_standard", level="standard", name="Standard Single", type="dance-single", difficulty="Medium", meter=6),
    dict(key="single_heavy", level="heavy", name="Heavy Single", type="dance-single", difficulty="Hard", meter=9),
    dict(key="double_beginner", level="beginner", name="Beginner Double", type="dance-double", difficulty="Beginner", meter=3),
    dict(key="double_easy", level="easy", name="Easy Double", type="dance-double", difficulty="Easy", meter=5),
    dict(key="double_standard", level="standard", name="Standard Double", type="dance-double", difficulty="Medium", meter=7),
    dict(key="double_heavy", level="heavy", name="Heavy Double", type="dance-double", difficulty="Hard", meter=10),
]
JUMP_MEASURES = {
    "single_beginner": set(),
    "single_easy": {30,42,62,68},
    "single_standard": {30,34,42,46,50,54,62,64,66,68},
    "single_heavy": {10,18,26,30,34,36,42,46,50,54,56,62,64,66,68},
    "double_beginner": set(),
    "double_easy": {30,42,62,68},
    "double_standard": {30,42,50,62,66,68},
    "double_heavy": {10,18,26,30,34,36,42,46,50,54,56,62,64,66,68},
}


def author(config):
    key = config["key"]
    double = config["type"] == "dance-double"
    ncols = 8 if double else 4
    notes = {}
    flow = FootFlow(double,config["level"])
    beats = [4*m+r for m in range(71) for r in rhythm(config["level"],m,double)]
    for i, beat in enumerate(beats):
        m = int(beat//4)
        jump = beat%4 == 0 and m in JUMP_MEASURES[key]
        cols = flow.jump(beat) if jump else flow.step(beat)
        for c in cols:
            notes[(int(round(beat*4)),c)] = "1"
        next_beat = beats[i+1] if i+1 < len(beats) else 283.5
        gap = next_beat-beat
        hold = not jump and beat%4 == 0 and gap >= 2 and m in [9,20,22,23,24,25,38,40,49,58,60,69,70]
        if hold:
            length = min(gap-.5, 3)
            # A freeze always releases before the next step; there is no
            # hidden third-foot demand from a hold plus a subsequent jump.
            tail = int(round((beat+length)*4))
            notes[(int(round(beat*4)),cols[0])] = "2"
            assert (tail,cols[0]) not in notes
            notes[(tail,cols[0])] = "3"
    measures = []
    for m in range(71):
        measures.append("\n".join("".join(notes.get((16*m+r,c),"0") for c in range(ncols)) for r in range(16)))
    text = ",\n".join(measures)
    return dict(**config, columns=ncols, notes=text, placements=flow.records)


def make_art():
    background = PROJECT / "out/thumbnail_1280.jpg"
    if background.exists():
        shutil.copy2(background, SONG / "background.jpg")
    elif not (SONG / "background.jpg").exists():
        raise FileNotFoundError("Restore the bundled song background before rebuilding.")
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    for filename,size in [("banner.png",(512,160)),("jacket.png",(512,512))]:
        im = Image.new("RGB",size,"#0a1029")
        d = ImageDraw.Draw(im)
        rng = np.random.default_rng(1420)
        for _ in range(130):
            x,y = rng.integers(0,size[0]),rng.integers(0,size[1])
            r = int(rng.choice([1,1,1,2]))
            d.ellipse((int(x)-r,int(y)-r,int(x)+r,int(y)+r),fill="#495487")
        if size[1] > 160:
            for r in [95,118,150]:
                d.ellipse((256-r,210-r,256+r,210+r),outline="#355e88",width=2)
            d.arc((120,74,392,346),205,337,fill="#5ee4dc",width=5)
            d.ellipse((248,202,264,218),fill="#f79470")
            yy = 358
        else:
            yy = 30
        d.text((24,yy),"RARE EARTH",font=ImageFont.truetype(font,43),fill="#f5f3ea")
        d.text((26,yy+55),"TECHNO REMIX",font=ImageFont.truetype(mono,20),fill="#70e0d4")
        d.text((26,yy+85),"ROBOT NINJA APOCALYPSE",font=ImageFont.truetype(mono,14),fill="#b8c1dc")
        im.save(SONG / filename)


def main():
    charts = [author(c) for c in CHARTS]
    bpmtext = ",\n".join(f"{s['beat']:.6f}={s['bpm']:.9f}" for s in TIMING["bpms"])
    labels = [(8,"VERSE 1"),(40,"VERSE 2"),(88,"BUILD"),(120,"DROP 1"),
              (168,"CHORUS"),(200,"VERSE RETURN"),(248,"FINAL DROP"),(276,"OUTRO")]
    header = (
        "#TITLE:Rare Earth;\n#SUBTITLE:(Techno Remix);\n"
        "#ARTIST:Robot Ninja Apocalypse;\n#GENRE:Techno;\n#CREDIT:Codex;\n"
        "#BANNER:banner.png;\n#BACKGROUND:background.jpg;\n#JACKET:jacket.png;\n"
        "#MUSIC:Rare_Earth_DDR.mp3;\n"
        f"#OFFSET:{TIMING['offset']:.7f};\n#SAMPLESTART:54.7604;\n#SAMPLELENGTH:18.0;\n"
        f"#DISPLAYBPM:{TIMING['bpm_range'][0]:.3f}:{TIMING['bpm_range'][1]:.3f};\n"
        "#SELECTABLE:YES;\n#STOPS:;\n#LASTSECONDHINT:127.96;\n"
        f"#BPMS:{bpmtext};\n"
    )
    sm = header
    ssc = "#VERSION:0.83;\n"+header
    ssc += "#TIMESIGNATURES:0=4=4;\n#TICKCOUNTS:0=4;\n"
    ssc += "#LABELS:"+",".join(f"{b}={name}" for b,name in labels)+";\n"
    for c in charts:
        sm += f"\n#NOTES:\n{c['type']}:\n{c['name']}:\n{c['difficulty']}:\n{c['meter']}:\n0,0,0,0,0:\n{c['notes']};\n"
        ssc += (
            f"\n#NOTEDATA:;\n#CHARTNAME:{c['name']};\n#STEPSTYPE:{c['type']};\n"
            f"#DESCRIPTION:{c['name']};\n#DIFFICULTY:{c['difficulty']};\n#METER:{c['meter']};\n"
            f"#CREDIT:Codex;\n#RADARVALUES:0,0,0,0,0;\n#NOTES:\n{c['notes']};\n"
        )
    (SONG / "Rare Earth (Techno Remix).sm").write_text(sm)
    (SONG / "Rare Earth (Techno Remix).ssc").write_text(ssc)
    source = PROJECT / "audio/Rare_Earth_DDR.mp3"
    shutil.copy2(source, SONG / "Rare_Earth_DDR.mp3")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == hashlib.sha256((SONG/source.name).read_bytes()).hexdigest()
    make_art()
    (ROOT / "analysis/choreography.json").write_text(json.dumps([
        {k:v for k,v in c.items() if k != "notes"} for c in charts
    ], indent=2)+"\n")
    print(f"Exported {len(charts)} charts to {SONG}")


if __name__ == "__main__":
    main()
