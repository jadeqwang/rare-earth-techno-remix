# Rare Earth (Techno Remix) — Beat Saber

Three Standard, two-saber maps for the **same 2:07.960 recording used by the DDR
pack**. The original `audio/Rare_Earth_DDR.mp3` is converted to Ogg Vorbis for
Beat Saber, with no trimming, padding, or tempo changes.

[Download the Beat Saber map pack (ZIP)](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/beatsaber/Rare_Earth_Beat_Saber_Pack.zip).
The ZIP contains `Info.dat`, all three
difficulty files, `song.ogg`, and the existing Rare Earth cover artwork, directly
at its root.

| Difficulty | Blocks | Average notes/sec | Jump speed |
|---|---:|---:|---:|
| Normal | 228 | 1.78 | 11 |
| Hard | 357 | 2.79 | 14 |
| Expert | 497 | 3.88 | 16 |

Normal uses mostly half-note and quarter-note phrases. Hard adds short eighth
figures and diagonals. Expert develops the drops into alternating eighth
streams. Each hand alternates forehand and backhand directions, with 135–180
degree changes. Double hits emphasize selected musical accents. Inner blocks
stay below eye level, and inward diagonals remain on the outer columns. The
first block arrives at 3.7745 seconds; the final accent at 126.2041 seconds.
The charts contain beat-matched lights, with no bombs, walls, or required
mapping extensions. Difficulty labels remain provisional until a VR playtest.

The track accelerates from **129.143 to 135.793 BPM**. Each exported chart has
71 native BPM events that reproduce the independently parsed DDR timing. The
61.1 ms lead-in is encoded into object positions; `songTimeOffset` remains zero,
because the [format documentation](https://bsmg.wiki/mapping/map-format/info.html)
describes that offset field as deprecated. Charts use v3.3.0 with v2.1.0 song
metadata, as documented in the [BSMG format reference](https://bsmg.wiki/mapping/map-format.html).

## Install and preview

On **PC VR**, create a folder named `Rare Earth (Techno Remix)` inside your Beat
Saber installation's `Beat Saber_Data/CustomLevels/` directory. Extract the ZIP
into that folder, so `Info.dat` sits directly inside it. Restart Beat Saber,
open Custom Levels, and choose Normal, Hard, or Expert.

For **standalone Quest**, import the ZIP using your existing custom-song setup.
The installation method depends on your Quest setup and supported game version;
see the maintained [BSMG Quest guide](https://bsmg.wiki/quest-modding.html).

[Watch the full-length preview](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/beatsaber/preview/Rare_Earth_Beat_Saber_preview.mp4): all three exported charts side
by side with their packaged audio. It is an autoplay visualization, rather than
footage from Beat Saber. Arrow directions show the cut; short colored traces
show the consumed block's swing. Visual hits occur on the first 60 fps frame at
or after the note time, within 16.7 ms. Three PNG stills are also included.

## Validation and rebuilding

`analysis/validation.json` records independent agreement with StepMania's SSC
timing parser at every sixteenth-note position, note bounds and overlap checks,
alternating directions, same-hand spacing, and ZIP integrity. Audio correlation
near the beginning, middle, and end checks conversion alignment against the
DDR MP3. `analysis/preview-check.json` checks the encoded video's audio against
that same source. These checks do not substitute for loading the map in Beat
Saber or playing it in VR; neither has been performed here.

The scripts reuse the DDR project's existing Python environment:

```bash
ddr/.venv/bin/python beatsaber/tools/build.py
ddr/.venv/bin/python beatsaber/tools/validate.py
ddr/.venv/bin/python beatsaber/tools/preview.py
```

Run those commands from the project root. For a separate environment, install
`numpy`, `Pillow`, `scipy`, `simfile`, and `imageio-ffmpeg`.

Music: Robot Ninja Apocalypse; written by Jade Q Wang and Charlie van Norman.
Beat Saber mapping and preview: Codex. Cover: existing Rare Earth DDR artwork.
