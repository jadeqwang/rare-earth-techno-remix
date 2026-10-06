# Rare Earth — DDR steps

Eight complete charts for the original `audio/Rare_Earth_DDR.mp3`: **Beginner,
Easy, Standard, and Heavy**, each for four-panel single and eight-panel double.
The source recording is included unchanged; it runs 2:07.960 and
gradually accelerates from 129.143 to 135.793 BPM.

[Download the step pack (ZIP)](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/Rare_Earth_DDR_Step_Pack.zip)
and extract it into your game's `Songs`
directory. The ZIP creates `Rare Earth Pack/Rare Earth (Techno Remix)/` beneath
that directory. Reload songs or restart, then select **Rare Earth Pack**.
To replace an earlier copy, replace the existing song folder and reload the
song cache.

The pack targets **both StepMania 3.9 and StepMania 5**: `.sm` for 3.9 and
`.ssc` for 5. Both files contain all eight charts with the same notes and
timing. StepMania 5 also reads `.sm` files. See the official
[file-format list](https://github.com/stepmania/stepmania/wiki/File-Formats)
and [SM format reference](https://github.com/stepmania/stepmania/wiki/sm).

| Chart | Engine difficulty / meter | Step rows | Holds | Jumps |
|---|---:|---:|---:|---:|
| Beginner Single | Beginner / 3 | 132 | 13 | 0 |
| Easy Single | Easy / 4 | 226 | 8 | 4 |
| Standard Single | Medium / 6 | 338 | 7 | 10 |
| Heavy Single | Hard / 9 | 490 | 1 | 15 |
| Beginner Double | Beginner / 3 | 132 | 13 | 0 |
| Easy Double | Easy / 5 | 226 | 8 | 4 |
| Standard Double | Medium / 7 | 278 | 7 | 6 |
| Heavy Double | Hard / 10 | 490 | 1 | 15 |

Standard and Heavy use the format's canonical `Medium` and `Hard` difficulty
tags for compatibility. Chart names use **Standard** and **Heavy**; themes
may display their own labels for the same difficulty slots.

Meters use the classic DDR / StepMania scale of roughly 1–10+, rather than
modern DDR's 1–20 scale. They remain provisional until pad playtesting.
Double is one player moving across two adjacent four-panel pads.

Beginner uses mostly two-beat spacing, simple freezes, and a few quarter-note
accents; Beginner Double travels between pads more slowly. Easy adds sustained
quarter-note patterns and four jumps without introducing eighths. Standard
adds short eighth-note phrases and more accents. Heavy develops those phrases
into eighth streams and brief sixteenth bursts. Heavy Double keeps each rapid
sixteenth burst on one pad, with travel during the surrounding phrases.
All charts start after the short intro, follow the verses, build and drops,
and finish within the original audio.

The [playable song folder](Songs/Rare%20Earth%20Pack/Rare%20Earth%20%28Techno%20Remix%29/)
includes equivalent `.sm` and `.ssc` exports, the MP3, banner, jacket, existing
video artwork as the background, and install instructions.
Full-length previews for [singles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/preview/Rare_Earth_DDR_single_preview.mp4)
and [doubles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/preview/Rare_Earth_DDR_double_preview.mp4) each show the four
difficulty levels together. They render notes directly from the exported SSC
against the audio and are autoplay visualizations, rather than game footage.
Moving arrows and stationary targets share the same sprite center. The
60 fps previews remove taps on the first frame at or after their scheduled
press time (less than 16.7 ms later); holds remain at the target until release.
The [frame review](preview/hit-timing-review.png) and
[encoded-video checks](analysis/preview-hit-check.json) verify the disappearance
at tap and hold-release boundaries in both previews. The checks also compare
the encoded audio against the source near the start, middle, and end to
detect an encoding delay or drift.

The [validation report](analysis/validation.json) records successful strict
parsing of both formats, matching chart data, complete hold pairs, timing
agreement, all panels used, the audio checksum, and a two-foot placement
review. No chart requires three feet or a forced crossover in that placement
model. Double stance and successive foot travel are bounded. No physical pad
playtest or game-engine launch was performed.
The report also checks all four difficulty slots in each mode, increasing
step counts/meters and single-pad sixteenth bursts in Heavy Double.

The [timing report](analysis/timing.json) preserves the source beat grid and
independent audio-transient check. One BPM segment per measure reproduces
the existing instrumental grid to within 0.95 ms; that measures conversion
accuracy against the existing grid, rather than claiming sub-millisecond
accuracy against every sound in the recording. The archived kick onsets have
a median absolute deviation of 3.6 ms and a 95th percentile of 9.62 ms from
that grid; the independent low-band envelope check also retains its larger
outliers for review.

To rebuild locally:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python tools/analyze.py
.venv/bin/python tools/build.py
.venv/bin/python tools/validate.py
.venv/bin/python tools/preview.py --mode single
.venv/bin/python tools/preview.py --mode double
.venv/bin/python tools/package.py
.venv/bin/python tools/verify_preview.py
```

Rhythms and foot placement preferences can be edited in `tools/build.py`.
Source and package song files are separate, so chart edits do not change the
original project audio or video. Pattern placement is recorded in
`analysis/choreography.json` for inspection.

Music: Robot Ninja Apocalypse; written by Jade Q Wang and Charlie van Norman.
Steps and code: Codex. Background: the existing Rare Earth music video art.
File-format references: [StepMania SM documentation](https://github.com/stepmania/stepmania/wiki/sm)
and [StepMania SSC documentation](https://github.com/stepmania/stepmania/wiki/ssc).
