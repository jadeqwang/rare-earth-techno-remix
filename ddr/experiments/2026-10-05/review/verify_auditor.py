"""Focused in-memory rejection checks for exported-chart requirements."""
import json
from pathlib import Path
import simfile
from compare import BASELINE, ROOT, summarize_chart

timing=json.loads((ROOT/"analysis/timing.json").read_text())
header=BASELINE.with_suffix(".sm").read_text().split("#NOTES:")[0]

def check(rows):
    sim=simfile.loads(header+"\n#NOTES:dance-single:Audit:Easy:4:0,0,0,0,0:\n"+"\n".join(rows)+";\n",strict=True)
    return summarize_chart(sim,sim.charts[0],timing,None,2.25)

good=check(["1000","0001","0100","0010"])
assert good["status"]=="passed", good
orphan=check(["3000","0000","0000","0000"])
assert any("Orphan" in e for e in orphan["errors"]), orphan
unclosed=check(["2000","0000","0000","0000"])
assert any("Unclosed" in e for e in unclosed["errors"]), unclosed
three=check(["1110","0000","0000","0000"])
assert any("Needs 3" in e for e in three["errors"]), three
inside=check(["2000","1000","3000","0000"])
assert any("inside active hold" in e for e in inside["errors"]), inside
third_hold=check(["2000","0110","3000","0000"])
assert any("Needs 3" in e for e in third_hold["errors"]), third_hold
sim=simfile.loads(header.replace("#OFFSET:-0.0611000;","#OFFSET:0;")+"\n#NOTES:dance-single:Audit:Easy:4:0,0,0,0,0:\n1000\n0000\n0000\n0000;\n",strict=True)
changed=summarize_chart(sim,sim.charts[0],timing,None,2.25)
assert any("timing" in e.lower() for e in changed["errors"]),changed
print("Passed: valid chart; orphan/unclosed hold; three-panel chord; third-foot hold demand; press inside hold; changed offset.")
