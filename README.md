# RARE EARTH — music video

A music video for **"Rare Earth"** (DDR / techno version), a song about hoping to find intelligent
life, written by Jade Q Wang and Charlie van Norman (Robot Ninja Apocalypse) for the SETI crowdfunding
campaign in 2011.

**▶ [`out/rare_earth_1080p.mp4`](out/rare_earth_1080p.mp4)** (1920×1080, 24 fps, 2:09). DOT has the
v3 hairstyle: centre part, long curtain bangs, long layers. This cut also renames the other world
**Echo**, ends on its beacon rather than an impossible reply, and gives every shot of Echo its own
footage (`docs/PROCESS.md` §3c). The release pass (§3d) sets the character sheet's lettering on DOT's
jacket (RARE EARTH) and sleeve patch (1420 MHz), shows a nuclear exchange on *or self-destruct* with that
whole line kept on screen, and credits the songwriters on the end card. The lip-sync pass (§3e) checked
every drawing of her face against the vocal, syllable by syllable, and replaced the mouth in the 90 of
355 where it was wrong: open through rests, late onto words, shut on held vowels, closures missed. Pass 6 (§3f) rebuilds the build into drop 1: Echo's signal tower is a new rotoscoped plate that charges on the
snare roll, and the flips that follow have Earth's array and Echo's field answer each other into the title. The 4K
thumbnail is [`out/thumbnail_4k.jpg`](out/thumbnail_4k.jpg). The first cut, with a hime cut, is in the git history at commit `8dedea7`.

![Twelve frames from the video](docs/storyboard.jpg)

Every frame you see is drawn by JavaScript: WebGL shaders and canvas type, rendered frame by frame
in headless Chromium. AI video generation (Seedance 2.5) was used only as rotoscope reference for
DOT's performances and the other world's plates. The generated footage itself never appears. The
renderer reads it as guide maps (edges, tone, matte, colour class) and redraws it as riso-print ink,
halftone and neon light.

## The idea

Two lonely worlds, each singing into the dark, find out the other one was listening the whole
time, and the song itself is the signal. Verses 1–2 are Earth asking. The build reveals
**Echo**, a fictional world 217 light-years away in the Earth Transit Zone, the part of the sky from
which *our* planet can be seen crossing the Sun. Verse 3 is the Great Filter: the launch that could
carry us to the stars *or* a nuclear exchange over the pole, the Drake equation's **L**, weapons, wars,
the blank, and *keep up funding*. Verses 4–5 repeat as call-and-response between
the two worlds. The final drop is contact: the galaxy lights up with a web of civilizations, and
Echo's beacon, sent in 1809, decodes as **STILL HERE.**

Echo is too far away to have heard us: our radio has only travelled about 100 light-years. It could
have seen Earth transit the Sun, so the message is their beacon, not a reply. The transmission Earth
sends in the video (2026) reaches Echo in 2243.

Earth gets at least as much screen time as the other world. The other world is only ever seen
zoomed out, as cities by day and night, a listening field, a lone dish on a cliff, a sea under two
moons, a signal tower and its beam, a space elevator, and its night side from orbit, never its people.
No plate of it plays twice. The full treatment is in [`docs/TREATMENT.md`](docs/TREATMENT.md) and
[`docs/PROCESS.md`](docs/PROCESS.md).

## How it was made

| Stage | Where | What |
|---|---|---|
| Song analysis | `pipeline/lyrics_align.py`, `pipeline/audio_map.py` | vocal stem (MDX-Net Kim_Vocal_2) → Whisper large-v3-turbo → word timings aligned to the canonical lyrics and snapped to vocal onsets; beat grid (the tempo accelerates 129.7 → 135 BPM), kick/snare onsets, per-frame features → `render/data/audio.json` |
| Design | `design/`, `pipeline/prompts/` | style board (SIGNAL PRINT), DOT character sheets, Earth and Echo world sheets (GPT Image 2.5, Nano Banana Pro, Seedream 5 Pro, FLUX.2 max, Grok Imagine); their labels were fact-checked and corrected in pass 3 (`pipeline/sheet_fixes/`) |
| Base performances | `pipeline/seedance_shots.py`, `pipeline/run_seedance.py` | 23 shots × multiple takes on Seedance 2.5 (720p), each passed the cut song audio as a lip-sync reference and the character sheet as an image reference |
| Lip sync | `pipeline/sync/` | per-take lag measured against the vocal envelope over exactly the window each shot uses (`clipTime = t − start + lag`). Then every drawing is checked against an exposure sheet read syllable by syllable off the stem's spectrogram (`lipsheet.json`); where the mouth is wrong, a right one is borrowed from another frame of the same take, registered onto the face and cloned in, with LivePortrait for head pose and the odd redraw (`relip.py`); `lipcheck.py` measures the result as played |
| Plate fixes | `pipeline/plate_fixes/` | the lettering the takes invented ("PACE EARTH", "D20 IHz") is painted out and the sheet's RARE EARTH and 1420 MHz set in its place, tracked through every frame (the patch's ring fitted as an ellipse) |
| Rotoscope guides | `pipeline/roto_extract.py`, `pipeline/extract_selects.py` | XDoG line art, bilateral tone, green-screen matte with despill, colour classes; the selected takes are archived in `pipeline/base_clips/` |
| Renderer | `render/` | three.js r186 + canvas 2D, deterministic `renderAt(t)`; scenes in `render/src/scenes/`, the edit in `render/src/timeline.js` |
| Sound design | `pipeline/sound_design.py` | receiver static, star pings, an ElevenLabs v3 radio voice ("Still listening.") in the intro, a signal dropout at the blank, and Echo's beacon ("Still here.") after the last note. The song itself is untouched |

Generation ran through Cloudflare's unified model catalog (`pipeline/gen.py`) with a small relay
Worker (`pipeline/relay/`) that receives async webhooks and mirrors results into KV. Every request is
logged in `pipeline/ledger.jsonl`. Total generation spend was roughly $147. Seedance accounts for
about $142: 103 runs, 478 s of 720p video up to and including the full re-shoot for DOT's new
hairstyle (v3), then about $17 of lip-sync re-rolls and about $15 for Echo's new plates (13 runs, 65 s;
see `docs/PROCESS.md` §3c). The rest is about 19 image runs plus small change for voice, transcription
and one video review.

## Render it yourself

```bash
cd render && npm install
# the corrected takes are archived in pipeline/base_clips/; to rebuild them from the takes as generated:
#   python3 ../pipeline/plate_fixes/fix_lettering.py   # lettering on the jacket and the sleeve patch
#   python3 ../pipeline/sync/remouth.py sd16           # alone2's mouths re-timed (needs the vocal stem, /tmp/work/vocals.wav)
#   python3 ../pipeline/sync/relip.py                  # every other singing shot's mouths checked against lipsheet.json
# guides for the selected takes (writes /tmp/work/guides, ~1.5 GB):
python3 ../pipeline/extract_selects.py
# sound-design mix (needs the Cloudflare account used by pipeline/gen.py for the voices):
python3 ../pipeline/sound_design.py
# one still, or the whole film (3 browser processes; ~1 s per 1080p frame each on CPU)
node tools/render.mjs --stills 1.0,54.8 --w 1920 --h 1080 --outdir /tmp/work/stills
# the 4K thumbnail (a frame of the film with the title card's lettering in place of its own type)
node tools/thumbnail.mjs --t 24.5 --w 3840 --h 2160 --out ../out/thumbnail_4k.png
node tools/render.mjs --from 0 --to 129.6 --fps 24 --w 1920 --h 1080 --jobs 3 \
  --audio /tmp/work/sfx/Rare_Earth_DDR_sfx.wav --out ../out/rare_earth_1080p.mp4
# live preview in a browser, with the song:
npm run serve   # then open http://127.0.0.1:8800/index.html?play=1&fit=1 and click
```

Python needs `numpy scipy soundfile librosa opencv-python-headless<5 pillow audio-separator onnxruntime`
(`relip.py` downloads LivePortrait's ONNX models from GitHub on first use).
Rendering uses the Chromium that Playwright finds (`CHROME=/path/to/chrome` to override) with
SwiftShader, so no GPU is needed.

## Credits

* Song: "Rare Earth", written by Jade Q Wang and Charlie van Norman (Robot Ninja Apocalypse) for the SETI
  crowdfunding campaign in 2011 (`audio/Rare_Earth_DDR.mp3`).
* Fonts: Archivo, Noto Serif Display, Noto Sans SC (subset to the title characters), JetBrains Mono,
  Anton, Big Shoulders Display, Instrument Serif, Space Mono, Unbounded, VT323. All SIL Open Font
  License; the licence texts are in `render/assets/fonts/`.
* Coastlines and populated places: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
* References, redrawn and not reproduced: Voyager 1's *Pale Blue Dot* (1990), the Big Ear *Wow!* signal
  printout (1977), Artemis II's Earthset (2026), the Allen Telescope Array, the Drake equation, and
  Kaltenegger & Faherty's Earth Transit Zone (Nature, 2021).
