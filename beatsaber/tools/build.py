"""Author Standard Beat Saber charts against the original DDR soundtrack."""
from pathlib import Path
import bisect
import hashlib
import json
import shutil
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
SONG = ROOT / "CustomLevels/Rare Earth (Techno Remix)"
ANALYSIS = ROOT / "analysis"
TIMING = json.loads((PROJECT / "ddr/analysis/timing.json").read_text())
SOURCE = PROJECT / TIMING["source"]
BPMS = TIMING["bpms"]
BPM = BPMS[0]["bpm"]
PHASE = TIMING["beat_zero_s"] * BPM / 60
CHARTS = [("Normal", 3, 11, .25), ("Hard", 5, 14, .5), ("Expert", 7, 16, .5)]
ANCHORS = [TIMING["beat_zero_s"]]
for a, b in zip(BPMS, BPMS[1:]):
    ANCHORS.append(ANCHORS[-1] + (b["beat"] - a["beat"]) * 60 / a["bpm"])


def source_time(beat):
    i = bisect.bisect_right([s["beat"] for s in BPMS], beat) - 1
    return ANCHORS[i] + (beat - BPMS[i]["beat"]) * 60 / BPMS[i]["bpm"]


def export_beat(beat):
    # Encode the 61.1 ms lead-in in object positions, avoiding deprecated offsets.
    return round(beat + PHASE, 9)


def section_at(beat):
    t = source_time(beat)
    return next(s["id"] for s in TIMING["sections"] if s["t"] <= t < s["end"])


def rhythm(level, measure):
    """Purposeful phrase rhythms; each tier gets its own two-hand arrangement."""
    if measure < 2:
        return []
    if measure == 70:
        return [0]
    section = section_at(4 * measure)
    if section == "outro":
        return [0, 2]
    if level == "Normal":
        if section == "build":
            return [0, 2] if measure < 26 else [0, 1, 2, 3]
        if section in ("v3", "v4", "v5", "final"):
            return [0, 1, 2, 3] if measure % 4 != 3 else [0, 2, 3]
        return [[0, 2], [0, 1, 2], [0, 2, 3], [0, 2]][measure % 4]
    if level == "Hard":
        if section == "build":
            return [0, 1, 2, 3] if measure < 26 else [0, 1, 2, 2.5, 3, 3.5]
        if section in ("v3", "v4", "v5", "final"):
            return [[0, 1, 1.5, 2, 3, 3.5], [0, .5, 1, 2, 2.5, 3],
                    [0, 1, 2, 2.5, 3], [0, 1, 2, 3, 3.5]][measure % 4]
        return [[0, 1, 2, 3], [0, 1, 2, 2.5, 3],
                [0, .5, 1, 2, 3], [0, 1, 2, 3]][measure % 4]
    if section == "build":
        return [0, .5, 1, 2, 2.5, 3] if measure < 26 else [i / 2 for i in range(8)]
    if section in ("v3", "v4", "v5", "final"):
        return [i / 2 for i in range(8)] if measure % 4 != 3 else [0, .5, 1, 2, 2.5, 3, 3.5]
    return [[0, .5, 1, 2, 2.5, 3], [0, 1, 1.5, 2, 3, 3.5],
            [0, .5, 1, 1.5, 2, 3, 3.5], [0, 1, 2, 2.5, 3]][measure % 4]


class SaberFlow:
    def __init__(self, level):
        self.level = level
        self.counts = [0, 0]
        self.next_hand = 0
        self.last = [-100, -100]
        self.notes = []
        self.records = []

    def hit(self, beat, hand):
        i = self.counts[hand]
        # Up/down alternates for each hand even through simultaneous accents.
        # Diagonal transitions are 135 or 180 degrees; hands stay on their half.
        if self.level == "Normal":
            direction = [1, 0][i % 2]
        else:
            directions = [1, 0, 6, 5, 1, 0, 7, 4]
            direction = directions[i % len(directions)]
            if hand == 1:
                direction = {4: 5, 5: 4, 6: 7, 7: 6}.get(direction, direction)
        outer = 0 if hand == 0 else 3
        inner = 1 if hand == 0 else 2
        # Inner blocks stay below eye level; upper/middle blocks stay outside.
        down = direction in (1, 6, 7)
        y = (1 if self.level == "Normal" else 2) if down else 0
        # Inward diagonals remain in outer columns, so simultaneous swings
        # cannot converge between the player's hands.
        x = inner if direction == 0 and i % 4 == 1 else outer
        self.notes.append(dict(b=export_beat(beat), x=x, y=y, c=hand, d=direction, a=0))
        self.records.append(dict(source_beat=beat, time_s=round(source_time(beat), 9),
                                 hand=hand, direction=direction, x=x, y=y,
                                 section=section_at(beat)))
        self.counts[hand] += 1
        self.last[hand] = beat

    def single(self, beat):
        hand = self.next_hand
        self.hit(beat, hand)
        self.next_hand = 1 - hand

    def double(self, beat):
        self.hit(beat, 0)
        self.hit(beat, 1)


def lightshow():
    events = [dict(b=0, et=et, i=1, f=.35) for et in range(5)]
    for beat in range(8, 283):
        section = section_at(beat)
        dense = section in ("v3", "v4", "v5", "final")
        red = (beat // 4) % 2 == 0
        if beat % 2 == 0 or dense:
            for et in (0, 4):
                events.append(dict(b=export_beat(beat), et=et,
                                   i=7 if red else 3, f=1.0 if dense else .7))
        if beat % 4 == 0:
            for et in (1, 2, 3):
                events.append(dict(b=export_beat(beat), et=et, i=6 if red else 2, f=.8))
        if beat % 16 == 0:
            events.append(dict(b=export_beat(beat), et=8, i=1 if dense else 0, f=1.0))
            events.append(dict(b=export_beat(beat), et=9, i=1 if dense else 0, f=1.0))
    for et in range(5):
        events.append(dict(b=export_beat(283), et=et, i=0, f=0.0))
    return sorted(events, key=lambda n: (n["b"], n["et"]))


def main():
    SONG.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if sha != TIMING["source_sha256"]:
        raise ValueError("DDR audio no longer matches the checked timing grid")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(SOURCE), "-map", "0:a:0", "-vn", "-c:a", "libvorbis", "-q:a", "6",
                    "-ar", "44100", "-map_metadata", "-1", str(SONG / "song.ogg")], check=True)
    shutil.copyfile(PROJECT / "ddr/Songs/Rare Earth Pack/Rare Earth (Techno Remix)/jacket.png",
                    SONG / "cover.png")
    bpm_events = [dict(b=0.0, m=BPM)] + [dict(b=export_beat(s["beat"]), m=s["bpm"]) for s in BPMS[1:]]
    charts = []
    choreo = {}
    for level, rank, njs, jump_offset in CHARTS:
        flow = SaberFlow(level)
        accents = ({30, 42, 62, 68} if level == "Normal" else
                   {30, 34, 42, 46, 50, 54, 62, 66, 68} if level == "Hard" else
                   {10, 18, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62, 64, 66, 68})
        for measure in range(71):
            for r in rhythm(level, measure):
                beat = measure * 4 + r
                if (measure in accents and r == 0) or measure == 70:
                    flow.double(beat)
                else:
                    flow.single(beat)
        chart = dict(version="3.3.0", bpmEvents=bpm_events, rotationEvents=[],
                     colorNotes=sorted(flow.notes, key=lambda n: (n["b"], n["c"])),
                     bombNotes=[], obstacles=[], sliders=[], burstSliders=[],
                     basicBeatmapEvents=lightshow(), colorBoostBeatmapEvents=[], waypoints=[],
                     basicEventTypesWithKeywords={"d": []}, lightColorEventBoxGroups=[],
                     lightRotationEventBoxGroups=[], lightTranslationEventBoxGroups=[],
                     vfxEventBoxGroups=[], _fxEventsCollection={"_fl": [], "_il": []},
                     useNormalEventsAsCompatibleEvents=True)
        (SONG / f"{level}.dat").write_text(json.dumps(chart, separators=(",", ":")) + "\n")
        choreo[level] = flow.records
        charts.append(dict(_difficulty=level, _difficultyRank=rank,
                           _beatmapFilename=f"{level}.dat", _noteJumpMovementSpeed=njs,
                           _noteJumpStartBeatOffset=jump_offset))
        print(f"{level}: {len(flow.notes)} blocks / {len(flow.notes) / TIMING['duration_s']:.2f} NPS")
    info = dict(_version="2.1.0", _songName="Rare Earth", _songSubName="(Techno Remix)",
                _songAuthorName="Robot Ninja Apocalypse", _levelAuthorName="Codex",
                _beatsPerMinute=BPM, _songTimeOffset=0, _shuffle=0, _shufflePeriod=.5,
                _previewStartTime=54.7604, _previewDuration=18,
                _songFilename="song.ogg", _coverImageFilename="cover.png",
                _environmentName="DefaultEnvironment", _allDirectionsEnvironmentName="GlassDesertEnvironment",
                _environmentNames=[], _colorSchemes=[],
                _difficultyBeatmapSets=[dict(_beatmapCharacteristicName="Standard", _difficultyBeatmaps=charts)])
    (SONG / "Info.dat").write_text(json.dumps(info, indent=2) + "\n")
    (ANALYSIS / "choreography.json").write_text(json.dumps(choreo, indent=2) + "\n")
    provenance = dict(source=str(SOURCE.relative_to(PROJECT)), source_sha256=sha,
                      audio_conversion="Original MP3 decoded to Ogg Vorbis q6, 44100 Hz; no trim, padding, or tempo change",
                      duration_s=TIMING["duration_s"], musical_beat_zero_s=TIMING["beat_zero_s"],
                      encoded_beat_phase=PHASE, initial_bpm=BPM,
                      bpm_events_per_chart=len(bpm_events), sections=TIMING["sections"],
                      physical_playtest=False, game_engine_load_test=False)
    (ANALYSIS / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


if __name__ == "__main__":
    main()
