# Rare Earth DDR model comparison — 2026-10-05

The playable **Model Edition** contains four learned ITGPT singles and four
doubles generated with the official GrooveAuthor generation library. The
original song files, pack ZIP, source audio, and measured timing report are
unchanged. This edition installs alongside the original as **Rare Earth Model Pack**.

- **[Download the Model Edition step pack](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/Rare_Earth_Model_Edition_Step_Pack.zip)**
- **[Watch singles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/preview/Rare_Earth_Model_Edition_single_preview.mp4)**
- **[Watch doubles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/preview/Rare_Earth_Model_Edition_double_preview.mp4)**
- **[Install and give pad-test feedback](PAD_REVIEW.md)**
- **[Review discussion and pad-test feedback — PR #6](https://github.com/jadeqwang/rare-earth-techno-remix/pull/6)**
- [Use the music video as the StepMania background](../../../README.md#use-the-music-video-as-the-stepmania-background)
- [Independent chart validation](release/validation.json)
- [Preview timing/audio validation](release/preview-validation.json)

## What changed

ITGPT's released **paper** checkpoints supplied both rhythmic placement and
four-panel arrow choices. Three random symbolic samples were generated for each
conditioned difficulty, using seeds 17, 29, and 43. The selected singles keep the
model arrows rather than replacing them with our original FootFlow planner.

| Level | Selected seed | Original single rows | New single/double rows | New holds | New jumps | Original → new rhythmic measure templates |
|---|---:|---:|---:|---:|---:|---:|
| Beginner | 43 | 132 | 113 | 10 | 0 | 3 → 14 |
| Easy | 29 | 226 | 175 | 42 | 2 | 8 → 15 |
| Standard | 29 | 338 | 245 | 9 | 12 | 16 → 21 |
| Heavy | 43 | 490 | 419 | 0 | 1 | 18 → 28 |

Beginner has sparser phrasing and longer freezes. Easy is intentionally
hold-heavy: holds are active for about 32% of the song, including sequential
freezes in some vocal passages. Standard combines quarters/eighths with more
accent jumps. Heavy emphasizes eighth streams and brief sixteenths, with fewer
jumps than the original. Classic provisional single meters remain 3/4/6/9;
double meters are 3/5/7/10.

These differences are not proof of greater enjoyment. The measured spectral
onset proxy improves for Standard/Heavy and decreases slightly for Beginner/Easy;
it is a coarse audio check, not a musicality score. Lower note counts also reduce
onset coverage. Full-length previews and pad testing should decide which edition
you prefer.

## Selection and repairs

Selection prioritized unchanged audio/timing, valid holds and two-foot demand,
bounded hold-aware foot assignments, few rapid repeated-foot requirements, and
rhythmic variety. Raw model outputs and all sampling/provenance records remain
in `candidates/`; full audits are in `review/`.

Three selected singles required **zero** syntax, chord, or hold repairs.
Easy's last hold begins at beat 283 and lacked a release. One tail closes it at
beat 283.916667, about 25 ms before the original audio ends. The repair is logged
in its candidate JSON and the pack's `MODEL_PROVENANCE.json`.

The official StepManiaChartGenerator/StepManiaLibrary search generated doubles
from those four reviewed singles, retaining the rhythms and hold durations.
Its chosen foot paths use all eight panels with no dropped notes or brackets.
All five Heavy sixteenth-burst beats remain on one pad. Exact configuration,
chosen foot paths, audits, and Linux portability patches are in `groove/`.

## Timing and model integration

The original 2:07.960 MP3 is copied byte-for-byte. All **71 BPM segments** and
the **-0.0611 offset** are retained exactly, preserving the gradual acceleration
from 129.143 to 135.793 BPM.

The stock ITGPT constant-tempo detector is bypassed. Audio windows use measured
beat boundaries, and onset prediction uses groups of at least 50 beats with
their local mean tempo for scalar BPM conditioning. Symbolic audio features are
normalized as in the model's training code. The model loader restores the
original official LayerNorm required by the released paper checkpoint; all
trained tensors load strictly, with no dropped weights.

## Verification and limits

The independent SM/SSC review checks identical note events, effective timing,
all eight difficulty slots, increasing difficulty/count progression, intact hold
pairs, at most two active panel demands, all panels used, and the original audio
hash. Hold-aware geometric foot assignment is an additional conservative review,
with its assumptions explicitly recorded in the report.

Both 1280×720, 60 fps autoplay previews fully decode. Encoded tap-hit and
hold-release probes verify disappearance on the scheduled frame; measured audio
lag is zero samples in windows near 5, 55, and 110 seconds. These are exported-chart
visualizations, not game footage.

**Physical pad playtesting and a game-engine launch have not been performed.**
Meters, bodily comfort, fatigue, and enjoyment remain provisional. The original
pack remains available for direct comparison.

## Reproduce

See [ITGPT setup](itgpt/SETUP.md) and [official footwork generation](groove/README.md)
for pinned source/model revisions, dependency locks, checksums, and setup commands.
From the project root:

```bash
uv venv ddr/.venv --python 3.13.5
uv pip install --python ddr/.venv/bin/python -r ddr/requirements.txt
bash ddr/experiments/2026-10-05/itgpt/setup.sh /tmp/rare-earth-itgpt-repro
ITGPT_REPO=/tmp/rare-earth-itgpt-repro /tmp/rare-earth-itgpt-repro/.venv/bin/python \
  ddr/experiments/2026-10-05/generation/generate_candidates.py --repo /tmp/rare-earth-itgpt-repro
bash ddr/experiments/2026-10-05/groove/bootstrap.sh
python3 ddr/experiments/2026-10-05/groove/run_generator.py \
  ddr/experiments/2026-10-05/selection/model-singles.sm --name selected-model-doubles
ddr/.venv/bin/python ddr/experiments/2026-10-05/generation/build_release.py
```

To check the committed pack without rerunning the models:

```bash
ddr/.venv/bin/python ddr/experiments/2026-10-05/review/verify_auditor.py
ddr/.venv/bin/python ddr/experiments/2026-10-05/review/verify_release.py
```

`generation/render_preview.py` accepts `--simfile`, `--out`, and `--mode single|double`.
`generation/verify_preview.py` audits both release videos. The original manifest
and preservation check are `baseline-manifest.json` and
`release/original-preservation.json`.
