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
  "( )" in verse 3 is kept as a timed gap, and "Keep" after it is pinned by hand to 61.86 s. "Our" (verse 3,
  line 15) is pinned to 71.28 s, where the note changes, not 71.14 s (§3d).
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

**The design sheets** had the same kind of errors, invented by the image models, and were corrected too
(`pipeline/sheet_fixes/fix_sheets.py` reads each sheet as generated from git and rewrites it). Labels are
painted out and set again in matching lettering, or rebuilt from the sheet's own glyphs where the font can't be
matched; the artwork is untouched except for the array panels:
* Earth sheet: "THE ARRAY · OWENS VALLEY, CA" showed big centre-fed dishes. The panel is now the Allen
  Telescope Array at Hat Creek (42 offset-Gregorian 6.1 m dishes under Lassen Peak; GPT Image 2.5, prompt in
  `pipeline/prompts/world_earth_ata_v1.txt`, source in `design/sources/`). The same picture replaces panel 2
  of the alternate sheet, whose caption now names it. "LAUNCH · VANDENBERG, CA" is now Starbase, TX, where
  Starship and its chopstick tower launch (Vandenberg flies Falcon 9). The alternate sheet was titled
  "Celestial Harmony".
* Echo sheet (`design/world_echo_sheet.jpg`, formerly `world_etz1715b_sheet.jpg`): titled ECHO; the star is an
  orange dwarf 217 ly away, not "KX-209 (coral giant)"; the bright star in the sky study is no longer labelled
  Sol, which from 217 ly is about magnitude 8.9 and invisible to the naked eye.
* DOT sheets (v3 and v2): the 1420 MHz patch is drawn on her left sleeve, not the right, and the Yagi in the
  detail box has 4 elements, not 5.
* Style boards: dates are 2026, not 2024; the readout's target is Echo, not a random real Kepler star
  (KIC 6923187); 6EQUJ5 is a signal, not a target; "a response" is "a signal"; the coordinates were Tokyo
  Tower's and are now the Allen Telescope Array's; the title-card specimens are Chinese and Russian, set in the
  fonts the video uses. On the flat board: two hex codes (#1F2BD1, #9CCBFF), the light-mode caption, a
  "monspace" typo and the printout's gibberish lines.
* Style boards, sample frames: the Earth and light-mode samples were drawn before revision v3 and showed
  DOT with the old hime cut. They are now frames from the finished video, which is v3 throughout (the poster
  at 0:03.08 and the neon close-up at 1:17.54). All 18 DOT takes in the edit are v3 (the `hair` tag in
  `pipeline/seedance_manifest.json`); the only sheets that still show the old cut are the archived earlier
  revisions, `design/dot_character_sheet_v2_hime.jpg` and `design/dot_character_sheet_alt.jpg`.

Three image runs made the array panel (two GPT Image 2.5, one Nano Banana Pro). Nano Banana drew ordinary
centre-fed dishes; the first GPT take has the ATA's offset feeds.

## 3d. Pass 4: release notes (lettering, lip sync, the Great Filter, credits)

The songwriter's notes before release, all acted on. No new generation was needed.

**Lettering.** The takes had invented their own lettering where the character sheet has DOT's: "PACE EARTH"
on the back of her jacket in the pull-back (sd04, 0:13), and "D20 IHz" or "TA20 DIIz" on her sleeve patch in
the pull-back, *caught* (sd05, 0:24) and *caught2* (sd13, 1:37). `pipeline/plate_fixes/fix_lettering.py`
corrects the takes themselves, before the guides are extracted, so the renderer redraws the new lettering as
ink like everything else in the plate:
* The patch is tracked by fitting an ellipse to its dark ring in every frame (`ringtrack.py`: dark on the
  ring, light just inside it and, where hair isn't in the way, just outside it; a weak smoothness prior). The
  rotation of its contents is registered against a reference frame. The old letters are inpainted and
  1420 / MHz is set in Archivo, mapped through the ellipse, so it foreshortens and turns with the patch.
* On the back, the pale-blue dot is fitted as a circle in every frame and the old line measured under it.
  RARE EARTH is set at the old line's length and angle until the camera has pulled back too far for it to
  read (frame 34 of 121); the patch on the far sleeve follows the dot once it is too small to fit.
* Under the beam in sd13 the plate washes the letters out to mid-grey, and the renderer's line art broke
  their thin strokes up. There the lettering is set heavier and in the ring's ink.

The corrected takes are the `*_lettering.mp4` files in `pipeline/base_clips/`.

**Lip sync.** The earlier passes (§3) corrected each take with one lag. That fits one stretch of a shot and
misses the next: in *transit_eye* "not that" was in sync and "far from my own" was not, because the take's
mouth ran on its own clock (it opened in the rest after "far" and shut on "from", about 0.3 s late). Seven
places were flagged, in eight shots. Here the mouth is re-timed separately from the body, the way cel
animation times mouths (`pipeline/sync/remouth.py`):
1. The mouth is tracked (the anime face cascade, or for the extreme close-ups the lower face registered frame
   to frame from a box placed by hand, then centred on the drawn mouth) and its openness measured.
2. The target is the vocal stem: log RMS times the pYIN voicing probability, so sung vowels open the mouth and
   rests, stops and unvoiced consonants close it.
3. For every drawing the renderer shows (on twos, at the shot's lag), a mouth is chosen from the same take by
   dynamic programming: open about as much as the target asks, moving forward the way the take moves, from a
   nearby frame so the head pose matches, lit like the body frame, and not from under a shadow or a hand.
4. That mouth is registered onto the body frame's face (ECC, affine, with the mouths masked out) and blended
   in. The mask covers every mouth pixel of both drawings (non-skin shapes that reach into the mouth box,
   holes filled) and their hull, extends down over the lower lip's shading, and is feathered in skin. The
   transplant takes on the body frame's low-frequency shading (the beam, a shadow). A QA count of the old
   mouth's pixels left in each result is logged; the one drawing it flags (sd13 frame 54) is the new mouth's
   own lip line.

219 of the 263 drawings in these shots got a new mouth: *blink* (sd06, 0:26, "of a star"), *transit_eye*
(sd07, 0:31–0:36), *vision* and *vision2* (sd10, 1:11–1:15), *care2* (sd11, 1:15–1:17), *caught2* (sd13,
1:35), *own* (sd15, 1:44–1:48) and *alone2* (sd16, 1:49), where the take shut her mouth twice during the
held "alone". sd16 turns from behind into profile, and in profile the lips meet the sky and can't be told apart
by colour, so there a fixed ellipse around the mouth is transplanted instead, from mouth positions placed by
hand. The re-timed takes are the `*_sync.mp4` files; sd13's is built on its lettering fix.

Correlation of mouth openness with the vocal target, per drawing as played. This is the metric the chooser
optimises, so it shows the choice worked rather than proving sync on its own; every shot was also checked by
eye, as mouth strips against the words and as rendered frames.

| shot | drawings | r before | r after |
|---|---|---|---|
| blink | 31 | +0.10 | +0.78 |
| transit_eye | 61 | +0.19 | +0.91 |
| vision | 18 | +0.45 | +0.98 |
| vision2 | 17 | +0.19 | +0.87 |
| care2 | 29 | +0.34 | +0.86 |
| caught2 | 35 | +0.22 | +0.53 |
| own | 42 | +0.30 | +0.91 |
| alone2 | 30 | −0.18 | +0.37 |

caught2 gains least: its first second is under the beam's moving shadow, and no mouth is taken from under it.
alone2 is limited by the profile: few mouth drawings to choose from, and a mouth that must stay close to the
body frame's head angle.

*Vision* opened on the end of "transmission". Its last syllable runs on D4 to 71.27 s and "Our" starts a tone
up, 0.14 s after the onset `audio.json` had for it. "Our" is pinned at 71.28 s, so OUR lands on the word, and
the mouth is held nearly shut on the voiced /ən/ before it (the stem alone would have opened it).

**Before they launch or self-destruct.** The line was hard to follow a word at a time, and its "or" is easy
to miss by ear. The whole line now stays on screen from its first word to its last (54.2–57.6 s), each word
lighting up as it is sung (`TypeLayer.line`). The rocket keeps "launch"; on "or" the same launch carries a
different payload. The cut goes to the night side of Earth over the pole, where missile tracks rise between the
silo fields of the Great Plains and central Russia and from submarines at sea, drawn like an early-warning
display. On "self-destruct" the warheads land on the cities of both sides, the globe burns red, its lights
go out, and the Drake equation's **L** follows (`render/src/scenes/war.js`). The HUD's countdown starts at
30:00, about an ICBM's flight time.

**End card.** The credit is two lines: *written by Jade Q Wang and Charlie van Norman (Robot Ninja
Apocalypse) for the SETI crowdfunding campaign in 2011*, then *video drawn in javascript · keep looking*.

**Delivery.** The whole film was rendered again at 1080p and reviewed as contact sheets (every 0.5 s, every
0.25 s through the changed shots) and full-size crops of each fix. The picture was encoded as in §8; the
soundtrack is the previous release's AAC stream, copied, and its packets are identical.

## 3e. Pass 5: lip sync, drawing by drawing

Before launch, a note asked for the whole video to be checked for DOT's mouth moving out of time with the vocal, or
the wrong way. The release was audited end to end: every drawing of all 20 shots of DOT, cropped from the released
video at the mouth and laid out against the vocal stem's envelope, its spectrogram and forced-aligned phones, one cell
per drawing as played (on twos, at each shot's lag). What was wrong:

* **Open through rests and breaths**: after "there" in *yearning* (0:08.5), after "not" and "that" in *transit_eye*,
  the breath before "science" in *vision* (1:12.1), after "care" in *care2* (1:17.5), after "caught" in *caught2*
  (1:37.1), after "that" in *own* (1:44.3).
* **Late or shut on the word**: "far" (0:33.0) and the whole held "own" (0:34.8–35.8, a closed smile) in
  *transit_eye*; "my" in *own* (1:45.9, shut for 0.3 s); "Do", "you" and "care" in *care2* (clenched teeth); "I've"
  in *caught* and *caught2*; "bea-" in *blink*; "star" in *blinkdance*; the first syllable of "there" in *listen*.
* **Lip closures missed**: the "f" and "m" of "from my" in *transit_eye* and *own*, the "b"s of "beating blinking",
  the "v" of "a vision", the "th" of "think".
* **Two mouths at once**: in *transit_eye* at 0:35.5 the transplant of §3d had put an open mouth over the take's
  closed smile and left the smile showing beside it. That pass replaced 219 of 263 drawings, the ones the take had got
  right as well as the wrong ones.

The instrumental final drop (*dance2*, *dance3*, *stillhere*) was checked too: her mouth stays shut there. *alone*
(tiny in frame until the held "alone"), *alone2* (from behind, then an open "alone"), the poster and the pull-back
(seen from behind) have nothing to fix.

**Tools.** The Cloudflare catalog was searched for a lip-sync model (every schema in the unified catalog's 164 models,
and Workers AI): none re-times a mouth in existing footage. The video models that take audio (Seedance 2.5 with
reference audio, Gemini Omni, MiniMax H3, Pruna P-Video) generate the whole shot again: a new performance, without the
lettering fixes, and no surer of sync than the takes (Seedance made them, and its sync is what drifted). The open
lip-sync models (Wav2Lip, LatentSync, MuseTalk) are trained on photographed faces and draw the mouth region at low
resolution (Wav2Lip at 96 px), and any generated mouth would be in a different hand from the take's. A mouth borrowed
from another frame of the same take is already drawn in its hand, so that is what this pass uses; LivePortrait (its
ONNX export, from facefusion's model assets on GitHub) reads the anime faces well enough to measure head pose and to
make small edits.

**Method** (`pipeline/sync/relip.py`), from the takes as generated, the lettering fixes kept:

1. An exposure sheet (`pipeline/sync/lipsheet.json`) gives, for every sung syllable, how open the mouth should be,
   read off spectrogram views of the stem with PocketSphinx's forced-aligned phones as a first guess. Lip closures (m,
   b, p, v, f) are marked to show even when shorter than a drawing, and each drawing is timed a frame ahead of the
   sound, as cel animation times mouths. The sheet lines up with the stem's envelope within 0.04 s in every shot but
   *vision*, where the voiced n that ends "transmission" is held nearly shut on purpose (§3d).
2. Every drawing's own mouth is found and measured: the gap between the lips for the face's size, against how wide
   that take opens it when it sings out.
3. A drawing is changed only if it reads as wrong: open through a rest or a closure, open wide on a consonant, shut
   on a sung vowel. Anything in between is how the take chose to sing it.
4. A wrong drawing gets a mouth from another frame of the same take, chosen by dynamic programming over each run of
   wrong drawings: open as far as the sheet asks, from a head turned within 10° (LivePortrait's pose estimate) and at
   the same scale, near in time and lit alike, moving forward as the take moves. The donor frame is registered onto
   the face (ECC, affine, both mouths masked out) and its mouth cloned in (Poisson) over both mouths and a margin of
   skin, so nothing of the old mouth is left; hands and hair are never taken in. Where registration can't follow the
   head, LivePortrait draws the donor's face in this frame's pose; where no frame has the mouth needed, it opens or
   closes the drawing's own lips.
5. Every result is measured again and must say what the sheet asks, still look like the donor's mouth, leave the face
   around it unchanged, and be drawn in dark, crisp line. If nothing passes, the drawing stays as the take drew it.

90 of the 355 drawings in these shots were changed: 89 with a mouth from the same take, one redrawn by LivePortrait.
Two had no clean fix and were left: the first drawing of *listen2* as her face turns into view on the held "me"
(1:23.2), and one open drawing on the "k" of "think" in *caught2* (1:36.2), which needs no closed lips. Every change
was checked by eye on QA sheets (before above, after below, from `relip.py --preview DIR`), the doubtful ones at full
size, and all of them again as rendered in the release.

As played, re-measured from the takes as written (`pipeline/sync/lipcheck.py`; *wrong* counts drawings that read as
wrong, *r* is the correlation of openness with the sheet):

| shot | drawings | changed | wrong before | wrong after | r before | r after |
|---|---|---|---|---|---|---|
| yearning | 39 | 7 | 7 | 0 | +0.45 | +0.82 |
| listen | 23 | 1 | 1 | 0 | +0.76 | +0.86 |
| caught | 20 | 3 | 3 | 2 | −0.04 | +0.45 |
| blink | 31 | 5 | 6 | 2 | +0.09 | +0.59 |
| transit_eye | 61 | 28 | 10 | 0 | +0.58 | +0.86 |
| keep_yagi | 10 | 0 | 0 | 0 | — | — |
| vision | 18 | 4 | 5 | 0 | +0.57 | +0.89 |
| vision2 | 17 | 4 | 4 | 0 | −0.01 | +0.79 |
| care2 | 29 | 10 | 12 | 0 | −0.03 | +0.82 |
| listen2 | 17 | 0 | 1 | 1 | −0.06 | −0.06 |
| caught2 | 35 | 13 | 11 | 1 | −0.17 | +0.57 |
| blinkdance | 13 | 3 | 3 | 0 | +0.58 | +0.85 |
| own | 42 | 12 | 5 | 0 | +0.64 | +0.92 |
| **all** | **355** | **90** | **68** | **6** | | |

The four left in *caught* and *blink* sit on the threshold: a small mouth on "I", teeth together a frame before
"I've", and teeth together on the "-ng" that ends "blinking", which needs no open lips. *keep_yagi* shows her face
only for the held "looking", and it was right. As rendered, two changes read less than in the takes: the "bea-"
opened by LivePortrait in *blink* (0:25.75) is small and pale enough inside that the ink draws it as a line, and in
*blinkdance* her face is small. The re-lipped takes are the `*_lips.mp4` files in `pipeline/base_clips/`; they
replace the `*_sync.mp4` takes of §3d except for *alone2* (sd16), which keeps its profile mouths. The storyboard's
1:16.8 tile is rendered again, since that drawing's mouth changed (the other tiles are unchanged).

**Notes on the lip-sync cut, acted on.**
* *of a star* (0:27.7): the last two drawings of *blink* opened wide, an "ah" that read as "star" before the word. "of a"
  is a small "uh"; the sheet now caps those spans (`small`) and they get small mouths from the same take.
* *my own* (0:34.7): the voice breaks from "my" into "own" at 34.66 s, not at 34.85 s where the phones had it, so the
  round "o" came about four frames late. "own" now starts there and asks for a rounded mouth (`round`).
* *our planet waits* (1:07): se03 drew only a faint teal ring on the back of her jacket, and the ink redraw lost it in the
  jacket's night shading, so the jacket didn't match the opening shot's. `pipeline/plate_fixes/fix_backdot.py` paints a
  solid dot over the ring, tracked by hand as the camera pulls back, with her hair left in front (`se03_..._dot.mp4`). Its
  colour is the drawn ring's own blue, the sheet's pale blue as it looks in that night light; a lighter fill looked lit
  by a light of its own.
* *Our science* (1:11): the take's mouth was open before "Our". "Our" starts where the note rises from the D4 of
  "-sion", about 71.31 s; the mouth is now shut until the drawing at 71.33 s, the last shut drawing held for two frames
  where no clean closed mouth could be made (`relip.py` holds the previous drawing then, as cel animation does).
  (The QA ink check compares a borrowed mouth's line with the donor's, not with the open mouth it replaces.)
* *do you still* (1:15.9): "do" ends at 75.84 s and "you" starts at 76.03 s, not at the phones' 75.99/76.02 with no
  breath between. The mouth now shuts in the breath and opens on "you" instead of a drawing later.
* *Our* (1:11) again: the take sang all of "our" in half a second and shut by 71.9 s, while the held E4 fades to 72.15 s,
  so the mouth finished before the voice did. The sheet now holds "-r" open to 72.12 s.
* *vision* (1:14): the take held a wide "ah" through "vi-"; the sheet marks it `small` (an "ih", teeth near together)
  from the release of the "v", and it gets that mouth from the same take.
* *you* (1:16): the drawing that comes on just before the voice (75.96 s) is now a rounded "oo" (`round`), held through
  the vowel, instead of the take's open mouth with "you" arriving a drawing later.
* *Our* (1:11), properly this time: the vocal stem's formants show that 71.3–71.9 s is still "transmission", its "-sion"
  rising from D4 to an open E4 and ending on a held "n" (low F1, 71.58–71.9 s); "Our" is the short, quiet syllable at
  71.92–72.16 s, just before the "s" of "science" (Whisper, on the stem, also puts it at 72.0 s). The mouth now stays
  small, then shut on the "n", and opens on "Our"; `render/data/audio.json` moves the word (and the OUR title) from
  71.28 s to 71.92 s. The earlier pin to 71.28 s (§3d) was the note change inside "-sion".
* *our planet waits* (1:08–1:09): RARE EARTH is set on the back under the dot, as on the sheet and in the pull-back, in
  the gap above the crop top's hem, and heavier than in the pull-back so the ink redraw keeps it at this size
  (`fix_backdot.py`).

**Re-shoots for the last three spots.** Retiming the old takes' mouths kept coming close without landing at *blink*
(0:25), *vision* (1:11) and *care2* (1:15). Those three shots were re-shot with Seedance 2.5 the way the alt-pop cut was
made (`pipeline/reshoot.py`): image-to-video from the shot's own first drawing, with the vocal cut to begin exactly at the
shot's first frame as the reference audio, so the new take needs no lag and no mouth retiming. 15 takes (about $14),
scored against the vocal and checked by eye; the chosen takes are `pipeline/base_clips/reshoot/` (`sd06r`, `sd10r`,
`sd11r` in `selects.json`). Also: *dot2* (1:31) is back to the field of petal dishes turning to our Sun (Kenton's note),
and Echo's night city at 1:57 glows fuchsia, like every other Echo shot.

## 3f. Pass 6: the build into drop 1 (0:51–0:55)

A note that the stretch at 0:51 was abstract and less engaging than the rest. Under it the kick and bass drop out
(47.5–52.5 s) and an eighth-note snare roll builds into the drop.

**The tower (0:51.16–0:52.96).** It was the one flat procedural shot of Echo, between two rotoscoped plates, locked off,
and its only motion (the ring lights) was keyed to kicks, of which there are none here. It is now a new plate, se11
(Seedance 2.5, take bce14cb91c, 2.9–4.7 s; references: the world sheet's tower and a frame of se10 so the design
carries over): low and close, the camera cranes up the tower as pulses of light climb it, the halo ring flares on the
51.79 snare and the tip starts to glow. It charges and does not fire: the beam is saved for se10 at 1:47; the other two
takes started firing one. Over it, `ECHO · SIGNAL TOWER` and a charge readout that steps on each snare to 100% at the
cut, and *are you there* in Echo's glyphs, carried over from the shot before it (the lone cliff dish at 0:50). Three runs, about $3.50. `gen.py` now
also takes an API token from `CLOUDFLARE_API_TOKEN` when it runs outside the original sandbox.

**The flips (0:52.96–0:54.76).** One beat each, Earth's array and Echo's field. Each snap finished in the first eighth
of a second, under the cut and its flash, so the rest of every beat was a still; the targets were random and Echo's
high camera made its petal dishes read as wireframe cones. With choreography `converse` (`array.js`, `petals.js`) the
two worlds take turns: Earth's dishes aim screen right and Echo's screen left, so each cut reads as one looking at the
other; each shot starts where the other world left off, dips, and snaps on the offbeat, one step higher, so they rise
together into the title; Echo blooms as it rises, seen from above the heads; both cameras push in on the last two beats.

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
