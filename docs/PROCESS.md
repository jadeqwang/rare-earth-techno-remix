# Process notes

How the video was made and checked, and what was decided along the way. See `README.md` for the
short version and how to run things.

## 1. Song analysis

* **Stems.** Demucs weights could not be downloaded from this environment, so the vocal stem comes from
  `audio-separator` with the UVR **Kim_Vocal_2** MDX-Net model. BS-Roformer was tried and was too slow on
  CPU (about 71 s per chunk).
* **Lyrics.** Whisper large-v3-turbo on Workers AI transcribes the vocal stem. `pipeline/lyrics_align.py`
  aligns the transcript to the canonical lyrics with difflib and snaps each word to the nearest vocal
  onset. Word starts within a line must be strictly increasing, at least 70 ms apart. The blank
  "( )" in verse 3 is kept as a timed gap, and "Keep" after it is pinned by hand to 61.86 s.
* **Tempo.** The track accelerates from 129.7 to 135 BPM. The beat grid is a degree-4 polynomial fit to
  tracked beats, not a constant BPM, so beat-quantised cuts stay on the beat through the final drop.
* **Features.** Kick and snare onsets and per-frame (24 fps) energy go into `render/data/audio.json`.
  Everything in the renderer that pulses (zoom punch, ping rings, misregistration, dish choreography)
  reads from this file.

## 2. Design

The style is **SIGNAL PRINT**: risograph anime in a few spot inks. It has three modes. *Print* is
halftone ink on paper, *light* is neon linework on black with bloom, and *data* is 1-bit dither. The
ink table, characters and worlds are in `TREATMENT.md`. The sheets in `design/` were generated as
references for Seedance and for the renderer's palette. The prompts are in `pipeline/prompts/`.

Image models tried: GPT Image 2.5 (best for the character sheet, which is canonical), Nano Banana Pro
(the flat style board), Seedream 5 Pro, FLUX.2 max and Grok Imagine 2.0 (Grok needs `b64_json` output
when run in background mode).

## 3. Base performances (Seedance 2.5) and the lip-sync loop

* Each of the 23 base shots (`pipeline/seedance_shots.py`) was generated at 720p / 24 fps. The inputs
  were the DOT character sheet as an image reference (cropped to 16:9, because references wider than
  2.5:1 are rejected) and **the cut song audio for that shot as an audio reference**.
  `generate_audio: false` avoids the copyright filter on the output track.
* Runs are asynchronous. `pipeline/gen.py` submits with a webhook to a relay Worker
  (`pipeline/relay/relay_worker.js`), which stores the result and mirrors the media into KV, because the
  provider's media host is not reachable from here. Synchronous calls are cut off at about 30 s.
  `run_seedance.py` keeps the manifest under a file lock (parallel collectors once raced and dropped two
  takes).
* **Verification.** `pipeline/sync/mouth.py` tracks the face (anime LBP cascade with a skin-ratio test
  and median-track rejection) and measures mouth openness as the non-skin area inside a mouth ellipse.
  For extreme close-ups the mouth region is fixed by hand, after checking each one with crops (two
  hand-picked regions were wrong at first). `score.py` cross-correlates openness with the vocal-stem
  envelope, but **only over the window the edit actually uses**. Whole-clip scores were misleading,
  because Seedance often idles before and after the reference phrase. The best lag is written into
  `selects.json` and applied in the renderer (`clipTime = t − start + lag`). `wordstrip.py` renders
  face crops at every sung word onset for five candidate lags, as the visual check.

| shot | lyric | take | lag | corr @ lag | corr @ 0 |
|---|---|---|---|---|---|
| sd03 | Are you still there | 12046ab509 | +0.125 s | 0.68 | 0.42 |
| sd06 | The beating blinking of a star | 8a7e7c3e89 | −0.083 s | 0.46 | 0.33 |
| sd07 | not that far from my own | efef2556bd | −0.167 s | 0.45 | 0.33 |
| sd08 | How could we be alone | 07ecd36aff | +0.167 s | 0.53 | 0.47 |
| sd09 | Keep on looking | 38a6fbaf1f | 0 | 0.91 | 0.91 |
| sd10 | Our science has a vision | 601824893f | +0.042 s | 0.43 | 0.40 |
| sd12 | Are you still there (V4) | da838b364d | −0.042 s | 0.46 | 0.42 |
| sd13 | Your signal here I think I've caught | 3cfdb90d7d | +0.042 s | 0.31 | 0.30 |
| sd14 | The beating blinking of a star (V5) | 9c9b39007d | +0.083 s | 0.70 | 0.50 |
| sd15 | far from my own (ECU) | bac460481f | −0.167 s | 0.42 | 0.08 |

  The correlation scores sd11 (*Do you still care*, V4) at 0.04. The camera pushes in through that
  take, so the face in a fixed crop keeps growing and the openness curve drifts with it. It was accepted
  on the word strip instead: a small round mouth on the held "Do", then wide open on "care". Measured
  lags fall within about ±0.17 s, which is within 4 frames at 24 fps.

## 4. Rotoscope guides

`pipeline/roto_extract.py` turns each selected take into per-frame guide maps: XDoG line art (R),
bilateral-filtered tone (G), a green-screen matte with despill (B), and a smoothed colour frame used
only to *classify* regions into inks (orange accents, blue hair, skin). The renderer
(`render/src/roto.js`) redraws the frame from these maps:

* halftone shadow ink, flat accents and black line in *print*;
* glowing linework, halftone fill and luminous environment fill in *light*.

Characters are drawn on twos (12 drawings per second) with a little line boil. Camera moves, type and
effects run on ones. The selected takes are archived, re-encoded, in `pipeline/base_clips/`, so the
guides can be rebuilt. They are never composited into the video.

## 5. Renderer

three.js r186 on WebGL2, run headless in Chromium with SwiftShader, so no GPU is needed. `renderAt(t)` is
deterministic. `tools/render.mjs` captures frames with one browser process per job (pages that share
one browser contend for the same GPU process) and muxes with ffmpeg.

* Procedural scenes: sky, dish array (42 dishes, beat-driven choreography), Earth globe (Natural Earth
  land and populated places, day/night and city blink), Voyager pale-blue-dot bands, zoom-out with
  Earthset, spectrogram waterfall, the Wow! printout, JWST-style star, transit light curve, mutual
  transit, the ringed planet (with a satellite train and space elevator), the other world's tower and
  skies, petal dishes, the galaxy (42k points), and the contact graph. The contact graph is a minimum
  spanning tree plus nearest-neighbour links, revealed in order of Dijkstra distance from Earth.
  Drake equation, the brutalist funding window, the journey beam, split screens and the end card are
  further scenes.
* `timeline.js` is the edit: every shot is placed on word onsets and the tracked beat grid.
* Global rhythm layer: kick zoom punch, chromatic aberration and shake in the drops, misregistration on
  the snare, and two-frame impact frames on the section hits.
* Two coordinate conventions coexist: 1920×1080 design px, y-down in canvas and y-up in shaders.
  Mixing them up caused several early bugs (the moon at the top of frame, flipped textures, the type
  layer upside-down).

## 6. Review passes

The whole film was rendered at 540p three times and reviewed as contact sheets (every 0.5 s) and
full-size stills. What each pass changed:

1. **Preview 1:** dishes read as mushrooms and the petal dishes as umbrellas; the light-mode 3D was
   overblown; keywords overflowed the frame; the first frame was black; NaN black blobs came from link
   geometry without normals; galaxy links were invisible. Fixed: dishes and petals face the camera, a
   "blueprint neon" 3D look, auto-fit type, NaN guards, 2D glow strokes for the galaxy links.
2. **Preview 2:** the cold open was not a strong enough hook. Added the animated poster (star flare,
   title plates snapping into register, halftone dissolve, typed HUD), the ETZ-1715 b chapter card,
   Earthset in the zoom-out, two-beat cuts in the final drop, burst backgrounds for performance shots,
   a geometric transit light curve, a bigger Drake equation, the planet push-in, the se05 rotoscope for
   their listening field, and splits for *science / vision*.
3. **Preview 3:** lyrics still sat on DOT's face in eight shots. Keyed shots are now re-framed so the
   words sit in the calm third; the extreme close-up lyric moved onto the dark hair and jacket. Other
   changes:
   * The dishes got real mounts (a thin pole under a shallow disc still read as an umbrella).
   * The planet got orbital infrastructure.
   * The contact web now reaches the whole disc; the old kNN graph was disconnected.
   * The Drake equation fits the frame with **L** circled.
   * *How could we be alone* is bilingual across the split.
   * The pale-blue-dot callback now plays from their side.
   * A signal-lost static burst covers the blank, and the reply lands on the end card.
4. **Final 1080p:** reviewed the same way before encoding.

## 7. Sound design

`pipeline/sound_design.py` leaves the song untouched and places everything where the track is quiet:

* **Cold open (0–3.4 s):** receiver static, three star-blink pings, and a radio-filtered **ElevenLabs v3**
  voice, *"Still listening."*
* **The blank (61.03–61.45 s):** the signal drops out into gated static.
* **After the last note:** an FSK data burst, then the reply *"Still here."* (two pitched copies,
  ring-modulated, with a light-years echo), synced to the end card's pulse arriving at Sol.

Each processed voice is transcribed back with Whisper before mixing, and both pass verbatim. The layer
peaks at −4.4 dBFS and the mix is never normalised, so the song's level is unchanged. The video runs
1.6 s past the song to let the reply land.

## 8. Delivery

The frames carry a lot of detail: halftone screens, paper tooth and line boil. At CRF 20, x264 needed
about 27–30 Mbit/s for the opening. GitHub rejects files over 100 MB, so the release file
(`out/rare_earth_1080p.mp4`) is a two-pass H.264 High-profile encode at about 5.6 Mbit/s with 192 kbit/s
AAC.

On the hardest 4-second test segment, H.264 at 5.5 Mbit/s scored an SSIM of 0.91 against the source
frames and 0.93 at 8 Mbit/s. HEVC at 5.5 Mbit/s also reached 0.93, but H.264 plays everywhere,
including social uploads. Two render changes make the frames cheaper to encode without changing the
look. Grain is seeded once per shot and stays static within it; per-frame grain cost about 16% more
bits for nothing visible at this rate. The kick zoom punch is limited to the drops.

## 9. What wasn't available

* The "mesh" and "video scoring" skills mentioned in the brief are not installed in this environment,
  so their roles were rebuilt as scripts. Mesh-like scene building is the procedural three.js scenes.
  Video scoring is the lip-sync loop and the contact-sheet reviews.
* The reference repository `JohnHeibel/PDo` was not accessible from this session.
* Hosts blocked from the container: `*.workers.dev` (worked around through the relay and KV via the
  Cloudflare API), developers.cloudflare.com (model docs read from a sparse clone of
  `cloudflare/cloudflare-docs`), Hugging Face, fbaipublicfiles and download.pytorch.org (UVR models from
  GitHub releases instead).
