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
  face crops at every sung word onset for candidate lags, as the visual check.
* **Two metrics, one method.** Profiles, push-ins and hands at the face defeat the cascade, so
  `mouth_color.py` adds a second, independent openness measure: the largest skin blob is taken as the
  face, and the dark-red mouth-interior pixels in its lower half are counted. `lag_curve.py` measures
  both metrics exactly the way the renderer plays a take. For every lag it resamples the openness curve
  at `t − start + lag` for each song time in the window and correlates that with the vocal envelope. A
  lag is trusted when both curves peak together. The first scorer (`score.py`) slid the curves inside
  the window instead. That drops edge samples, and on short rhythmic windows it can pick the wrong one
  of two periodic peaks: sd06 v3 read −0.33 s there and +0.29 s here, where both metrics agree.

Current selects (character revision v3; *r* = correlation with the vocal envelope at the applied lag /
at zero lag):

| shot | lyric | take | lag | face r | colour r |
|---|---|---|---|---|---|
| sd02 | You're yearning to see the life out there | c8b3647c99 | −0.083 s | 0.78 / 0.32 | profile, n/a |
| sd03 | Are you still there | 17fad81acf | −0.292 s | 0.72 / −0.32 | 0.13 / −0.28 |
| sd06 | The beating blinking of a star | a30f474b95 | +0.292 s | 0.44 / 0.03 | 0.38 / 0.07 |
| sd07 | not that far from my own | 9681e0518b | 0 | ECU, n/a | 0.52 / 0.52 |
| sd09 | Keep on looking | c6c9c8b95f | −0.083 s | 0.82 / 0.18 | hand at face, n/a |
| sd10 | Our science has a vision | 1368eb119a | +0.042 s | 0.49 / 0.41 | 0.40 / 0.31 |
| sd11 | Do you still care | 03ce0c9203 | +0.125 s | 0.41 / 0.09 | 0.46 / 0.16 |
| sd12 | Are you still there (V4) | 58e3680064 | −0.250 s | 0.69 / −0.70 | 0.60 / −0.61 |
| sd13 | Your signal here I think I've caught | d1fa06cb74 | +0.208 s | 0.22 / −0.08 | 0.32 / −0.18 |
| sd14 | The beating blinking of a star (V5) | bd2b906427 | −0.146 s | 0.68 / 0.03 | 0.75 / 0.01 |
| sd15 | far from my own (ECU) | afca32f85b | −0.125 s | 0.36 / −0.08 | 0.40 / −0.09 |

  sd05 (hands over the face), sd08 (tiny in frame until the held "alone") and sd16 (seen from behind)
  play at zero lag; neither metric is meaningful there. The v3 takes needed larger corrections than the
  v2 batch, which stayed within ±0.17 s. Without them sd12 would have played visibly out of sync
  (r = −0.70 at zero lag). A few corrections run a plate past its end; for sd13, the cut to the next shot
  moved 0.3 s earlier rather than freezing the last drawings.

### Lip-sync pass 2: scoring what is actually played

A later audit checked sync end to end:

* **Audio.** The soundtrack of the final MP4, the source MP3 and the vocal stem cross-correlate at
  exactly 0 ms, so any error has to come from the footage.
* **Twos.** DOT is drawn on twos: a drawing is held for two frames. That makes the displayed plate up to
  one frame late and quantises the lag. Lags tuned on single frames turned out to cost real sync once
  held. For example, "of a star" scored 0.45 as played against 0.70 on ones.
  `render/src/timeline.js` now uses lags tuned *as played*, on twos, per shot. The scorer lives in the
  session tools, and `lag_curve.py` is the per-clip version. vision2 overrides its clip's lag, because
  the same take peaks three frames later in that window.
* **Frame rounding.** Lags are exact multiples of 1/24 s. The renderer's frame lookup now tolerates
  1e-3 of a frame, because a lag stored as −0.291667 had landed one frame away from −7/24 whenever a
  plate started exactly on a frame.
* **Re-rolls.** The three weakest shots were re-rolled, four new takes each, and each shot now uses its
  best take:
  * caught2: 935323d481, r = 0.57 / 0.56, up from 0.24 / 0.04. This take is framed wider, so the
    plate is pushed in 1.35×.
  * own: 3eb552a647, colour r = 0.63.
  * caught: ba8af2ae02, face 0.22 / colour 0.59, the only lag where both metrics are positive.

As played now (face r / colour r; "—" = metric not usable for that framing):

| shot | r | shot | r |
|---|---|---|---|
| yearning | 0.73 / — | vision2 | 0.39 / 0.33 |
| listen | 0.73 / — | care2 | 0.30 / 0.41 |
| caught | 0.22 / 0.59 | listen2 | 0.67 / 0.54 |
| blink | 0.51 / 0.42 | caught2 | 0.57 / 0.56 |
| transit_eye | — / 0.53 | blinkdance | 0.87 / 0.85 |
| keep_yagi | 0.79 / — | own | — / 0.63 |
| vision | 0.47 / 0.40 | | |

alone (DOT tiny in frame until the held "alone") and alone2 (seen from behind) can't be measured.
The table in §3 records the first v3 pass.

## 3b. Character revision v3 (new hairstyle)

After v1 was delivered, the songwriter asked for DOT to get a different hairstyle, from a reference
photo. The photo itself was not sent to any model. The hairstyle was written into a text-only edit of the
canonical sheet (`pipeline/prompts/dot_sheet_v3_hair.txt`): long, straight black hair with a centre part,
long curtain bangs framing the face, and long layered ends past the shoulders. It replaces the hime cut
and drops the blue under-layer. Everything else on the sheet was kept.

GPT Image 2.5 made two edits of the v2 sheet and Nano Banana Pro one. The first GPT edit became
`design/dot_character_sheet.jpg`. The Nano Banana edit ignored the instruction and kept the hime cut.
The v2 sheet is kept as `design/dot_character_sheet_v2_hime.jpg`.

All 18 DOT shots were regenerated with the new sheet as the image reference: 56 Seedance takes, with
takes tagged by revision in the manifest. The picks were made on contact sheets of each shot's used
window and verified with the lip-sync loop above. Two prompts were changed after the first round:
* sd02: the three-quarter view came back as a pure profile, so the prompt now asks for the face to be
  visible.
* sd11: the extreme close-up looked angry, so it was reframed and the prompt asks for a pleading look.

Some new takes also frame DOT differently, and type was moved to match:
* the poster's star flare now follows the star in the new plate;
* "ALONE?" moved below DOT, because the new sd08 cranes in until her head fills the top third;
* *far from my own* moved onto her hair;
* the listen plate is pushed in so her cupped hand clears the lyric.

## 3c. Pass 3: Echo (fact check and new views of the other world)

A fact check before release, with an eye to what people will screenshot, plus a note from a viewer
that the other world kept showing the same shots.

**The name.** The other world was called "ETZ-1715 b". That reads like a real catalogue designation,
and it isn't one: 1,715 is the number of stars counted by Kaltenegger & Faherty (Nature, 2021). It is
now **Echo**. The science stays on screen as a caption during the warp: *1,715 stars within 326 ly could
have seen Earth cross the Sun in the last 5,000 years*, with the citation.

**The timing.** Echo is 217 light-years away. Our radio has only travelled about 100 light-years (in
the same paper, 75 of the stars are close enough for it to have reached them), so Echo cannot have heard
us, and a "reply" with a 434-year round trip could not reach DOT in her lifetime. The last message is
now Echo's **beacon**, sent in 1809 after they saw our transit and landing now:
* the HUD under *STILL HERE.* reads `BEACON · ORIGIN ECHO · SENT 1809 · 217 YEARS IN FLIGHT`;
* the contact shot no longer claims `SIGNAL LOCK · BOTH WAYS`. It reads `SOL III · OURS ARRIVES 2243`,
  `SIGNAL LOCK`, `THEIRS SENT 1809 · ECHO`, consistent with the journey counter (launched 2026, arrives
  2243).

Also corrected: Voyager 1 was 40.47 AU (6,055 million km) from Earth when it took the Pale Blue Dot, so
the HUD reads 6.1 × 10⁹ km, not 6.4. And the Allen Telescope Array did not come back on crowdfunding alone:
SETIStars raised over $200K from more than 2,000 donors, and the US Air Force paid to use the array for
tracking space debris. The margin note in the funding window now says both.

**No view of Echo plays twice.** Before this pass the planet-from-space shot played four times, and the
se04 city, the se05 listening field and the signal tower twice each. Five new environment plates were
generated (Seedance 2.5, 720p, 5 s, no audio), with the panels of the world sheet as references and an
environment style line instead of the DOT one that the first plates had appended by mistake:

| shot | time | was | now |
|---|---|---|---|
| yearning2 | 77.66–79.61 | se04 city again | se06 take 8321aeff0a, 2.9–4.9 s: tilt from the sea to the ring and two moons |
| lifeoutthere | 79.61–81.00 | planet from space | se07 take a2174d9ef8, 1.5–2.9 s: up the space elevator, climbers rising past the ring |
| dot2 | 90.47–93.59 | se05 field again | se08 take c696ce0051, mirrored: a lone petal dish on a cliff turns toward the Sun marker |
| blinkecho | 98.80–99.76 | planet from space | procedural: the night side from low orbit, cities linked like a constellation |
| alone2 (right) | 107.79–112.02 | the tower again | se10 take 7ab900a4f5: the tower far across the clouds fires its beam up |
| echoblink | 116.47–117.35 | planet from space | se09 take ff0c2e46ca, 1.2–2.1 s: a canyon city at night, its terraces lighting up in a wave |
| science (right) | 72.54–74.00 | petal field, low angle | the same procedural field from high above |
| searching2 (right) | 81.00–82.20 | petal field, low angle | se08 take 490a672d82, 2.0–3.2 s: the cliff dish opening, pushed in |

The split screens had shown the same low-angle petal field three times; the dance break keeps it (both
worlds dancing is the point there), the other two now differ. The procedural petal field stays as the
other world's counterpart to Earth's dish array, with a different camera and choreography each time.

The night side reuses the planet shader with a new composition (the same framing as Earth's blinking
night side just before it) and a new city layer for close views: one city per lon/lat cell on land,
linked to its neighbours, plus a finer scatter of towns (`cityNet` in `render/src/scenes/etz.js`).

Generation went through the relay's cron queue (`run_seedance.py submit --cron`), which needs no webhook
secret: the Worker runs the job itself and mirrors the video into KV. Thirteen runs, 65 s of video, about
$15. The first two se09 takes used the dusk vista as reference and came back as dusk copies of it, so
se09 was re-rolled text-only. The released soundtrack is unchanged: its AAC stream is copied into the new
encode rather than re-encoded.

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
4. **Outside review.** Gemini 3.8 Flash watched the 540p preview with its audio and scored it
   (`docs/reviews/gemini_preview3.md`). The actionable findings were acted on:
   * yearning lip sync measured 1–2 frames late (fixed, see §3);
   * line boil strobing under bloom in the neon dance shots (light-mode boil halved);
   * type crowding the eye in *not that far* and the colliding BEATING / BLINKING (both resized).

   Its other findings were already fixed in the newer build (the words beside the ECU face, the decode
   over the waterfall), or were deliberate: the white impact frame on the drop after the blank.
5. **Final 1080p:** reviewed the same way before encoding. Changed shots were re-rendered in place from
   the shot table (`render/tools/shots.mjs`, then `render.mjs --resume`).

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
