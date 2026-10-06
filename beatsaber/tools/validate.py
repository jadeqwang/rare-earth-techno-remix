"""Validate exports independently against StepMania's parser and decoded audio."""
from pathlib import Path
import bisect
import hashlib
import json
import math
import subprocess
import zipfile

import imageio_ffmpeg
import numpy as np
from PIL import Image
from scipy.signal import correlate, correlation_lags
import simfile
from simfile.timing import Beat, TimingData
from simfile.timing.engine import TimingEngine

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
SONG = ROOT / "CustomLevels/Rare Earth (Techno Remix)"
SOURCE = PROJECT / "audio/Rare_Earth_DDR.mp3"
DDR = PROJECT / "ddr/Songs/Rare Earth Pack/Rare Earth (Techno Remix)"
with (DDR / "Rare Earth (Techno Remix).ssc").open() as f:
    ENGINE = TimingEngine(TimingData(simfile.load(f, strict=True)))
INFO = json.loads((SONG / "Info.dat").read_text())
PROVENANCE = json.loads((ROOT / "analysis/provenance.json").read_text())
PHASE = PROVENANCE["encoded_beat_phase"]
DIRECTIONS = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0),
              4: (-1, 1), 5: (1, 1), 6: (-1, -1), 7: (1, -1)}


class BeatClock:
    def __init__(self, initial_bpm, events):
        self.beats = [0.0]
        self.seconds = [0.0]
        self.bpms = [initial_bpm]
        for e in sorted(events, key=lambda x: x["b"]):
            if e["b"] == 0:
                self.bpms[0] = e["m"]
                continue
            self.seconds.append(self.seconds[-1] + (e["b"] - self.beats[-1]) * 60 / self.bpms[-1])
            self.beats.append(e["b"])
            self.bpms.append(e["m"])

    def seconds_at(self, beat):
        i = bisect.bisect_right(self.beats, beat) - 1
        return self.seconds[i] + (beat - self.beats[i]) * 60 / self.bpms[i]


def decode(path, rate=22050):
    output = subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(path),
                                      "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", str(rate), "pipe:1"])
    return np.frombuffer(output, dtype="<f4")


def check_audio(path):
    rate = 22050
    a, b = decode(SOURCE, rate), decode(path, rate)
    reports = []
    for center in [5, 35, 65, 95, 123]:
        start, end = int((center - 1) * rate), int((center + 1) * rate)
        x, y = a[start:end], b[start:end]
        corr = correlate(y, x, mode="full", method="fft")
        lags = correlation_lags(len(y), len(x), mode="full")
        near = np.abs(lags) <= rate // 10
        lag = int(lags[near][np.argmax(corr[near])])
        similarity = float(np.corrcoef(x, y)[0, 1])
        reports.append(dict(center_s=center, lag_samples=lag, lag_ms=round(lag / rate * 1000, 4),
                            zero_lag_correlation=round(similarity, 6)))
    assert max(abs(r["lag_ms"]) for r in reports) <= 1, reports
    assert min(r["zero_lag_correlation"] for r in reports) > .96, reports
    assert abs(len(a) - len(b)) / rate < .02
    return dict(source_decoded_duration_s=round(len(a) / rate, 6),
                output_decoded_duration_s=round(len(b) / rate, 6), windows=reports)


def main():
    assert INFO["_version"] == "2.1.0"
    assert INFO["_songTimeOffset"] == 0
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PROVENANCE["source_sha256"]
    image = Image.open(SONG / INFO["_coverImageFilename"])
    assert image.width == image.height and image.width >= 256
    levels = INFO["_difficultyBeatmapSets"][0]
    assert levels["_beatmapCharacteristicName"] == "Standard"
    assert [c["_difficulty"] for c in levels["_difficultyBeatmaps"]] == ["Normal", "Hard", "Expert"]
    reports = {}
    for entry in levels["_difficultyBeatmaps"]:
        chart = json.loads((SONG / entry["_beatmapFilename"]).read_text())
        assert chart["version"] == "3.3.0"
        assert not chart.get("customData", {}).get("requirements")
        clock = BeatClock(INFO["_beatsPerMinute"], chart["bpmEvents"])
        errors = []
        # Every sixteenth position, including anchors, is checked against an
        # independent StepMania timing implementation rather than build.py.
        for quarter in range(1133):
            musical = quarter / 4
            errors.append(abs(clock.seconds_at(musical + PHASE) - float(ENGINE.time_at(Beat(musical)))))
        assert max(errors) < .000001, max(errors)
        notes = chart["colorNotes"]
        assert notes == sorted(notes, key=lambda n: (n["b"], n["c"]))
        occupied = set()
        last = {}
        times = []
        angles = []
        gaps = []
        for n in notes:
            assert all(k in n for k in ("b", "x", "y", "c", "d", "a"))
            assert n["c"] in (0, 1) and n["d"] in DIRECTIONS and n["a"] == 0
            assert 0 <= n["x"] <= 3 and 0 <= n["y"] <= 2
            assert n["x"] <= 1 if n["c"] == 0 else n["x"] >= 2
            assert not (n["x"] in (1, 2) and n["y"] > 0), "Face obstruction"
            cell = (n["b"], n["x"], n["y"])
            assert cell not in occupied
            occupied.add(cell)
            t = clock.seconds_at(n["b"])
            assert 3.1 <= t < PROVENANCE["duration_s"] - .2
            musical = round((n["b"] - PHASE) * 2) / 2
            assert abs(musical - (n["b"] - PHASE)) < 1e-7
            assert abs(t - float(ENGINE.time_at(Beat(musical)))) < 1e-6
            times.append(t)
            if n["c"] in last:
                prev, pt = last[n["c"]]
                a, b = np.array(DIRECTIONS[prev["d"]]), np.array(DIRECTIONS[n["d"]])
                angle = math.degrees(math.acos(float(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))
                angles.append(angle)
                gaps.append(t - pt)
                assert angle >= 134.99, (prev, n, angle)
                assert t - pt >= .21, "Same-hand hit spacing too short"
            last[n["c"]] = (n, t)
        assert chart["bombNotes"] == [] and chart["obstacles"] == []
        assert chart["sliders"] == [] and chart["burstSliders"] == []
        for e in chart["basicBeatmapEvents"]:
            assert all(k in e for k in ("b", "et", "i", "f"))
            assert e["et"] in (*range(5), 8, 9)
            assert 0 <= clock.seconds_at(e["b"]) < PROVENANCE["duration_s"]
        peak = max(bisect.bisect_right(times, t + 1) - i for i, t in enumerate(times))
        reports[entry["_difficulty"]] = dict(blocks=len(notes), average_nps=round(len(notes) / PROVENANCE["duration_s"], 3),
                                               peak_blocks_in_one_second=peak, double_hits=len(notes) - len(set(times)),
                                               min_same_hand_gap_s=round(min(gaps), 6), min_direction_change_degrees=round(min(angles), 2),
                                               first_hit_s=round(min(times), 6), last_hit_s=round(max(times), 6),
                                               max_ddr_timing_difference_ms=round(max(errors) * 1000, 6),
                                               light_events=len(chart["basicBeatmapEvents"]), bpm_events=len(chart["bpmEvents"]))
    assert len({r["blocks"] for r in reports.values()}) == 3
    assert list(r["blocks"] for r in reports.values()) == sorted(r["blocks"] for r in reports.values())
    audio = check_audio(SONG / INFO["_songFilename"])
    archive = ROOT / "Rare_Earth_Beat_Saber_Pack.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(SONG.iterdir()):
            z.write(path, path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == {"Info.dat", "Normal.dat", "Hard.dat", "Expert.dat", "song.ogg", "cover.png"}
        for filename in z.namelist():
            assert z.read(filename) == (SONG / filename).read_bytes()
    report = dict(passed=True, source_sha256=PROVENANCE["source_sha256"], charts=reports,
                  audio=audio, cover_size=list(image.size), archive_files=6,
                  checks=["independent DDR timing integration", "all note bounds and fields", "strict hand separation",
                          "alternating swing directions", "same-hand time spacing", "no face notes or overlaps",
                          "audio alignment at five song positions", "archive round-trip"],
                  physical_playtest=False, game_engine_load_test=False,
                  limitations="Static format and flow checks plus decoded-audio checks; no VR gameplay test.")
    (ROOT / "analysis/validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
