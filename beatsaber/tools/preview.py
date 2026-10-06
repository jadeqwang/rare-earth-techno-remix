"""Render all three exported maps with their actual timing and Ogg audio."""
from pathlib import Path
import argparse
import bisect
import json
import math
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from validate import BeatClock, check_audio

ROOT = Path(__file__).resolve().parents[1]
SONG = ROOT / "CustomLevels/Rare Earth (Techno Remix)"
OUT = ROOT / "preview"
OUT.mkdir(parents=True, exist_ok=True)
INFO = json.loads((SONG / "Info.dat").read_text())
PROV = json.loads((ROOT / "analysis/provenance.json").read_text())
W, H, FPS = 1280, 720, 60
COLORS = [(255, 84, 110), (76, 176, 255)]
DIRS = {0: (0, -1), 1: (0, 1), 2: (-1, 0), 3: (1, 0),
        4: (-1, -1), 5: (1, -1), 6: (-1, 1), 7: (1, 1)}
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONTS = {n: ImageFont.truetype(FONT_PATH, n) for n in (12, 13, 14, 16, 18)}
BOLD = {n: ImageFont.truetype(BOLD_PATH, n) for n in (18, 22, 30)}
PANELS = []
for index, entry in enumerate(INFO["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"]):
    chart = json.loads((SONG / entry["_beatmapFilename"]).read_text())
    clock = BeatClock(INFO["_beatsPerMinute"], chart["bpmEvents"])
    notes = [{**n, "t": clock.seconds_at(n["b"])} for n in chart["colorNotes"]]
    PANELS.append(dict(x=24 + 420 * index, w=392, entry=entry, clock=clock, notes=notes,
                       times=[n["t"] for n in notes]))

BASE = Image.new("RGB", (W, H), "#080d1b")
d = ImageDraw.Draw(BASE)
cover = Image.open(SONG / "cover.png").convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
BASE.paste(cover, (24, 16))
d.text((104, 16), "RARE EARTH", font=BOLD[30], fill="#f7f3e8")
d.text((105, 54), "TECHNO REMIX  /  Robot Ninja Apocalypse", font=FONTS[16], fill="#6bddd8")
d.text((977, 22), "BEAT SABER", font=BOLD[22], fill="#f7f3e8")
d.text((977, 53), "Standard / two sabers", font=FONTS[14], fill="#a9b7ce")
for p in PANELS:
    x, w = p["x"], p["w"]
    d.rounded_rectangle((x, 96, x + w, 610), radius=12, fill="#0e1829", outline="#293a52")
    d.text((x + 18, 111), p["entry"]["_difficulty"].upper(), font=BOLD[22], fill="#f4f0e6")
    d.text((x + 18, 143), f"{len(p['notes'])} blocks  /  {len(p['notes']) / PROV['duration_s']:.2f} notes/sec", font=FONTS[14], fill="#9aafc8")
    # A perspective tunnel with the hit grid at the near plane.
    cx, cy = x + w / 2, 344
    for column in range(5):
        xx = cx + (column - 2) * 68
        d.line((cx + (xx - cx) * .15, 288, xx, 564), fill="#20334e", width=1)
    for row in range(4):
        yy = 448 - (row - 1) * 68
        d.line((cx - 136, yy, cx + 136, yy), fill="#243b54", width=1)
    d.line((cx - 136, 564, cx + 136, 564), fill="#559895", width=2)
    d.text((x + 25, 580), "LEFT", font=FONTS[12], fill=COLORS[0])
    d.text((x + w - 75, 580), "RIGHT", font=FONTS[12], fill=COLORS[1])
d.text((24, 674), "Autoplay visualization from exported maps  /  arrows show cut direction", font=FONTS[13], fill="#8d9eb7")
d.text((24, 697), "Original DDR track and tempo  /  VR playtest pending", font=FONTS[12], fill="#72849f")


def project(p, n, delta):
    # Arrival plane is exactly delta=0. Positive delta recedes into the tunnel.
    scale = 1 / (1 + delta * 1.65)
    cx, cy = p["x"] + p["w"] / 2, 344
    xx = cx + (n["x"] - 1.5) * 68 * scale
    yy = cy + (104 - (n["y"] - 1) * 68) * scale
    return xx, yy, 48 * scale


def cube(draw, x, y, size, color, direction):
    if size < 4:
        return
    half = size / 2
    depth = size * .16
    dark = tuple(int(v * .52) for v in color)
    light = tuple(min(255, int(v * 1.18)) for v in color)
    draw.polygon([(x - half, y - half), (x - half + depth, y - half - depth),
                  (x + half + depth, y - half - depth), (x + half, y - half)], fill=light)
    draw.polygon([(x + half, y - half), (x + half + depth, y - half - depth),
                  (x + half + depth, y + half - depth), (x + half, y + half)], fill=dark)
    draw.rectangle((x - half, y - half, x + half, y + half), fill=color, outline=light, width=1)
    dx, dy = DIRS[direction]
    length = math.hypot(dx, dy)
    dx, dy = dx / length, dy / length
    ax, ay = -dy, dx
    # White filled arrow remains centered on the note face for every direction.
    points = []
    for along, across in [(-.30, -.065), (.035, -.065), (.035, -.18),
                          (.32, 0), (.035, .18), (.035, .065), (-.30, .065)]:
        points.append((x + (dx * along + ax * across) * size,
                       y + (dy * along + ay * across) * size))
    draw.polygon(points, fill="#fffdf7")


def render(t):
    im = BASE.copy()
    draw = ImageDraw.Draw(im)
    for p in PANELS:
        times, notes = p["times"], p["notes"]
        first, last = bisect.bisect_right(times, t), bisect.bisect_right(times, t + 2.5)
        # Far notes first, near notes last. Notes vanish at the first frame >= hit.
        for n in reversed(notes[first:last]):
            xx, yy, size = project(p, n, n["t"] - t)
            cube(draw, xx, yy, size, COLORS[n["c"]], n["d"])
        # Brief post-hit saber trace depicts the direction of the consumed block.
        begin = bisect.bisect_left(times, t - .12)
        for n in notes[begin:first]:
            age = t - n["t"]
            if age < 0:
                continue
            xx, yy, _ = project(p, n, 0)
            dx, dy = DIRS[n["d"]]
            norm = math.hypot(dx, dy)
            dx, dy = dx / norm, dy / norm
            frac = age / .12
            bright = tuple(int(v * (1 - .65 * frac)) for v in COLORS[n["c"]])
            draw.line((xx - dx * 29, yy - dy * 29, xx + dx * 29, yy + dy * 29), fill=bright, width=4)
            draw.ellipse((xx - 4, yy - 4, xx + 4, yy + 4), fill="#f6f7ee")
        draw.text((p["x"] + 18, 173), f"HIT {first:03d} / {len(notes)}", font=FONTS[13], fill="#7e99b3")
    section = next((s["label"].split(" (")[0] for s in PROV["sections"] if s["t"] <= t < s["end"]), "outro")
    clock = PANELS[0]["clock"]
    segment = bisect.bisect_right(clock.seconds, t) - 1
    bpm = clock.bpms[max(0, segment)]
    draw.rectangle((24, 625, 1256, 630), fill="#20324a")
    draw.rectangle((24, 625, 24 + 1232 * min(1, t / PROV["duration_s"]), 630), fill="#65d8d0")
    draw.text((24, 643), f"{int(t) // 60}:{int(t) % 60:02d} / 2:08    {bpm:.1f} BPM    {section.upper()}", font=FONTS[16], fill="#d5deea")
    return im


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", action="store_true")
    args = parser.parse_args()
    for t in [18.8, 54.9, 112.5]:
        render(t).save(OUT / f"choreography-{t:.1f}s.png")
    if args.stills:
        return
    video = OUT / "Rare_Earth_Beat_Saber_preview.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
           "-i", str(SONG / INFO["_songFilename"]), "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-t", str(PROV["duration_s"]), "-movflags", "+faststart", str(video)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as process:
        for i in range(math.ceil(PROV["duration_s"] * FPS)):
            process.stdin.write(render(i / FPS).tobytes())
            if i % (FPS * 20) == 0:
                print(f"Rendered {i / FPS:.0f}s / {PROV['duration_s']:.2f}s", flush=True)
        process.stdin.close()
        if process.wait():
            raise RuntimeError("Preview encoding failed")
    # Alignment test is run against encoded output, not only input PCM.
    audio = check_audio(video)
    report = dict(passed=True, fps=FPS, duration_s=PROV["duration_s"],
                  max_visual_hit_lateness_ms=1000 / FPS, audio=audio,
                  kind="Autoplay visualization; not footage from Beat Saber")
    (ROOT / "analysis/preview-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {video}", flush=True)


if __name__ == "__main__":
    main()
