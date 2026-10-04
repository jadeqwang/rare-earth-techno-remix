# Working on this video

Start every session with `bash pipeline/audit/setup.sh` (~3 min). It restores `/tmp/work` from files saved in the repo,
so nothing has to be separated, tracked or aligned again:

* `audio/stems/vocals_kim_vocal_2.flac`: the vocal stem (UVR Kim_Vocal_2); becomes `/tmp/work/vocals.wav`.
* `pipeline/audit/vocal_100hz.npz`: the stem's log RMS, pYIN voicing and pitch at 100 Hz (`vocal.load()`).
* `pipeline/audit/align.json`: PocketSphinx phone alignment of every lyric line (a first guess; the ear decides).
* guides for every take (`/tmp/work/guides`) and the release soundtrack (`/tmp/work/rel_audio.m4a`).

## Fixing a lip-sync note ("at 1:11 the mouth opens early")

1. Look: `python3 /tmp/work/audit/specview.py A B out.png` draws the stem's spectrogram, envelope, pitch and phones for
   seconds A–B. `strips.py SHOT` crops the mouth from every drawing of a shot in the release, with the vocal under it.
   Shot names and song windows are in `pipeline/audit/shots.py` and `render/src/timeline.js`.
2. Edit the shot's spans in `pipeline/sync/lipsheet.json` ([t0, t1, openness 0–1, label, flag]). Flags: `hard` (a lip
   closure that must show), `small` (cap the opening: an "uh"/"ih"), `round` (an "oo"), `hold` / `roundhold` (one mouth
   held through the span, the body still moving).
3. `python3 pipeline/sync/relip.py sdNN --preview /tmp/work/relip` re-mouths that take (plates in `relip.py`'s PLATES);
   check `/tmp/work/relip/sdNN_SHOT.jpg` (before above, after below).
4. `python3 pipeline/extract_selects.py sdNN --force` (the guides are cached by file name, so --force is required).
5. Delete the shot's frames from `/tmp/work/frames_rel` and re-render only those:
   `cd render && node tools/render.mjs --from 0 --to 129.6 --fps 24 --w 1920 --h 1080 --jobs 4 --noenc --resume 1 --framedir /tmp/work/frames_rel`.
   In a fresh session render the whole film once first (~22 min), then only the changed shots.
6. `bash render/tools/encode_release.sh /tmp/work/frames_rel /tmp/work/rel_audio.m4a out/rare_earth_1080p.mp4`
   (soundtrack copied, not re-encoded), check frames pulled from the MP4, commit.

Word onsets used by the type and the edit are in `render/data/audio.json`. The method and its history are in
`docs/PROCESS.md` §3e. Plate fixes (lettering, the back dot) are in `pipeline/plate_fixes/`.
