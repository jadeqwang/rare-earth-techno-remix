# Kenton's Rare Earth pad review

**[Download the Model Edition step pack (ZIP)](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/Rare_Earth_Model_Edition_Step_Pack.zip)**
· [Watch singles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/preview/Rare_Earth_Model_Edition_single_preview.mp4)
· [Watch doubles](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/experiments/2026-10-05/release/preview/Rare_Earth_Model_Edition_double_preview.mp4)

## Install

1. Extract the ZIP into StepMania's `Songs` directory. The resulting chart path
   should be `Songs/Rare Earth Model Pack/Rare Earth (Techno Remix - Model Edition)/`.
   If the unzip tool creates an extra folder named after the ZIP, move
   `Rare Earth Model Pack` directly into `Songs`.
2. Reload songs or restart the game. Select **Rare Earth Model Pack**, then
   **Rare Earth (Techno Remix - Model Edition)**.
3. Choose Single for one four-panel pad, or Double for one player using two
   adjacent pads. Each mode includes Beginner, Easy, Standard, and Heavy.
   Some themes call Standard **Medium** and Heavy **Hard**.

The `.sm` file targets StepMania 3.9 and the `.ssc` file targets StepMania 5;
both contain the same eight charts. The original MP3 runs 2:07.960.

For comparison, [download the original pack](https://github.com/jadeqwang/rare-earth-techno-remix/raw/refs/heads/main/ddr/Rare_Earth_DDR_Step_Pack.zip)
and install it as **Rare Earth Pack** alongside this edition. To use the music
video during gameplay, follow the [README background instructions](../../../README.md#use-the-music-video-as-the-stepmania-background).

## What to check on pads

| Level | Single meter | Double meter | Particular passages to review |
|---|---:|---:|---|
| Beginner | 3 | 3 | Sparse phrasing, freezes up to 5.37 seconds, and double pad transitions. |
| Easy | 4 | 5 | Hold-heavy phrasing: 42 holds, active through about 32% of the song. Does it feel natural and distinct from Beginner? |
| Standard | 6 | 7 | Eighth-note phrases, accent jumps, and double transitions. |
| Heavy | 9 | 10 | Eighth streams, short sixteenth bursts, and double travel around fast phrases. |

Meters use the classic DDR scale and remain provisional. Please check that all
eight charts load, that hits follow the music near the start, middle, and end,
and that holds release when expected. Physical feedback should cover foot flow,
awkward repeated-foot moves, turns, balance during holds, double travel, fatigue,
and whether patterns fit the song. Comparing the same level in both editions
will help decide which charts to keep or revise.

## Send review notes

Leave feedback on [GitHub pull request #6](https://github.com/jadeqwang/rare-earth-techno-remix/pull/6),
or share notes with Jade. For each issue, include the edition, mode, difficulty,
song timestamp or beat, what feels awkward, and the change you suggest.
Also include the StepMania version/theme, pad setup, playback rate, use of a bar,
and whether you adjusted machine sync or song sync. A recording is helpful if
you already have one.

Example: `Model Edition / Double / Heavy / 0:31 — the transition after this
phrase needs a repeated right-foot step; suggest keeping it on the left pad.`
This is an example reporting format, not an observed defect.

Software checks passed for parsing, matching SM/SSC notes and timing, complete
holds, at most two active panel demands, bounded foot assignments, audio
preservation, ZIP contents, and preview timing. **No in-game launch or physical
pad test has been performed yet.** See the [generation comparison](README.md)
and [chart review](review/REVIEW.md) for evidence and limitations.
