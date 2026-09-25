# Outside review of preview 3 (Gemini 3.8 Flash)

The 540p preview 3 (before the final fixes) was down-scaled to 480×270 at 380 kbit/s with mono audio and
sent whole to `google/gemini-3.8-flash` through the Cloudflare catalog. The model watched it with the
audio. What was acted on is listed in `docs/PROCESS.md` §6.

## Prompt

```
You are reviewing a 2-minute music video (techno song about SETI / the search for alien life) as a demanding
K-pop MV director and anime key-animation director. The visuals are an original rotoscoped riso-print / neon style.
Watch and listen to the whole video, then give:
1) Scores 1-10 for: opening hook (first 5 s), lyric legibility & placement, cut rhythm vs. the beat, lip sync of the singer,
   story clarity (Earth searching -> another world -> the Great Filter -> call & response -> contact), visual polish.
2) The 8 most important concrete problems, each with a timestamp (mm:ss) and a specific fix.
3) Any frames that look broken (glitches, unreadable text, text covering faces, empty/black frames).
Be terse and specific. No praise padding.
```

## Response

### 1. Evaluation Scores (Scale 1–10)

* **Opening hook (first 5 s):** 6/10
* **Lyric legibility & placement:** 5/10
* **Cut rhythm vs. the beat:** 6/10
* **Lip sync of the singer:** 4/10
* **Story clarity (SETI narrative arc):** 6/10
* **Visual polish:** 6/10

---

### 2. Priority Issues & Targeted Fixes

1. **00:06 — Lip Sync Timing:** Phoneme shapes lag behind the fast vocal attack on *"yearning"*. Advance mouth keyframes by 2–3 frames to align audio transients.
2. **00:26 — Typography Overlap:** Large text (*"BEATING BLINKING"*) collides with the character's hands and lower torso. Drop baseline coordinates to the lower screen boundary or scale down 20%.
3. **00:32 — Framing Obstruction:** The left-aligned type block crowds the character’s eye line. Anchor text to screen-left margins with proper negative space.
4. **00:50 — Visual Contrast:** Yellow alphanumeric symbols (`LN5B<N`) get lost against the halftone sky and dish lattice. Add a darker drop shadow or outer stroke to separate glyphs.
5. **00:58 — Narrative Pacing:** The Drake Equation parameter screen cuts away before viewers can parse the "weapons/wars" filter concept. Extend screen duration by 12–16 frames or simplify highlighted text.
6. **01:01 — Transition Clashing:** The hard white flash blowout feels unmotivated and breaks the retro riso tone. Replace full white with a stepped 4-frame exposure taper.
7. **01:44 — Emotional Occlusion:** Text overlays directly beside the weeping facial expression, diluting the climactic acting beat. Relocate typography entirely off the face into empty upper-right space.
8. **01:52 — Rotoscope Inconsistency:** Keyframe tracking jitter during the neon dance drop causes strobing line weight around the limbs. Clean vector contours and smooth interpolation curves.

---

### 3. Broken or Problematic Frames

* **00:31–00:34:** Subtitle layers intrude on key facial animation.
* **00:50:** Decoding text string is illegible due to low luminance contrast against background noise.
* **01:00–01:01:** Pure white clipping creates an unintended flash frame appearance.
* **01:18:** Cyan/yellow garbled text layer clips into the alien waterfall silhouette, rendering both unreadable.
