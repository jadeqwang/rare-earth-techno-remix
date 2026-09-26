# RARE EARTH — music video

A music video for **"Rare Earth"** (DDR / techno version), a song about hoping to find intelligent
life, written in 2011 for a SETI event.

**▶ [`out/rare_earth_1080p.mp4`](out/rare_earth_1080p.mp4)** (1920×1080, 24 fps, 2:09). DOT has the
v3 hairstyle: centre part, long curtain bangs, long layers. The first cut, with a hime cut, is in the
git history at commit `8dedea7`.

![Twelve frames from the video](docs/storyboard.jpg)

Every frame you see is drawn by JavaScript: WebGL shaders and canvas type, rendered frame by frame
in headless Chromium. AI video generation (Seedance 2.5) was used only as rotoscope reference for
DOT's performances and the other world's plates. The generated footage itself never appears. The
renderer reads it as guide maps (edges, tone, matte, colour class) and redraws it as riso-print ink,
halftone and neon light.

## The idea

Two lonely worlds, each singing into the dark, find out the other one was listening the whole
time, and the song itself is the signal. Verses 1–2 are Earth asking. The build reveals
**ETZ-1715 b**, a fictional world in the Earth Transit Zone that could have watched *our* planet
transit the Sun. Verse 3 is the Great Filter: the Drake equation's **L**, weapons, wars, the blank,
and *keep up funding*. Verses 4–5 repeat as call-and-response between the two worlds. The final drop
is contact: the galaxy lights up with a web of civilizations, and the reply decodes as **STILL HERE.**

Earth gets at least as much screen time as the other world. The other world is only ever seen
zoomed out, as cities, a listening field, a signal tower, a satellite train and a space elevator,
never its people. The full treatment is in [`docs/TREATMENT.md`](docs/TREATMENT.md) and
[`docs/PROCESS.md`](docs/PROCESS.md).

## How it was made

| Stage | Where | What |
|---|---|---|
| Song analysis | `pipeline/lyrics_align.py`, `pipeline/audio_map.py` | vocal stem (MDX-Net Kim_Vocal_2) → Whisper large-v3-turbo → word timings aligned to the canonical lyrics and snapped to vocal onsets; beat grid (the tempo accelerates 129.7 → 135 BPM), kick/snare onsets, per-frame features → `render/data/audio.json` |
| Design | `design/`, `pipeline/prompts/` | style board (SIGNAL PRINT), DOT character sheets, Earth and ETZ-1715 b world sheets (GPT Image 2.5, Nano Banana Pro, Seedream 5 Pro, FLUX.2 max, Grok Imagine) |
| Base performances | `pipeline/seedance_shots.py`, `pipeline/run_seedance.py` | 23 shots × multiple takes on Seedance 2.5 (720p), each passed the cut song audio as a lip-sync reference and the character sheet as an image reference |
| Lip-sync verification | `pipeline/sync/` | anime face / mouth tracking → mouth-openness curve, cross-correlated with the vocal envelope over exactly the window each shot uses; per-take lag measured and corrected (`clipTime = t − start + lag`); visual word strips for manual checks |
| Rotoscope guides | `pipeline/roto_extract.py`, `pipeline/extract_selects.py` | XDoG line art, bilateral tone, green-screen matte with despill, colour classes; the selected takes are archived in `pipeline/base_clips/` |
| Renderer | `render/` | three.js r186 + canvas 2D, deterministic `renderAt(t)`; scenes in `render/src/scenes/`, the edit in `render/src/timeline.js` |
| Sound design | `pipeline/sound_design.py` | receiver static, star pings, an ElevenLabs v3 radio voice ("Still listening.") in the intro, a signal dropout at the blank, and the reply ("Still here.") after the last note. The song itself is untouched |

Generation ran through Cloudflare's unified model catalog (`pipeline/gen.py`) with a small relay
Worker (`pipeline/relay/`) that receives async webhooks and mirrors results into KV. Every request is
logged in `pipeline/ledger.jsonl`. Total generation spend was roughly $115. Seedance accounts for
about $110: 103 runs, 478 s of 720p video, including the full re-shoot for DOT's new hairstyle (v3).
The rest is about 19 image runs plus small change for voice, transcription and one video review.

## Render it yourself

```bash
cd render && npm install
# guides for the selected takes (writes /tmp/work/guides, ~1.3 GB):
python3 ../pipeline/extract_selects.py
# sound-design mix (needs the Cloudflare account used by pipeline/gen.py for the voices):
python3 ../pipeline/sound_design.py
# one still, or the whole film (3 browser processes; ~1 s per 1080p frame each on CPU)
node tools/render.mjs --stills 1.0,54.8 --w 1920 --h 1080 --outdir /tmp/work/stills
node tools/render.mjs --from 0 --to 129.6 --fps 24 --w 1920 --h 1080 --jobs 3 \
  --audio /tmp/work/sfx/Rare_Earth_DDR_sfx.wav --out ../out/rare_earth_1080p.mp4
# live preview in a browser, with the song:
npm run serve   # then open http://127.0.0.1:8800/index.html?play=1&fit=1 and click
```

Python needs `numpy scipy soundfile librosa opencv-python-headless<5 pillow audio-separator`.
Rendering uses the Chromium that Playwright finds (`CHROME=/path/to/chrome` to override) with
SwiftShader, so no GPU is needed.

## Credits

* Song: "Rare Earth", written in 2011 for a SETI event (`audio/Rare_Earth_DDR.mp3`).
* Fonts: Archivo, Noto Serif Display, Noto Sans SC (subset to the title characters), JetBrains Mono,
  Anton, Big Shoulders Display, Instrument Serif, Space Mono, Unbounded, VT323. All SIL Open Font
  License; the licence texts are in `render/assets/fonts/`.
* Coastlines and populated places: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
* References, redrawn and not reproduced: Voyager 1's *Pale Blue Dot* (1990), the Big Ear *Wow!* signal
  printout (1977), Artemis II's Earthset (2026), the Allen Telescope Array, the Drake equation, and
  Kaltenegger & Faherty's Earth Transit Zone (Nature, 2021).
