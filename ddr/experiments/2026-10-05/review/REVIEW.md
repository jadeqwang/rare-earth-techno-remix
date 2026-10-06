# Rare Earth model edition review

Recommended and released singles: Beginner seed 43, Easy seed 29, Standard seed 29, Heavy seed 43. The first, third and fourth need no model-output repairs. Easy needs one final hold closure: beat 283 to 283.916667, about 0.405 seconds, ending before the source audio endpoint. All original charts remain unchanged.

| Level | Single / double classic meter | Rows | Jumps | Holds | Peak rows/s over 2 s | Single foot speed proxy | Double foot speed proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Beginner | 3 / 3 | 113 | 0 | 10 | 2.5 | 1.60 | 1.60 |
| Easy | 4 / 5 | 175 | 2 | 42 | 2.5 | 2.24 | 2.25 |
| Standard | 6 / 7 | 245 | 12 | 9 | 5.0 | 3.20 | 3.20 |
| Heavy | 9 / 10 | 419 | 1 | 0 | 6.5 | 6.40 | 6.40 |

Speed proxies are panel units per second for a bounded, hold-aware two-foot assignment chosen to minimize consecutive same-foot singleton presses and then travel. They are not difficulty estimates or proof of a comfortable human movement path. They include movement into jumps, which the original validator omitted.

Beginner and Easy press only integer beats. Standard adds half beats. Heavy adds quarter beats. The Easy hold closure is the only irregular release fraction among the selected singles; there are no off-grid press microticks. Heavy Double keeps all five sixteenth-note beat units on one pad. Eighth-note arrows frequently alternate between pads around the seam; that is normal doubles footwork and does not imply the player's body crosses pads on every note.

Easy is deliberately hold-heavy: 32.15% of the song has an active hold, the longest individual hold is 3.60 seconds, and the longest contiguous passage of successive holds is 10.33 seconds. Beginner's longest hold is 5.37 seconds. None of the selected holds is shorter than 150 ms. These are style observations, not export defects.

The model has more rhythmic measure templates than the baseline: 14/15/21/28 versus 3/8/16/18 for singles. Baseline Beginner repeats the [0,2] rhythm in 78.3% of its nonempty measures, with a ten-measure uninterrupted run. Added variety is descriptive; it does not establish better musicality. The coarse spectral-onset proxy is mixed: selected Beginner/Easy have lower note-to-strong-onset agreement than baseline, while Standard/Heavy have slightly higher agreement. All selected charts have fewer rows, so coverage of strong spectral peaks also declines.

Heavy seed 17 was rejected as a selection choice: its conservative left/right-order search fails at beat 68 (31.2654 seconds), while a crossover-permitting assignment has 16 rapid same-foot repeats. Heavy seed 43 has no repairs, no consecutive same-foot presses in the left/right-order model, and no rapid-repeat flags. Easy seed 29 was preferred over seeds 17 and 43 for fewer repairs and lower movement speed. Beginner seed 43 has no jumps. Standard seed 29 permits strict alternating feet in the bounded model.

`compare.py` independently parses SM/SSC using simfile, checks the exact MP3 SHA256, all 71 measured BPM segments and offset, all anchor times, closed holds, active panel demand, panel use, phrase repetition, section density, and bounded foot assignment. `verify_auditor.py` exercises meaningful rejection cases in memory. `verify_release.py` checks all eight expected slots, progression, SM/SSC equivalence, preservation of selected model/Groove notes, unchanged original charts, and ZIP contents. The final machine-readable report is `../release/validation.json`.

No physical pad playtest was performed. The geometric model does not model body facing, equal-x up/down swaps, brackets, airborne idle-foot repositioning, mine avoidance, fatigue, or human enjoyment. GrooveAuthor's official footwork-node review provides additional style evidence, documented in the separate Groove generation audit. Difficulty meters remain provisional.
