"""Independently parse exports, check timing, and audit two-foot playability."""
from pathlib import Path
import hashlib
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="fs")
import numpy as np
import simfile
from simfile.notes import NoteData, NoteType
from simfile.notes.count import count_steps, count_jumps, count_holds, count_mines
from simfile.timing import TimingData
from simfile.timing.engine import TimingEngine
from simfile.timing import Beat
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SONG = ROOT / "Songs/Rare Earth Pack/Rare Earth (Techno Remix)"
timing = json.loads((ROOT / "analysis/timing.json").read_text())
choreography = json.loads((ROOT / "analysis/choreography.json").read_text())
coords = np.array([(-1,0),(0,-1),(0,1),(1,0),(2,0),(3,-1),(3,1),(4,0)])


def audit(sim, config):
    chart = next(c for c in sim.charts if c.get("DESCRIPTION") == config["name"])
    assert chart.get("STEPSTYPE") == config["type"]
    assert chart.get("DIFFICULTY") == config["difficulty"]
    assert int(chart.get("METER")) == config["meter"]
    nd = NoteData(chart)
    notes = list(nd)
    engine = TimingEngine(TimingData(sim, chart))
    ncols = config["columns"]
    active = {}
    groups = {}
    times = []
    end_times = []
    pairs = []
    for n in notes:
        assert 0 <= n.column < ncols
        assert n.note_type in [NoteType.TAP, NoteType.HOLD_HEAD, NoteType.TAIL]
        groups.setdefault(n.beat,[]).append(n)
    max_feet = 0
    for beat,row in sorted(groups.items()):
        for n in row:
            if n.note_type == NoteType.TAIL:
                assert n.column in active, f"Orphan tail at {beat}"
                head = active.pop(n.column)
                assert beat > head
                pairs.append([float(head),float(beat),n.column])
                end_times.append(float(engine.time_at(beat)))
        presses = [n for n in row if n.note_type != NoteType.TAIL]
        demand = len(active)+len(presses)
        max_feet = max(max_feet,demand)
        assert demand <= 2, f"{config['name']} needs {demand} feet at {beat}"
        assert len({n.column for n in row}) == len(row)
        for n in presses:
            assert n.column not in active, f"Note inside active hold at {beat}"
            t = float(engine.time_at(beat))
            assert 0 <= t < timing["duration_s"]
            if not times or t != times[-1]:
                times.append(t)
            if n.note_type == NoteType.HOLD_HEAD:
                active[n.column] = beat
    assert not active, "Unclosed holds"
    assert not end_times or max(end_times) < timing["duration_s"]
    exported_heads = [(float(n.beat),n.column) for n in notes if n.note_type != NoteType.TAIL]
    authored_heads = [(p["beat"],c) for p in config["placements"] for c in (p["feet"] if p["jump"] else [p["column"]])]
    assert sorted(exported_heads) == sorted(authored_heads)
    last_feet = [0,3]
    max_travel = 0.0
    last_step_times = [-99.,-99.]
    max_speed = 0.0
    for p in config["placements"]:
        feet = p["feet"]
        left,right = coords[feet]
        assert left[0] <= right[0], f"Forced crossover at {p['beat']}"
        assert np.linalg.norm(left-right) <= 2.25
        moving = [0,1] if p["jump"] else [p["foot"]]
        for f in moving:
            travel = float(np.linalg.norm(coords[feet[f]]-coords[last_feet[f]]))
            if ncols == 8:
                assert travel <= 2.83, f"Pad teleport at {p['beat']}"
            if not p["jump"]:
                max_travel = max(max_travel, travel)
                elapsed = float(engine.time_at(Beat(str(p["beat"]))))-last_step_times[f]
                max_speed = max(max_speed,travel/elapsed)
            last_step_times[f] = float(engine.time_at(Beat(str(p["beat"]))))
        last_feet = list(feet)
    used = sorted(set(n.column for n in notes))
    assert used == list(range(ncols)), f"Unused arrows: {used}"
    if config["level"] == "beginner":
        assert count_jumps(nd) == 0
        assert all(float(n.beat).is_integer() for n in notes if n.note_type != NoteType.TAIL)
    if config["level"] == "easy":
        assert all(float(n.beat).is_integer() for n in notes if n.note_type != NoteType.TAIL)
    local_bursts = 0
    if ncols == 8 and config["level"] == "heavy":
        rapid_units = {int(float(n.beat)) for n in notes
                       if n.note_type != NoteType.TAIL and float(n.beat)%1 in [.25,.75]}
        for beat in rapid_units:
            pads = {n.column//4 for n in notes if n.note_type != NoteType.TAIL
                    and beat <= float(n.beat) < beat+1}
            assert len(pads) == 1, f"Sixteenth burst crosses pads at beat {beat}"
        local_bursts = len(rapid_units)
    t = np.array(times)
    peak2 = max(int(np.count_nonzero((t>=x)&(t<x+2))) for x in t)/2
    subdivisions = sorted(set(round(float(n.beat)%1,2) for n in notes if n.note_type != NoteType.TAIL))
    result = dict(
        name=config["name"], type=config["type"], difficulty=config["difficulty"],
        meter=config["meter"], step_rows=count_steps(nd),
        arrow_presses=sum(n.note_type != NoteType.TAIL for n in notes),
        jumps=count_jumps(nd), holds=count_holds(nd), mines=count_mines(nd),
        max_simultaneous_feet=max_feet, used_columns=used,
        first_note_s=round(times[0],4), last_note_or_tail_s=round(max(times+end_times),4),
        peak_2s_note_rows_per_second=peak2,
        max_same_foot_travel_panel_units=round(max_travel,3),
        max_same_foot_speed_panel_units_per_second=round(max_speed,3),
        fractional_beat_positions=subdivisions,
        verified_single_pad_sixteenth_bursts=local_bursts,
        hold_pairs=pairs,
    )
    return result, notes


def main():
    parsed = []
    for ext in ["sm","ssc"]:
        with (SONG / f"Rare Earth (Techno Remix).{ext}").open() as f:
            parsed.append(simfile.load(f,strict=True))
    assert all(len(s.charts) == 8 for s in parsed)
    expected = {(t,d) for t in ["dance-single","dance-double"]
                for d in ["Beginner","Easy","Medium","Hard"]}
    for sim in parsed:
        assert {(c["STEPSTYPE"],c["DIFFICULTY"]) for c in sim.charts} == expected
    baseline_path = ROOT / "analysis/revision-baseline.json"
    preserved = []
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())
        for sim in parsed:
            for k,v in baseline["shared_tags"].items():
                assert sim[k] == v, f"Changed shared song metadata: {k}"
        original_names = {
            "Beginner Single":"Beginner Single",
            "Standard Single":"Intermediate Single",
            "Heavy Single":"Advanced Single",
            "Standard Double":"Intermediate Double",
        }
        for chart in parsed[1].charts:
            name = chart["DESCRIPTION"]
            if name in original_names:
                digest = hashlib.sha256(chart["NOTES"].encode()).hexdigest()
                assert digest == baseline["note_sha256"][original_names[name]], f"Changed steps in {name}"
                preserved.append(name)
    summaries = []
    for config in choreography:
        a,na = audit(parsed[0],config)
        b,nb = audit(parsed[1],config)
        assert a == b
        assert [(n.beat,n.column,n.note_type) for n in na] == [(n.beat,n.column,n.note_type) for n in nb]
        summaries.append(b)
    for step_type in ["dance-single","dance-double"]:
        levels = [c for c in summaries if c["type"] == step_type]
        assert [c["difficulty"] for c in levels] == ["Beginner","Easy","Medium","Hard"]
        for low,high in zip(levels,levels[1:]):
            assert low["meter"] < high["meter"]
            assert low["step_rows"] < high["step_rows"]
            assert low["peak_2s_note_rows_per_second"] <= high["peak_2s_note_rows_per_second"]
    engine = TimingEngine(TimingData(parsed[1]))
    errors = [abs(float(engine.time_at(Beat(b["beat"]))) - b["time_s"]) for b in timing["beats"]]
    assert max(errors) < .00001
    for asset in ["MUSIC","BANNER","BACKGROUND","JACKET"]:
        assert (SONG/parsed[1][asset]).is_file()
    audio = SONG / parsed[1]["MUSIC"]
    assert hashlib.sha256(audio.read_bytes()).hexdigest() == timing["source_sha256"]
    assert abs(sf.info(audio).duration-timing["duration_s"]) < .001
    report = dict(
        status="passed", parser="simfile 2.1.1 (strict)",
        equivalent_sm_ssc=True, charts=len(summaries),
        levels_per_mode=4, original_charts_preserved=preserved,
        serialized_timing_max_error_ms=round(max(errors)*1000,7),
        original_audio_sha256=timing["source_sha256"],
        audio_unchanged=True, bpm_range=timing["bpm_range"],
        duration_s=timing["duration_s"],
        limitations="Programmatic file/timing/two-foot review. Difficulty meters are provisional; no physical pad playtest or game-engine launch was performed.",
        chart_summary=summaries,
    )
    (ROOT / "analysis/validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({**report,"chart_summary":[{k:v for k,v in c.items() if k != "hold_pairs"} for c in summaries]},indent=2))


if __name__ == "__main__":
    main()
