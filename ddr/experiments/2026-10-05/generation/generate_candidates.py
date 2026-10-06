"""Run the released ITGPT paper models against Rare Earth's measured beat map.

The upstream tempo detector is intentionally bypassed. Model outputs and raw
samples remain archived; only a separate playable candidate receives logged
hold/chord repairs. This script never writes to the original song folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path('/tmp/rare-earth-itgpt'))
    parser.add_argument('--models', type=Path)
    parser.add_argument('--seeds', nargs='+', type=int, default=[17, 29, 43])
    parser.add_argument('--levels', nargs='+', type=int, default=[3, 4, 6, 9])
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--threshold', type=float, default=.5)
    parser.add_argument('--temperature', type=float, default=1.)
    parser.add_argument('--top-p', type=float, default=.9)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[4]
    experiment = Path(__file__).resolve().parents[1]
    out = experiment / 'candidates'
    out.mkdir(parents=True, exist_ok=True)
    cache = experiment / 'generation/cache'
    cache.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.repo))
    import numpy as np
    import torch
    sys.path.insert(0, str(experiment / 'itgpt'))
    from load_models import load_models
    from util import (create_analyzers, extract_mel_feats,
                      make_onset_feature_context_range,
                      make_onset_feature_context, unravel_onehot)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    device = torch.device('cpu')
    models = args.models or args.repo / 'trained_models'
    onset_path = models / 'onset_paper.pt'
    sym_path = models / 'sym_paper.pt'
    if models != args.repo / 'trained_models':
        raise ValueError('Use the verified paper checkpoints in the repo trained_models directory')
    onset_model, sym_model = load_models(device=device, repo=args.repo)
    timing_path = project / 'ddr/analysis/timing.json'
    timing = json.loads(timing_path.read_text())
    audio = project / 'audio/Rare_Earth_DDR.mp3'
    assert sha256(audio) == timing['source_sha256']
    grid = np.array([b['time_s'] for b in timing['beats']], dtype=float)
    # Include a boundary for the last beat's feature window. Export remains
    # confined to notes and releases before the original audio endpoint.
    boundaries = np.r_[grid, grid[-1] + 60 / timing['bpms'][-1]['bpm']]
    feature_path = cache / 'audio-features.npy'
    if feature_path.exists():
        feats = np.load(feature_path)
    else:
        print('Extracting model audio features', flush=True)
        feats = extract_mel_feats(str(audio), create_analyzers(nhop=441), nhop=441)
        np.save(feature_path, feats)
    beat_contexts = np.array([
        make_onset_feature_context_range(feats, boundaries[i], boundaries[i+1], frame_density=32)
        for i in range(len(grid))
    ])
    beat_contexts = (beat_contexts - beat_contexts.mean(0)) / (beat_contexts.std(0) + 1e-6)
    # Symbolic training normalizes over the song per frequency/channel. The
    # same normalization is used here instead of feeding unnormalized values.
    symbolic_feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-6)
    chunk_segments = []
    for start in range(0, len(grid), 64):
        end = min(start + 64, len(grid))
        if len(grid) - end < 50 and end < len(grid):
            end = len(grid)
        chunk_segments.append((start, end))
        if end == len(grid):
            break
    labels = {3:('Beginner','Beginner',3),4:('Easy','Easy',4),6:('Standard','Medium',6),9:('Heavy','Hard',9)}
    baseline_file = experiment / 'baseline/Rare Earth (Techno Remix).sm'
    original_header = baseline_file.read_text().split('#NOTES:')[0]
    # Generation credits and subtitle differ; audio and timing remain literal
    # copies of the original SM header.
    header = original_header.replace('#CREDIT:Codex;', '#CREDIT:ITGPT + Codex;')
    metadata = dict(
        source_audio_sha256=sha256(audio), timing_sha256=sha256(timing_path),
        onset_checkpoint_sha256=sha256(onset_path), symbolic_checkpoint_sha256=sha256(sym_path),
        model='ITGPT released paper checkpoints', threshold=args.threshold,
        temperature=args.temperature, top_p=args.top_p, threads=args.threads,
        inference_device='cpu', symbolic_audio_normalization='per-song frequency/channel mean and std, matching training',
        upstream_repository='https://github.com/miguelomalley/ITGPT',
        tempo_handling='Original 71 BPM segments and measured beat times; bypass upstream constant-tempo detector',
        onset_chunk_segments=chunk_segments,
    )
    # Use >=50-beat chunks with their average tempo as described by the paper;
    # all feature times still use the exact changing-tempo grid.
    for level in args.levels:
        name, difficulty, meter = labels[level]
        onset_cache = cache / f'onsets-{level}.npz'
        if onset_cache.exists():
            loaded = np.load(onset_cache)
            probabilities = loaded['probabilities']
        else:
            probabilities = []
            for start, end in chunk_segments:
                bpm = 60 / float(np.mean(np.diff(boundaries[start:end+1])))
                x = torch.tensor(beat_contexts[start:end], dtype=torch.float32, device=device).unsqueeze(0)
                with torch.inference_mode():
                    # Return probability estimates as well as hard decisions.
                    outputs = onset_model(x, bpm, level)
                    logits = outputs['onset_logits'] if isinstance(outputs, dict) else outputs[0]
                    probabilities.append(torch.sigmoid(logits).squeeze(0).cpu().numpy())
                print(f'{name}: onset beats {start}-{end}', flush=True)
            probabilities = np.concatenate(probabilities)
            np.savez_compressed(onset_cache, probabilities=probabilities)
        positions = []
        for i, row in enumerate(probabilities):
            for j, probability in enumerate(row):
                beat = i + j / len(row)
                when = boundaries[i] + (boundaries[i+1]-boundaries[i])*j/len(row)
                if probability > args.threshold and beat >= 8 and when < timing['duration_s']-.08:
                    positions.append((beat, when, float(probability)))
        beats = np.array([p[0] for p in positions])
        audio_contexts = np.array([make_onset_feature_context(symbolic_feats,int(p[1]*100),20) for p in positions])
        deltas = np.array([(0 if i==0 else round(beats[i]-beats[i-1],2),
                            0 if i+1==len(beats) else round(beats[i+1]-beats[i],2)) for i in range(len(beats))])
        audio_tensor = torch.tensor(audio_contexts,dtype=torch.float32,device=device).unsqueeze(0)
        aux_tensor = torch.tensor(deltas,dtype=torch.float32,device=device).unsqueeze(0)
        with torch.inference_mode():
            encoded = sym_model.encode_audio(audio_tensor, aux_tensor)
        for seed in args.seeds:
            stem = f'{name.lower()}-seed-{seed}'
            report_path = out / f'{stem}.json'
            if report_path.exists():
                print(f'{stem}: already saved', flush=True)
                continue
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            begun = time.monotonic()
            done = 0
            def progress(n):
                nonlocal done
                done += n
                if done % 50 == 0:
                    print(f'{stem}: {done}/{len(beats)} sampled steps ({time.monotonic()-begun:.1f}s)',flush=True)
            with torch.inference_mode():
                tokens = sym_model.generate(
                    aux_steps=aux_tensor, max_len=len(beats), temperature=args.temperature,
                    top_p=args.top_p, preencoded_audio=encoded, device=device,
                    progress_callback=progress)
            rows = {int(round(beat*48)):unravel_onehot(int(tok),4) for beat,tok in zip(beats,tokens)}
            note_text = serialize(rows, len(grid), 4)
            chart_header = f'\n#NOTES:\ndance-single:\n{name} Single - ITGPT seed {seed}:\n{difficulty}:\n{meter}:\n0,0,0,0,0:\n'
            (out/f'{stem}-raw.sm').write_text(header+chart_header+note_text+';\n')
            clean, repairs = repair_rows(rows, len(grid), timing['duration_s'], boundaries)
            (out/f'{stem}.sm').write_text(header+chart_header+serialize(clean,len(grid),4)+';\n')
            report = dict(**metadata, seed=seed, conditioned_difficulty=level,
                          chart_name=name, model_onset_rows=len(beats),
                          generation_seconds=round(time.monotonic()-begun,3),
                          raw_tokens=[dict(beat=float(b),time_s=float(t),onset_probability=p,token=int(tok),row=unravel_onehot(int(tok),4))
                                      for (b,t,p),tok in zip(positions,tokens)],
                          repairs=repairs, raw_sm=f'{stem}-raw.sm', candidate_sm=f'{stem}.sm')
            report_path.write_text(json.dumps(report,indent=2)+'\n')
            print(f'{stem}: saved, repairs={len(repairs)}, elapsed={report["generation_seconds"]}s',flush=True)


def serialize(rows, beat_count, columns):
    measures=[]
    for m in range(math.ceil(beat_count/4)):
        measures.append('\n'.join(rows.get(m*192+i,'0'*columns) for i in range(192)))
    return ',\n'.join(measures)


def repair_rows(raw, beat_count, duration, boundaries):
    """Log syntax/hold/chord repairs; do not invent rhythmic patterns."""
    rows={}; active={}; changes=[]
    for tick,original in sorted(raw.items()):
        row=list(original)
        for c,x in enumerate(row):
            if x=='3':
                if c in active:
                    del active[c]
                else:
                    row[c]='0';changes.append(dict(tick=tick,column=c,from_note=x,to_note='0',reason='orphan hold tail'))
            elif x in '12' and c in active:
                row[c]='0';changes.append(dict(tick=tick,column=c,from_note=x,to_note='0',reason='press inside active hold'))
        presses=[c for c,x in enumerate(row) if x in '12']
        # Release retained holds before a jump would require a third foot.
        if len(active)+len(presses)>2 and active:
            release_tick=tick-1
            prior=list(rows.get(release_tick,'0000'))
            for c in list(active):
                if release_tick>active[c] and prior[c]=='0':
                    prior[c]='3';del active[c]
                    changes.append(dict(tick=release_tick,column=c,from_note='0',to_note='3',reason='release before third-foot demand'))
            rows[release_tick]=''.join(prior)
        for c in presses[max(0,2-len(active)):]:
            old=row[c];row[c]='0'
            changes.append(dict(tick=tick,column=c,from_note=old,to_note='0',reason='reduce three/four-panel chord to two-foot demand'))
        for c,x in enumerate(row):
            if x=='2':active[c]=tick
        if any(x!='0' for x in row): rows[tick]=''.join(row)
    # A hold without a model-generated tail ends at the last exported grid tick
    # before audio ends. This remains explicit in the repair log for review.
    final_tick=beat_count*48-1
    while final_tick>0:
        beat=final_tick/48
        i=int(beat)
        t=boundaries[i]+(boundaries[i+1]-boundaries[i])*(beat-i)
        if t<duration-.02:break
        final_tick-=1
    for c,head in active.items():
        row=list(rows.get(final_tick,'0000'))
        if head<final_tick and row[c]=='0':
            row[c]='3';rows[final_tick]=''.join(row)
            changes.append(dict(tick=final_tick,column=c,from_note='0',to_note='3',reason='close model hold before audio endpoint'))
        else:
            row=list(rows[head]);row[c]='1';rows[head]=''.join(row)
            changes.append(dict(tick=head,column=c,from_note='2',to_note='1',reason='unclosable final hold converted to tap'))
    return rows,changes


if __name__=='__main__':
    main()
