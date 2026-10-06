"""Assert final pack completeness, selected-note preservation, and ZIP payload."""
import json
import hashlib
from pathlib import Path
import zipfile
from compare import ROOT, BASELINE, note_signature, sha
import simfile

experiment=Path(__file__).resolve().parents[1]
release=experiment/"release"
report_path=release/"validation.json"
report=json.loads(report_path.read_text())
expected={(mode,level) for mode in ["dance-single","dance-double"] for level in ["Beginner","Easy","Medium","Hard"]}
checks={}

def release_song_path(file_report):
    # Archived reports record the generation checkout's absolute paths. Resolve
    # the same export inside this checkout so review works after cloning.
    matches=list((release/"Songs").rglob(Path(file_report["path"]).name))
    assert len(matches)==1, (file_report["path"],matches)
    return matches[0]

for file_report in report["candidates"]:
    assert file_report["status"]=="passed",file_report
    charts=file_report["charts"]
    assert len(charts)==8
    assert {(c["type"],c["difficulty"]) for c in charts}==expected
    assert all(not c["errors"] and c["max_simultaneous_panel_demand"]<=2 and c["holds"]+c["rolls"]==c["complete_hold_pairs"] for c in charts)
    assert all(c["foot_assignment"]["forward_only"]["feasible"] for c in charts)
    assert all(c["foot_assignment"]["forward_only"]["chosen_assignment_rapid_same_foot_singletons"]==0 for c in charts)
    assert all(c["used_columns"]==list(range(4 if c["type"]=="dance-single" else 8)) for c in charts)
    assert all(p["meters_strictly_increase"] and p["rows_strictly_increase"] and p["peaks_do_not_decrease"] for p in file_report["progression"])
    path=release_song_path(file_report)
    assert sha(path)==file_report["file_sha256"]
    with path.open() as handle:
        sim=simfile.load(handle,strict=True)
    assert all((path.parent/sim[key]).is_file() for key in ["MUSIC","BANNER","BACKGROUND","JACKET"])
checks["eight_expected_difficulty_slots_per_export"]=True
checks["all_holds_complete_and_at_most_two_panel_demands"]=True
checks["all_panel_columns_used"]=True
checks["meters_rows_and_peak_density_progress"]=True
checks["bounded_two_foot_assignments_exist_for_all_charts"]=True
checks["no_rapid_same_foot_repeats_in_selected_assignments"]=True
checks["all_referenced_audio_and_art_assets_exist"]=True
for pair in report["equivalent_export_checks"]:
    assert all(pair[key] for key in ["same_chart_keys","same_note_events","same_chart_meters","same_effective_timing","same_shared_metadata"])
checks["sm_ssc_normalized_note_events_timing_meters_and_metadata_equal"]=True
with release_song_path(report["candidates"][0]).open() as handle:
    exported=simfile.load(handle,strict=True)
index={(c["STEPSTYPE"],c["DIFFICULTY"]):c for c in exported.charts}
seeds={"Beginner":("beginner",43),"Easy":("easy",29),"Medium":("standard",29),"Hard":("heavy",43)}
for difficulty,(stem,seed) in seeds.items():
    with (experiment/"candidates"/f"{stem}-seed-{seed}.sm").open() as handle:
        candidate=simfile.load(handle,strict=True)
    assert note_signature(index[("dance-single",difficulty)])==note_signature(candidate.charts[0])
with (experiment/"groove/selected-model-doubles/output/model-singles.sm").open() as handle:
    groove=simfile.load(handle,strict=True)
for chart in groove.charts:
    if chart["STEPSTYPE"]=="dance-double":
        assert note_signature(chart)==note_signature(index[("dance-double",chart["DIFFICULTY"])])
checks["released_singles_equal_selected_model_candidates"]=True
checks["released_doubles_equal_grooveauthor_generated_notes"]=True
initial=json.loads((experiment/"review/baseline-audit.json").read_text())
assert sha(BASELINE)==initial["baseline"]["file_sha256"]
assert sha(BASELINE.with_suffix(".sm"))==sha(experiment/"baseline/Rare Earth (Techno Remix).sm")
checks["original_sm_ssc_unchanged"]=True
archive=release/"Rare_Earth_Model_Edition_Step_Pack.zip"
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for file_report in report["candidates"]:
        relative=release_song_path(file_report).relative_to(release/"Songs").as_posix()
        assert hashlib.sha256(z.read(relative)).hexdigest()==file_report["file_sha256"]
    audio_names=[name for name in z.namelist() if name.endswith("Rare_Earth_DDR.mp3")]
    assert len(audio_names)==1
    assert hashlib.sha256(z.read(audio_names[0])).hexdigest()==report["source_sha256"]
checks["zip_crc_and_song_exports_and_audio_payload_match"]=True
checks["physical_pad_playtest_performed"]=False
report["release_checks"]=checks
report["status"]="passed"
report["review_limitations"]="Programmatic timing, hold and bounded two-foot geometry review plus a coarse spectral-onset proxy. Classic meters are provisional. No physical pad playtest was performed. Geometric feasibility does not prove body-facing correctness, comfort, fatigue, or musical enjoyment."
report_path.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"status":report["status"],"release_checks":checks},indent=2))
