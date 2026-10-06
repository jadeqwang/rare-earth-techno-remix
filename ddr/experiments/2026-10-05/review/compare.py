"""Independent SM/SSC audit for the Rare Earth model edition.

Run with ddr/.venv/bin/python compare.py [candidate.sm ...] --out report.json.
Only writes the selected report. The existing source/chart files are read only.
Foot assignment is a deliberately bounded geometric model, not a pad playtest.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="fs")
import numpy as np
import simfile
from simfile.notes import NoteData, NoteType
from simfile.timing import Beat, TimingData
from simfile.timing.engine import TimingEngine
import soundfile as sf

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "Songs/Rare Earth Pack/Rare Earth (Techno Remix)/Rare Earth (Techno Remix).ssc"
SOURCE = ROOT.parent / "audio/Rare_Earth_DDR.mp3"
TIMING = ROOT / "analysis/timing.json"
COORDS = [(-1, 0), (0, -1), (0, 1), (1, 0), (2, 0), (3, -1), (3, 1), (4, 0)]
PRESS_TYPES = {NoteType.TAP, NoteType.HOLD_HEAD, NoteType.ROLL_HEAD}
HEAD_TYPES = {NoteType.HOLD_HEAD, NoteType.ROLL_HEAD}
SUPPORTED = PRESS_TYPES | {NoteType.TAIL, NoteType.MINE}
LEVEL_ORDER = {"Beginner": 0, "Easy": 1, "Medium": 2, "Hard": 3, "Challenge": 4, "Edit": 5}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distance(a, b):
    return math.dist(COORDS[a], COORDS[b])


def quantile(xs, fraction):
    return float(np.quantile(xs, fraction)) if xs else None


def peak_window(times, seconds=2):
    right = peak = 0
    for left, start in enumerate(times):
        right = max(right, left)
        while right < len(times) and times[right] < start + seconds:
            right += 1
        peak = max(peak, right - left)
    return peak / seconds


def max_run(signatures):
    best = run = 0
    previous = None
    for signature in signatures:
        run = run + 1 if signature == previous else 1
        best = max(best, run)
        previous = signature
    return best


def note_signature(chart):
    return [(str(n.beat), n.column, str(n.note_type)) for n in NoteData(chart)]


def infer_feet(events, ncols, forward_only, span=2.25, max_move=2.83):
    """Hold-aware finite-state search, no brackets or airborne idle reposition.

    DP minimizes consecutive same-foot singleton presses, then total movement.
    Each state retains foot panels, locked holds, and previous singleton foot.
    Movement rate is descriptive for that optimum, not a speed lower bound.
    All valid initial stances are allowed; movement before first notes is free.
    """
    def valid(a, b):
        return a != b and distance(a, b) <= span and (
            not forward_only or COORDS[a][0] <= COORDS[b][0]
        )

    states = {}
    # value: (double steps, total travel, predecessor, event, last press times)
    for a, b in itertools.permutations(range(ncols), 2):
        if valid(a, b):
            states[(a, b, -1, -1, -1)] = (0, 0., None, None, (None, None))
    for event in events:
        beat, time, presses, tails, heads = event
        new = {}
        for key, value in states.items():
            a, b, previous, locka, lockb = key
            locks = [locka, lockb]
            for foot in [0, 1]:
                if locks[foot] in tails:
                    locks[foot] = -1
            free = [foot for foot in [0, 1] if locks[foot] < 0]
            if len(presses) > len(free):
                continue
            assignments = itertools.permutations(free, len(presses))
            for assigned in assignments:
                positions = [a, b]
                next_locks = list(locks)
                travels = [0., 0.]
                for column, foot in zip(presses, assigned):
                    positions[foot] = column
                    travels[foot] = distance((a, b)[foot], column)
                    if column in heads:
                        next_locks[foot] = column
                if not valid(*positions) or (ncols == 8 and max(travels) > max_move):
                    continue
                singleton = assigned[0] if len(assigned) == 1 else -1
                double_step = singleton >= 0 and previous == singleton
                next_previous = singleton if presses else previous
                next_times = list(value[4])
                speeds = []
                for foot in assigned:
                    elapsed = None if next_times[foot] is None else time - next_times[foot]
                    if elapsed and elapsed > 0:
                        speeds.append((travels[foot] / elapsed, foot))
                    next_times[foot] = time
                crossed = COORDS[positions[0]][0] > COORDS[positions[1]][0]
                record = {"beat": beat, "time_s": time, "feet": positions,
                          "press_columns": presses, "assigned_feet": assigned,
                          "consecutive_same_foot": bool(double_step),
                          "crossed_stance": crossed, "travel": travels, "speeds": speeds}
                next_key = (*positions, next_previous, *next_locks)
                next_value = (value[0] + int(double_step), value[1] + sum(travels),
                              value, record, tuple(next_times))
                if next_key not in new or next_value[:2] < new[next_key][:2]:
                    new[next_key] = next_value
        if not new:
            return {"feasible": False, "first_failure_beat": beat,
                    "first_failure_time_s": round(time, 6),
                    "reason": "No foot assignment under this model's stance/travel/hold constraints."}
        states = new
    if not states:
        return {"feasible": False, "reason": "No initial stance under model constraints."}
    best = min(states.values(), key=lambda value: value[:2])
    path = []
    cursor = best
    while cursor[2] is not None:
        path.append(cursor[3])
        cursor = cursor[2]
    path.reverse()
    speed_records = sorted(
        [{"beat": p["beat"], "time_s": round(p["time_s"], 6), "foot": foot,
          "panel_units_per_second": round(speed, 4)} for p in path for speed, foot in p["speeds"]],
        key=lambda x: x["panel_units_per_second"], reverse=True,
    )
    repeated = [p for p in path if p["consecutive_same_foot"]]
    # In the chosen optimum: repeats of the same foot within 300 ms are difficult,
    # but this is not a proof that every valid assignment needs a rapid repeat.
    rapid = []
    previous_press = None
    for p in path:
        if p["consecutive_same_foot"] and previous_press and p["time_s"] - previous_press["time_s"] <= .30:
            rapid.append({"beat": p["beat"], "time_s": round(p["time_s"], 6),
                          "gap_s": round(p["time_s"] - previous_press["time_s"], 6)})
        if p["press_columns"]:
            previous_press = p
    return {"feasible": True,
            "minimum_consecutive_same_foot_singletons": best[0],
            "chosen_assignment_travel_panel_units": round(best[1], 4),
            "chosen_assignment_crossed_stance_rows": sum(p["crossed_stance"] for p in path),
            "chosen_assignment_maximum_stance_span_panel_units": round(max((distance(*p["feet"]) for p in path),default=0),4),
            "chosen_assignment_maximum_per_foot_travel_panel_units": round(max((max(p["travel"]) for p in path),default=0),4),
            "chosen_assignment_rapid_same_foot_singletons": len(rapid),
            "rapid_same_foot_examples": rapid[:20],
            "chosen_assignment_peak_speed_panel_units_per_s": speed_records[0]["panel_units_per_second"] if speed_records else 0,
            "peak_speed_examples": speed_records[:8]}


def make_onsets(audio):
    """Low/broad spectral novelty proxy from unchanged MP3, 10 ms analysis hop."""
    samples, sr = sf.read(audio, dtype="float32", always_2d=True)
    samples = samples.mean(axis=1)
    # Integer decimation keeps exact frame times; its antialias limitation is
    # documented and only bins below 4 kHz are used for this coarse proxy.
    decimation = max(1, sr // 22050)
    samples = samples[::decimation]
    rate = sr / decimation
    hop = round(rate * .010)
    width = 1024
    padded = np.pad(samples, (width // 2, width // 2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, width)[::hop]
    frequencies = np.fft.rfftfreq(width, 1 / rate)
    low = (frequencies >= 30) & (frequencies < 250)
    broad = (frequencies >= 250) & (frequencies <= 4000)
    window = np.hanning(width)
    previous = np.zeros(width // 2 + 1)
    output = []
    for start in range(0, len(frames), 256):
        spectrum = np.log1p(10 * np.abs(np.fft.rfft(frames[start:start+256] * window)))
        changes = np.maximum(0, np.diff(np.vstack([previous, spectrum]), axis=0))
        output.extend(np.column_stack([changes[:, low].mean(axis=1), changes[:, broad].mean(axis=1)]))
        previous = spectrum[-1]
    output = np.asarray(output)
    for band in range(2):
        output[:, band] /= max(float(np.quantile(output[:, band], .95)), 1e-9)
    strength = .5 * output[:, 0] + .5 * output[:, 1]
    threshold = float(np.quantile(strength, .95))
    candidates = [i for i in range(1, len(strength)-1)
                  if strength[i] >= threshold and strength[i] >= strength[i-1] and strength[i] > strength[i+1]]
    peaks = []
    for i in sorted(candidates, key=lambda j: strength[j], reverse=True):
        if not any(abs(i-j) * hop / rate < .070 for j in peaks):
            peaks.append(i)
    peaks.sort()
    return {"frame_times": np.arange(len(strength)) * hop / rate,
            "strength": strength, "peaks": [i * hop / rate for i in peaks],
            "threshold": threshold,
            "method": "Centered 1024-sample FFT; 10 ms hop; positive log spectral flux in 30–250 Hz and 250–4000 Hz bands; peaks above full-song 95th percentile, 70 ms separation; 50 ms matching tolerance. Coarse proxy; no stem analysis or musical judgment."}


def nearest_distance(sorted_values, x):
    index = bisect.bisect_left(sorted_values, x)
    return min([abs(sorted_values[i]-x) for i in [index-1, index] if 0 <= i < len(sorted_values)], default=float("inf"))


def onset_metrics(times, onset):
    strengths = []
    frames = onset["frame_times"]
    for time in times:
        left = int(np.searchsorted(frames, time - .040))
        right = int(np.searchsorted(frames, time + .040))
        strengths.append(float(np.max(onset["strength"][left:right])) if right > left else 0.)
    peaks = onset["peaks"]
    return {"mean_near_note_novelty": round(float(np.mean(strengths)), 5) if strengths else 0,
            "median_near_note_novelty": round(float(np.median(strengths)), 5) if strengths else 0,
            "notes_near_strong_onset_fraction": round(sum(nearest_distance(peaks, t) <= .05 for t in times) / max(1, len(times)), 5),
            "strong_onset_coverage_fraction": round(sum(nearest_distance(times, t) <= .05 for t in peaks) / max(1, len(peaks)), 5),
            "strong_onset_count": len(peaks)}


def summarize_chart(sim, chart, timing, onset, stance_span):
    name = chart.get("DESCRIPTION") or chart.get("CHARTNAME") or "Unnamed"
    kind = chart.get("STEPSTYPE")
    ncols = {"dance-single": 4, "dance-double": 8}.get(kind)
    result = {"name": name, "type": kind, "difficulty": chart.get("DIFFICULTY"),
              "meter": int(chart.get("METER") or 0), "errors": [], "warnings": []}
    if ncols is None:
        result["errors"].append("Unsupported chart type for this four/eight-panel foot audit.")
        return result
    engine = TimingEngine(TimingData(sim, chart))
    grid_errors = [abs(float(engine.time_at(Beat(str(b["beat"])))) - b["time_s"]) for b in timing["beats"]]
    result["timing_max_reference_error_ms"] = round(max(grid_errors) * 1000, 8)
    if max(grid_errors) > .0001:
        result["errors"].append("Chart timing diverges from measured source grid by more than 0.1 ms.")
    source_timing = TimingData(sim, chart)
    expected_bpms = [(float(s["beat"]), float(s["bpm"])) for s in timing["bpms"]]
    actual_bpms = [(float(pair.beat), float(pair.value)) for pair in source_timing.bpms]
    result["bpm_segment_count"] = len(actual_bpms)
    result["bpm_map_matches_reference"] = len(actual_bpms) == len(expected_bpms) and all(
        abs(a-c) < 1e-7 and abs(b-d) < 1e-6 for (a,b), (c,d) in zip(actual_bpms, expected_bpms))
    result["offset_matches_reference"] = abs(float(source_timing.offset)-timing["offset"]) < 1e-7
    result["extra_timing_events"] = {key: len(getattr(source_timing, key)) for key in ["stops", "delays", "warps"]}
    if not result["bpm_map_matches_reference"] or not result["offset_matches_reference"] or any(result["extra_timing_events"].values()):
        result["errors"].append("BPM map, offset, or extra timing events differ from source timing.")
    notes = list(NoteData(chart))
    groups = defaultdict(list)
    for note in notes:
        groups[float(note.beat)].append(note)
        if not 0 <= note.column < ncols:
            result["errors"].append(f"Out-of-range column {note.column} at beat {note.beat}.")
        if note.note_type not in SUPPORTED:
            result["errors"].append(f"Unsupported note type {note.note_type} at beat {note.beat}.")
    active = {}
    rows, hold_pairs, events, all_times = [], [], [], []
    max_demand = 0
    for beat, row in sorted(groups.items()):
        time = float(engine.time_at(Beat(str(beat))))
        all_times.append(time)
        if time < 0 or time >= timing["duration_s"]:
            result["errors"].append(f"Note/tail outside source duration at beat {beat} ({time:.6f} s).")
        columns = [note.column for note in row]
        if len(set(columns)) != len(columns):
            result["errors"].append(f"Duplicate column events at beat {beat}.")
        tails = [note.column for note in row if note.note_type == NoteType.TAIL]
        for column in tails:
            head = active.pop(column, None)
            if head is None:
                result["errors"].append(f"Orphan hold tail at beat {beat}, column {column}.")
            elif beat <= head:
                result["errors"].append(f"Nonpositive hold at beat {beat}, column {column}.")
            else:
                hold_pairs.append([head, beat, column])
        presses = [note.column for note in row if note.note_type in PRESS_TYPES]
        heads = [note.column for note in row if note.note_type in HEAD_TYPES]
        demand = len(active) + len(presses)
        max_demand = max(max_demand, demand)
        if demand > 2:
            result["errors"].append(f"Needs {demand} simultaneous panels at beat {beat} (held panels plus new presses).")
        for column in presses:
            if column in active:
                result["errors"].append(f"Press inside active hold at beat {beat}, column {column}.")
        for column in heads:
            active[column] = beat
        if presses:
            rows.append((beat, time, tuple(sorted(presses))))
        events.append((beat, time, presses, tails, heads))
    if active:
        result["errors"].append(f"Unclosed holds: {active}.")
    times = [r[1] for r in rows]
    gaps = [b-a for a,b in zip(times, times[1:])]
    press_hist = Counter(column for _,_,columns in rows for column in columns)
    probabilities = [n / max(1, sum(press_hist.values())) for n in press_hist.values()]
    count = len(rows)
    hold_durations = [float(engine.time_at(Beat(str(b)))) - float(engine.time_at(Beat(str(a))))
                      for a,b,_ in hold_pairs]
    intervals = sorted((float(engine.time_at(Beat(str(a)))), float(engine.time_at(Beat(str(b)))))
                       for a,b,_ in hold_pairs)
    merged = []
    for start,end in intervals:
        if merged and start <= merged[-1][1] + 1e-7:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start,end])
    result["hold_density"] = {"minimum_hold_s": min(hold_durations,default=None),
                              "median_hold_s": quantile(hold_durations,.50),
                              "maximum_hold_s": max(hold_durations,default=None),
                              "total_held_panel_seconds": round(sum(hold_durations),5),
                              "song_fraction_with_any_active_hold": round(sum(b-a for a,b in merged)/timing["duration_s"],5),
                              "longest_contiguous_hold_passage_s": max((b-a for a,b in merged),default=0),
                              "holds_under_150ms": sum(duration < .15 for duration in hold_durations),
                              "release_fractional_beat_positions": sorted(set(round(b%1,8) for _,b,_ in hold_pairs))}
    if any(duration < .15 for duration in hold_durations):
        result["warnings"].append("One or more holds last less than 150 ms; inspect their readability.")
    result.update({"step_rows": count, "arrow_presses": sum(press_hist.values()),
                   "jumps": sum(len(columns) == 2 for _,_,columns in rows),
                   "holds": sum(note.note_type == NoteType.HOLD_HEAD for note in notes),
                   "rolls": sum(note.note_type == NoteType.ROLL_HEAD for note in notes),
                   "mines": sum(note.note_type == NoteType.MINE for note in notes),
                   "complete_hold_pairs": len(hold_pairs), "hold_pairs": hold_pairs,
                   "max_simultaneous_panel_demand": max_demand,
                   "used_columns": sorted(press_hist), "column_press_counts": dict(sorted(press_hist.items())),
                   "normalized_column_entropy": round(-sum(p*math.log2(p) for p in probabilities)/math.log2(ncols), 5),
                   "first_note_s": round(times[0], 6) if times else None,
                   "last_note_or_tail_s": round(max(all_times), 6) if all_times else None,
                   "average_note_rows_per_song_second": round(count / timing["duration_s"], 4),
                   "peak_2s_note_rows_per_second": peak_window(times),
                   "fractional_beat_positions": sorted(set(round(beat%1, 8) for beat,_,_ in rows)),
                   "minimum_interrow_gap_s": min(gaps, default=None),
                   "longest_interrow_rest_s": max(gaps, default=None),
                   "interrow_gap_p10_s": quantile(gaps, .10), "interrow_gap_median_s": quantile(gaps, .50)})
    measures = defaultdict(list)
    for beat,time,columns in rows:
        measures[int(beat//4)].append((round(beat%4, 8), columns))
    nonempty = sorted(measures)
    rhythm = [tuple((offset, len(columns)) for offset,columns in measures[m]) for m in nonempty]
    arrow = [tuple(measures[m]) for m in nonempty]
    rhythm_counts, arrow_counts = Counter(rhythm), Counter(arrow)
    phrases = [tuple(tuple(measures.get(m+i, ())) for i in range(4)) for m in range(0, max(measures,default=0)+1, 4)]
    phrase_counts = Counter(p for p in phrases if any(p))
    ngrams = [tuple(columns for _,_,columns in rows[i:i+4]) for i in range(max(0,count-3))]
    # Consecutive runs preserve empty measures, unlike prevalence measures.
    all_rhythm = [tuple((offset,len(columns)) for offset,columns in measures.get(m, ())) for m in range(min(measures,default=0), max(measures,default=0)+1)]
    result["repetition"] = {"nonempty_measures": len(nonempty),
                            "unique_rhythmic_measure_templates": len(rhythm_counts),
                            "unique_arrow_measure_templates": len(arrow_counts),
                            "most_common_rhythm_measure_fraction": round(max(rhythm_counts.values(),default=0)/max(1,len(nonempty)),5),
                            "most_common_arrow_measure_fraction": round(max(arrow_counts.values(),default=0)/max(1,len(nonempty)),5),
                            "max_consecutive_identical_rhythm_measures": max_run(all_rhythm),
                            "unique_nonempty_four_measure_arrow_phrases": len(phrase_counts),
                            "four_measure_phrase_count": sum(phrase_counts.values()),
                            "unique_four_row_arrow_ngrams": len(set(ngrams)),
                            "four_row_arrow_ngram_diversity": round(len(set(ngrams))/max(1,len(ngrams)),5),
                            "most_common_rhythm_templates": [{"rows": list(pattern), "measures": n} for pattern,n in rhythm_counts.most_common(5)]}
    result["section_density"] = []
    for section in timing["sections"]:
        local = [(beat,time,cols) for beat,time,cols in rows if section["t"] <= time < section["end"]]
        result["section_density"].append({"id": section["id"], "label": section["label"],
                                          "start_s": section["t"], "end_s": section["end"],
                                          "step_rows": len(local),
                                          "rows_per_second": round(len(local)/(section["end"]-section["t"]),4),
                                          "jumps": sum(len(cols)==2 for _,_,cols in local),
                                          "offbeat_rows": sum(beat%1!=0 for beat,_,_ in local)})
    rapid_same = []
    rapid_aba = []
    for i,(beat,time,cols) in enumerate(rows):
        if i and len(cols)==1 and cols == rows[i-1][2] and time-rows[i-1][1] <= .30:
            rapid_same.append({"beat": beat,"time_s": round(time,6),"column": cols[0],"gap_s": round(time-rows[i-1][1],6)})
        if i>=2 and len(cols)==1 and cols==rows[i-2][2] and len(rows[i-1][2])==1 and cols!=rows[i-1][2] and time-rows[i-2][1]<=.65:
            rapid_aba.append({"beat": rows[i-2][0],"columns": [cols[0],rows[i-1][2][0],cols[0]],"duration_s": round(time-rows[i-2][1],6)})
    result["suspicious_patterns"] = {"rapid_repeated_panel_count": len(rapid_same), "rapid_repeated_panel_examples": rapid_same[:20],
                                     "rapid_aba_count": len(rapid_aba), "rapid_aba_examples": rapid_aba[:20]}
    if ncols==8:
        rapid_crosspad=[]
        for previous,current in zip(rows,rows[1:]):
            before={column//4 for column in previous[2]}
            after={column//4 for column in current[2]}
            if before.isdisjoint(after) and current[1]-previous[1] <= .30:
                rapid_crosspad.append({"beat":current[0],"gap_s":round(current[1]-previous[1],6)})
        sixteenth_units={int(beat) for beat,_,_ in rows if round(beat%1,8) in [.25,.75]}
        mixed=[]
        for unit in sorted(sixteenth_units):
            pads={column//4 for beat,_,columns in rows if unit<=beat<unit+1 for column in columns}
            if len(pads)>1:
                mixed.append(unit)
        result["double_pad_transitions"]={"rapid_crosspad_row_transitions":len(rapid_crosspad),
                                           "rapid_crosspad_examples":rapid_crosspad[:20],
                                           "sixteenth_beat_units":len(sixteenth_units),
                                           "sixteenth_units_staying_on_one_pad":len(sixteenth_units)-len(mixed),
                                           "mixed_pad_sixteenth_unit_beats":mixed}
    if result["mines"]:
        result["warnings"].append("Mines are counted, but the foot assignment search does not model mine avoidance.")
    if not result["errors"]:
        forward = infer_feet(events,ncols,True,stance_span)
        result["foot_assignment"] = {"forward_only": forward}
        relaxed = infer_feet(events,ncols,False,stance_span)
        result["foot_assignment"]["crossovers_allowed"] = relaxed
        if not forward["feasible"] and relaxed["feasible"]:
            result["warnings"].append("A crossover or a more relaxed stance is required by this conservative model; crossovers are a valid advanced chart style.")
        if not relaxed["feasible"]:
            result["warnings"].append("No solution under the conservative stance/travel model; inspect manually or with GrooveAuthor before selecting.")
        if forward["feasible"] and forward["minimum_consecutive_same_foot_singletons"] > 0:
            result["warnings"].append("Perfect alternation is unavailable under this forward-facing model; counts include harmless repeats around rests.")
    if onset:
        result["onset_proxy"] = onset_metrics(times,onset)
    result["status"] = "failed" if result["errors"] else "passed"
    return result


def audit_file(path, timing, onset, stance_span):
    result = {"path": str(path), "file_sha256": sha(path)}
    try:
        with path.open() as handle:
            sim = simfile.load(handle,strict=True)
        audio = path.parent / (sim.get("MUSIC") or "")
        result["music_path"] = str(audio)
        result["music_exists"] = audio.is_file()
        result["music_sha256"] = sha(audio) if audio.is_file() else None
        result["music_matches_source"] = result["music_sha256"] == timing["source_sha256"]
        result["charts"] = [summarize_chart(sim,chart,timing,onset,stance_span) for chart in sim.charts]
        result["errors"] = [] if result["music_matches_source"] else ["Candidate MUSIC file is missing or does not have the exact source SHA256."]
        result["progression"] = []
        for kind in ["dance-single","dance-double"]:
            charts = sorted([c for c in result["charts"] if c["type"]==kind], key=lambda c: (LEVEL_ORDER.get(c["difficulty"],99),c["meter"]))
            if len(charts)<2:
                continue
            result["progression"].append({"type":kind,
                "names":[c["name"] for c in charts], "meters":[c["meter"] for c in charts],
                "rows":[c.get("step_rows") for c in charts], "peaks_2s":[c.get("peak_2s_note_rows_per_second") for c in charts],
                "meters_strictly_increase": all(a["meter"]<b["meter"] for a,b in zip(charts,charts[1:])),
                "rows_strictly_increase": all(a.get("step_rows",0)<b.get("step_rows",0) for a,b in zip(charts,charts[1:])),
                "peaks_do_not_decrease": all(a.get("peak_2s_note_rows_per_second",0)<=b.get("peak_2s_note_rows_per_second",0) for a,b in zip(charts,charts[1:]))})
        result["status"] = "failed" if result["errors"] or any(c.get("errors") for c in result["charts"]) else "passed"
    except Exception as error:
        result.update({"status":"failed", "errors":[f"{type(error).__name__}: {error}"]})
    return result


def compare_exports(files):
    results = []
    for left,right in itertools.combinations(files,2):
        if Path(left["path"]).with_suffix("") != Path(right["path"]).with_suffix(""):
            continue
        try:
            parsed=[]
            for item in [left,right]:
                with Path(item["path"]).open() as handle:
                    parsed.append(simfile.load(handle,strict=True))
            indexed=[{(c.get("STEPSTYPE"),c.get("DIFFICULTY"),c.get("DESCRIPTION") or c.get("CHARTNAME")):c for c in sim.charts} for sim in parsed]
            equal_keys=set(indexed[0])==set(indexed[1])
            def canonical_timing(sim,chart):
                data=TimingData(sim,chart)
                return {"offset":str(data.offset), **{key:[(str(p.beat),str(p.value)) for p in getattr(data,key)] for key in ["bpms","stops","delays","warps"]}}
            results.append({"left":left["path"],"right":right["path"],"same_chart_keys":equal_keys,
                            "same_note_events": equal_keys and all(note_signature(indexed[0][key])==note_signature(indexed[1][key]) for key in indexed[0]),
                            "same_chart_meters":equal_keys and all(indexed[0][key].get("METER")==indexed[1][key].get("METER") for key in indexed[0]),
                            "same_effective_timing":equal_keys and all(canonical_timing(parsed[0],indexed[0][key])==canonical_timing(parsed[1],indexed[1][key]) for key in indexed[0]),
                            "same_shared_metadata":all(parsed[0].get(key)==parsed[1].get(key) for key in ["TITLE","SUBTITLE","ARTIST","MUSIC","BANNER","BACKGROUND","JACKET"])})
        except Exception as error:
            results.append({"left":left["path"],"right":right["path"],"error":str(error)})
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates",nargs="*",type=Path)
    parser.add_argument("--baseline",type=Path,default=BASELINE)
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--timing",type=Path,default=TIMING)
    parser.add_argument("--out",type=Path,default=Path(__file__).with_name("comparison.json"))
    parser.add_argument("--audio-onsets",action="store_true")
    parser.add_argument("--stance-span",type=float,default=2.25)
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    source_sha=sha(args.source)
    if source_sha!=timing["source_sha256"]:
        raise RuntimeError("Source audio hash differs from the measured timing report.")
    onset=make_onsets(args.source) if args.audio_onsets else None
    baseline=audit_file(args.baseline,timing,onset,args.stance_span)
    candidates=[audit_file(path,timing,onset,args.stance_span) for path in args.candidates]
    report={"source_audio":str(args.source), "source_sha256":source_sha,
            "duration_s":timing["duration_s"],"reference_bpm_range":timing["bpm_range"],
            "baseline":baseline,"candidates":candidates,
            "equivalent_export_checks":compare_exports([baseline]+candidates),
            "foot_model_assumptions":{"feet":2,"brackets":False,"held_panels_lock_assigned_foot":True,
                "maximum_stance_span_panel_units":args.stance_span,"maximum_double_movement_per_press_panel_units":2.83,
                "idle_foot_reposition_between_events":False,"all_valid_initial_stances_allowed":True,
                "objective":"Minimize consecutive same-foot singleton presses, then total travel. Reported speed is for that path; it is not a lower bound.",
                "forward_only_constraint":"Left foot x <= right foot x. Equal-x up/down swaps and body facing are not modeled.",
                "limitations":"No brackets, airborne reposition, heel/toe detail, facing/twists, mine avoidance, human fatigue, or actual pad playtest. A failed geometric search flags review; it does not prove a chart impossible."},
            "onset_proxy_method":onset["method"] if onset else None,
            "selection_guidance":"Reject changed audio/timing, broken holds, and >2 active panel demands first. Inspect conservative footwork failures and rapid repeats. Compare onset proxy, rests and section density within each difficulty, then repetition/diversity. Classic meters remain provisional until pad playtest."}
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"report":str(args.out),"baseline_status":baseline["status"],
                      "candidate_statuses":[{"path":c["path"],"status":c["status"]} for c in candidates]},indent=2))


if __name__=="__main__":
    main()
