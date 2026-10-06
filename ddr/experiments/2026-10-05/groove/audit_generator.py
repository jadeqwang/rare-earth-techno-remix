"""Independently audit official generated charts and exported footwork paths."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='fs')
import simfile
from simfile.notes import NoteData, NoteType
from simfile.notes.count import count_steps, count_holds, count_jumps
from simfile.timing import Beat, TimingData
from simfile.timing.engine import TimingEngine

COORDS = [(-1, 0), (0, -1), (0, 1), (1, 0), (2, 0), (3, -1), (3, 1), (4, 0)]


def load(path: Path):
    with path.open() as file:
        return simfile.load(file, strict=True)


def inspect_chart(song, chart, source_chart, telemetry: Path) -> dict:
    notes, original = list(NoteData(chart)), list(NoteData(source_chart))
    # Ignore panel identities; demand and hold timing must survive conversion.
    timeline = lambda ns: sorted((str(n.beat), str(n.note_type)) for n in ns)
    assert timeline(notes) == timeline(original), 'Conversion changed note demand/timing'
    groups = defaultdict(list)
    for note in notes:
        assert note.note_type in (NoteType.TAP, NoteType.HOLD_HEAD, NoteType.TAIL)
        groups[note.beat].append(note)
    active, holds, peak = {}, [], 0
    for beat, row in sorted(groups.items()):
        for note in row:
            if note.note_type == NoteType.TAIL:
                assert note.column in active, 'Orphan hold tail'
                start = active.pop(note.column)
                assert beat > start
                holds.append((float(start), float(beat)))
        presses = [note for note in row if note.note_type != NoteType.TAIL]
        peak = max(peak, len(active) + len(presses))
        assert peak <= 2, 'Over two simultaneous feet required'
        for note in presses:
            assert note.column not in active, 'Note inside active hold'
            if note.note_type == NoteType.HOLD_HEAD:
                active[note.column] = beat
    assert not active, 'Unclosed hold'
    nd = NoteData(chart)
    engine = TimingEngine(TimingData(song, chart))
    nodes = json.loads(telemetry.read_text())
    types, orientations = Counter(), Counter()
    bracket_nodes, crossover_nodes, inverted_nodes, footswap_nodes = [], [], [], []
    travel, stance, speeds, last_time, transitions = [], [], [], {}, []
    previous = None
    last_pad = None
    for node in nodes:
        beat = node['row'] / 48
        feet = [next(item for item in node['feet'] if item['foot'] == foot and item['portion'] == 0)
                for foot in range(2)]
        if any(item['portion'] == 1 and item['lane'] >= 0 for item in node['feet']):
            bracket_nodes.append(beat)
        moves = [item for item in node['feet'] if item['moving'] and item['action'] != 'Release']
        if moves:
            orientations[node['orientation']] += 1
        for item in moves:
            step = item['step'] or ''
            types[step] += 1
            if 'Crossover' in step: crossover_nodes.append(beat)
            if 'Invert' in step: inverted_nodes.append(beat)
            if 'FootSwap' in step: footswap_nodes.append(beat)
        valid = all(item['lane'] >= 0 for item in feet)
        if valid:
            positions = [COORDS[item['lane']] for item in feet]
            stance.append(math.dist(*positions))
            pad = feet[0]['lane'] // 4 if feet[0]['lane'] // 4 == feet[1]['lane'] // 4 else None
            if moves and pad is not None:
                if last_pad is not None and pad != last_pad:
                    transitions.append(beat)
                last_pad = pad
        if previous is not None:
            for move in moves:
                foot = move['foot']
                if move['portion'] != 0 or previous[foot]['lane'] < 0 or move['lane'] < 0: continue
                distance = math.dist(COORDS[previous[foot]['lane']], COORDS[move['lane']])
                travel.append(distance)
                time = float(engine.time_at(Beat(str(beat))))
                if foot in last_time and time > last_time[foot]:
                    speeds.append(distance / (time - last_time[foot]))
                last_time[foot] = time
        previous = feet
    rapid = {int(float(note.beat)) for note in notes if note.note_type != NoteType.TAIL
             and float(note.beat) % 1 in (0.25, 0.75)}
    cross_pad_bursts = []
    if chart['STEPSTYPE'] == 'dance-double':
        for unit in sorted(rapid):
            pads = {note.column // 4 for note in notes if note.note_type != NoteType.TAIL
                    and unit <= float(note.beat) < unit + 1}
            if len(pads) > 1: cross_pad_bursts.append(unit)
    return {
        'type': chart['STEPSTYPE'], 'difficulty': chart['DIFFICULTY'],
        'step_rows': count_steps(nd), 'holds': count_holds(nd), 'jumps': count_jumps(nd),
        'all_notes_preserved': True, 'complete_hold_pairs': True, 'max_simultaneous_feet': peak,
        'used_panels': sorted({note.column for note in notes}),
        'official_step_types': dict(types), 'official_orientations': dict(orientations),
        'bracket_beats': bracket_nodes, 'crossover_beats': sorted(set(crossover_nodes)),
        'inverted_beats': sorted(set(inverted_nodes)), 'footswap_beats': sorted(set(footswap_nodes)),
        'max_stance_panel_centers': max(stance, default=0),
        'max_foot_travel_panel_centers': max(travel, default=0),
        'max_foot_speed_panel_centers_per_second': max(speeds, default=0),
        'full_pad_transitions': len(transitions), 'full_pad_transition_beats': transitions,
        'sixteenth_burst_beats': len(rapid), 'sixteenth_cross_pad_beats': cross_pad_bursts,
        'footwork_source': str(telemetry.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    source = next((args.run / 'input').glob('*.sm'), None) or next((args.run / 'input').glob('*.ssc'))
    destination = args.run / 'output' / source.name
    original, generated = load(source), load(destination)
    assert original['OFFSET'] == generated['OFFSET'], 'Global offset changed'
    assert original['BPMS'] == generated['BPMS'], 'Global BPM map changed'
    config = json.loads((args.run / 'config.json').read_text())
    output_type = config['OutputChartType']
    latest = sorted((args.run / 'review/visualizations').iterdir())[-1]
    reports = []
    for chart in generated.charts:
        if chart['STEPSTYPE'] != output_type: continue
        source_chart = next(c for c in original.charts if c['STEPSTYPE'] == 'dance-single'
                            and c['DIFFICULTY'] == chart['DIFFICULTY'])
        telemetry = latest / f'{source.name}.{chart["DIFFICULTY"]}.footwork.json'
        reports.append(inspect_chart(generated, chart, source_chart, telemetry))
    assert reports, 'No converted charts found'
    report = {'timing_preserved_exactly': True, 'bpm_segments': len(generated['BPMS'].split(',')),
              'charts': reports}
    (args.run / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
