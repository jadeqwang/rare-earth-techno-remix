"""Package the reviewed ITGPT singles and official generated doubles separately."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import warnings
import zipfile

warnings.filterwarnings('ignore',category=UserWarning,module='fs')
import simfile
from simfile.notes import NoteData, NoteType
from simfile.notes.count import count_steps, count_jumps, count_holds

EXPERIMENT = Path(__file__).resolve().parents[1]
PROJECT = Path(__file__).resolve().parents[4]
RELEASE = EXPERIMENT / 'release'
SONG = RELEASE / 'Songs/Rare Earth Model Pack/Rare Earth (Techno Remix - Model Edition)'
SELECTION = dict(Beginner='beginner-seed-43', Easy='easy-seed-29', Medium='standard-seed-29', Hard='heavy-seed-43')
NAMES = dict(Beginner='Beginner',Easy='Easy',Medium='Standard',Hard='Heavy')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = EXPERIMENT / 'groove/selected-model-doubles/output/model-singles.sm'
    with source.open() as handle:
        sim = simfile.load(handle, strict=True)
    expected={(kind,level) for kind in ['dance-single','dance-double'] for level in SELECTION}
    assert {(c['STEPSTYPE'],c['DIFFICULTY']) for c in sim.charts}==expected
    assert len(sim.charts)==8
    SONG.mkdir(parents=True,exist_ok=True)
    baseline = EXPERIMENT / 'baseline'
    for filename in ['Rare_Earth_DDR.mp3','banner.png','jacket.png','background.jpg']:
        shutil.copy2(baseline/filename,SONG/filename)
    original = (baseline/'Rare Earth (Techno Remix).sm').read_text()
    header=original.split('#NOTES:',1)[0]
    header=header.replace('#SUBTITLE:(Techno Remix);','#SUBTITLE:(Techno Remix - Model Edition);')
    header=header.replace('#CREDIT:Codex;','#CREDIT:ITGPT paper models + GrooveAuthor + Codex;')
    sm=header
    ssc='#VERSION:0.83;\n'+header+'#TIMESIGNATURES:0=4=4;\n#TICKCOUNTS:0=4;\n'
    ssc+='#LABELS:8=VERSE 1,40=VERSE 2,88=BUILD,120=DROP 1,168=CHORUS,200=VERSE RETURN,248=FINAL DROP,276=OUTRO;\n'
    report=[]
    for kind in ['dance-single','dance-double']:
        for i,difficulty in enumerate(SELECTION):
            chart=next(c for c in sim.charts if c['STEPSTYPE']==kind and c['DIFFICULTY']==difficulty)
            name=f'{NAMES[difficulty]} {"Single" if kind=="dance-single" else "Double"}'
            meter=([3,4,6,9] if kind=='dance-single' else [3,5,7,10])[i]
            credit='ITGPT paper models' if kind=='dance-single' else 'ITGPT rhythms + GrooveAuthor footwork'
            notes=chart['NOTES'].strip()
            if kind=='dance-single':
                with (EXPERIMENT/'candidates'/f'{SELECTION[difficulty]}.sm').open() as handle:
                    learned=simfile.load(handle,strict=True).charts[0]
                signature=lambda c:[(str(n.beat),n.column,n.note_type) for n in NoteData(c)]
                assert signature(chart)==signature(learned),f'Single arrows changed in {name}'
            sm+=f'\n#NOTES:\n{kind}:\n{name}:\n{difficulty}:\n{meter}:\n0,0,0,0,0:\n{notes};\n'
            ssc+=f'\n#NOTEDATA:;\n#CHARTNAME:{name};\n#STEPSTYPE:{kind};\n#DESCRIPTION:{name};\n#DIFFICULTY:{difficulty};\n#METER:{meter};\n#CREDIT:{credit};\n#RADARVALUES:0,0,0,0,0;\n#NOTES:\n{notes};\n'
            nd=NoteData(chart)
            candidate=json.loads((EXPERIMENT/'candidates'/f'{SELECTION[difficulty]}.json').read_text())
            report.append(dict(name=name,type=kind,difficulty=difficulty,meter=meter,
                               step_rows=count_steps(nd),jumps=count_jumps(nd),holds=count_holds(nd),
                               source_candidate=SELECTION[difficulty],seed=candidate['seed'],
                               conditioned_difficulty=candidate['conditioned_difficulty'],
                               model_repairs=candidate['repairs'],credit=credit))
    stem='Rare Earth (Techno Remix - Model Edition)'
    (SONG/f'{stem}.sm').write_text(sm)
    (SONG/f'{stem}.ssc').write_text(ssc)
    # Assert exact literal timing copied from the original validated export.
    for tag in ['BPMS','OFFSET']:
        value=lambda text:re.search(r'#'+tag+r':(.*?);',text,re.S).group(1)
        assert value(original)==value(sm)==value(ssc)
    timing=json.loads((PROJECT/'ddr/analysis/timing.json').read_text())
    assert sha(SONG/'Rare_Earth_DDR.mp3')==timing['source_sha256']
    provenance=dict(
        edition='Rare Earth Techno Remix - Model Edition',original_pack_unchanged=True,
        source_audio_sha256=timing['source_sha256'],timing_sha256=sha(PROJECT/'ddr/analysis/timing.json'),
        timing_method='Original measured grid, all 71 BPM segments and offset copied exactly',
        model_repository='https://github.com/miguelomalley/ITGPT',
        model_checkpoints='https://huggingface.co/miguelomalley/ITGPT/tree/main',
        model_setup=json.loads((EXPERIMENT/'itgpt/setup_report.json').read_text()),
        checkpoints={k:v for k,v in json.loads((EXPERIMENT/'candidates/beginner-seed-43.json').read_text()).items() if 'checkpoint_sha256' in k},
        selection='Three symbolic seeds per difficulty; selected by independent timing, hold, footwork and repetition audit',
        doubles_generator='Official PerryAsleep StepManiaChartGenerator / StepManiaLibrary',
        doubles_config='groove/selected-model-doubles/config.json (archived in experiment)',
        difficulty_scale='Provisional classic DDR scale; physical pad playtest pending',
        limitations='Model-generated drafts with software audit and autoplay previews. No physical pad playtest; no verified game-engine launch.',
        charts=report,
    )
    (SONG/'MODEL_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    rows='\n'.join(f"{c['name']:<18} meter {c['meter']:>2}   {c['step_rows']:>3} rows   {c['holds']:>2} holds   {c['jumps']:>2} jumps" for c in report)
    (SONG/'README.txt').write_text(f'''RARE EARTH (TECHNO REMIX) — MODEL EDITION

Music: Robot Ninja Apocalypse; written by Jade Q Wang and Charlie van Norman.
Singles: released ITGPT paper checkpoints, adapted by Codex to the existing beat grid.
Doubles: official GrooveAuthor generation library via StepManiaChartGenerator.

INSTALLATION
Extract Rare_Earth_Model_Edition_Step_Pack.zip into StepMania's Songs folder.
Reload songs/restart, then choose Rare Earth Model Pack. This is a separate
edition so it can be installed alongside the original Rare Earth Pack.
SM targets StepMania 3.9; SSC targets StepMania 5. Both contain identical notes.

CHARTS — provisional classic DDR meters
{rows}

TIMING AND VALIDATION
Original 2:07.960 MP3, unchanged; gradual acceleration 129.143–135.793 BPM.
All 71 BPM segments and the -0.0611 offset are preserved.
All singles retain the selected model's arrows. Easy's final hold required
one explicit tail at the audio endpoint. The other three selected singles
required no syntax, chord or hold repairs.
Doubles preserve the learned rhythms and hold durations while generating
new panel placement with footwork and travel controls.
Physical pad playtesting remains pending. Software geometry and difficulty
meters do not establish human comfort or enjoyment.

MODEL_PROVENANCE.json records sources, checkpoints, seeds and repairs.
''')
    archive=RELEASE/'Rare_Earth_Model_Edition_Step_Pack.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in sorted((RELEASE/'Songs').rglob('*')):
            if path.is_file():bundle.write(path,path.relative_to(RELEASE/'Songs'))
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist())==8
    (RELEASE/'chart-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(archive)
    print(rows)


if __name__=='__main__':
    main()
