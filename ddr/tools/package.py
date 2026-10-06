"""Bundle only the playable two-level Songs hierarchy, then check the ZIP."""
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SONGS = ROOT / "Songs"
OUT = ROOT / "Rare_Earth_DDR_Step_Pack.zip"
report = json.loads((ROOT / "analysis/validation.json").read_text())
assert report["status"] == "passed"
assert report["charts"] == 8 and report["levels_per_mode"] == 4
with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(SONGS.rglob("*")):
        if p.is_file():
            z.write(p,p.relative_to(SONGS))
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert len(names) == 7
    assert all(len(Path(n).parts) == 3 for n in names)
    assert sum(n.endswith(".ssc") for n in names) == 1
    assert sum(n.endswith(".sm") for n in names) == 1
    assert sum(n.endswith(".mp3") for n in names) == 1
print(f"Verified {OUT} ({OUT.stat().st_size:,} bytes)")
print("\n".join(names))
