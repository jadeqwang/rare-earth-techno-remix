"""Subtitles for the release: the sung lines from render/data/audio.json (aligned to the vocal stem, the same timings
the on-screen type uses) plus the two voices of the sound design (pipeline/sound_design.py).

    python3 pipeline/subtitles.py        # writes out/rare_earth.en.srt and out/rare_earth.en.vtt
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", "rare_earth.en"))
MAXLEN = 42          # longer lines are broken in two (the usual subtitle line limit)

# the radio voice in the cold open and Echo's beacon after the last note (placed at these times in sound_design.py)
VOICES = [(0.88, 2.40, "<i>Still listening.</i>"), (128.02, 129.50, "<i>Still here.</i>")]


def wrap(text):
    if len(text) <= MAXLEN:
        return text
    words = text.split()
    # break at the word boundary closest to the middle, preferring after a comma
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        cost = abs(len(a) - len(b)) - (8 if a.endswith(",") else 0)
        if best is None or cost < best[0]:
            best = (cost, a, b)
    return best[1] + "\n" + best[2]


def cues():
    lines = json.load(open(os.path.join(HERE, "..", "render", "data", "audio.json")))["lines"]
    out = list(VOICES[:1])
    for k, l in enumerate(lines):
        end = l["end"]
        if k + 1 < len(lines):
            end = min(end, lines[k + 1]["t"] - 0.04)     # never overlap the next line
        out.append((l["t"], end, wrap(l["text"])))
    out += VOICES[1:]
    return out


def stamp(t, sep):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


if __name__ == "__main__":
    cs = cues()
    with open(OUT + ".srt", "w") as f:
        for i, (a, b, text) in enumerate(cs, 1):
            f.write(f"{i}\n{stamp(a, ',')} --> {stamp(b, ',')}\n{text}\n\n")
    with open(OUT + ".vtt", "w") as f:
        f.write("WEBVTT\n\n")
        for a, b, text in cs:
            f.write(f"{stamp(a, '.')} --> {stamp(b, '.')}\n{text}\n\n")
    print(f"{len(cs)} cues -> {OUT}.srt, {OUT}.vtt")
