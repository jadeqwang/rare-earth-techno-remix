"""Submit / collect / score Seedance 2.5 base clips.

  python3 run_seedance.py submit [shot_id ...]   # submit missing takes (all shots if none given)
  python3 run_seedance.py collect                # download finished clips, score lip sync
  python3 run_seedance.py status
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync"))
import gen  # noqa: E402
from seedance_shots import SHOTS, STYLE  # noqa: E402

WORK = "/tmp/work/sd/prod"
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seedance_manifest.json")
AUDIO = {"voc": "/tmp/work/vocals.wav", "inst": "/tmp/work/inst.wav", "mix": "/tmp/work/song.wav"}


import fcntl
from contextlib import contextmanager


@contextmanager
def locked():
    """Exclusive lock for read-modify-write of the manifest (submit and the collector run concurrently)."""
    with open(MANIFEST + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def load():
    return json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}


def save(m):
    tmp = MANIFEST + ".tmp"
    json.dump(m, open(tmp, "w"), indent=1)
    os.replace(tmp, MANIFEST)


def update_take(sid, job, **fields):
    with locked():
        m = load()
        for t in m[sid]["takes"]:
            if t["job"] == job:
                t.update(fields)
        save(m)


def cut_audio(kind, t0, dur):
    os.makedirs(WORK, exist_ok=True)
    out = f"{WORK}/ref_{kind}_{t0:07.3f}_{dur}.mp3"
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0}", "-t", f"{dur}", "-i", AUDIO[kind],
                        "-ac", "2", "-ar", "44100", "-b:a", "192k", out], check=True)
    return out


def build_input(s):
    inp = {"prompt": s["prompt"] + STYLE, "duration": s["dur"], "resolution": "720p", "aspect_ratio": "16:9",
           "fps": 24, "generate_audio": False, "camera_fixed": False, "watermark": False, "output_format": "mp4",
           "use_virtual_avatar": False}
    if s["refs"]:
        inp["reference_images"] = [gen.data_uri(p) for p in s["refs"]]
    if s["audio"]:
        inp["reference_audios"] = [gen.data_uri(cut_audio(s["audio"], s["t0"], s["dur"]))]
    return inp


def submit(ids, extra=0):
    for s in SHOTS:
        if ids and s["id"] not in ids:
            continue
        with locked():
            m = load()
            entry = m.setdefault(s["id"], {"spec": {}, "takes": []})
            entry["spec"] = {k: v for k, v in s.items() if k != "refs"}
            live = [t for t in entry["takes"] if t.get("state") not in ("error",)]
            need = max(0, s["takes"] - len(live)) + extra
            save(m)
        for k in range(need):
            jid = gen.submit("bytedance/seedance-2.5", build_input(s), tag=s["id"])
            with locked():
                m = load()
                m[s["id"]]["takes"].append({"job": jid, "state": "submitted", "ts": time.time()})
                save(m)
            print("submitted", s["id"], jid, flush=True)


def collect():
    import mouth
    import score as sc
    with locked():
        m = load()
    for sid, entry in m.items():
        spec = entry["spec"]
        for i, t in enumerate(entry["takes"]):
            if t.get("state") in ("done", "error"):
                continue
            try:
                rec = gen.poll(t["job"])
            except Exception as e:  # noqa: BLE001
                print("poll failed", sid, e, flush=True); continue
            if rec is None:
                continue
            if rec.get("state") != "done":
                update_take(sid, t["job"], state="error", error=json.dumps(rec)[:800])
                print("ERROR", sid, t["job"], json.dumps(rec)[:300], flush=True)
                continue
            if rec.get("via") == "webhook" and "media" not in rec and time.time() * 1000 - rec.get("t1", 0) < 180000:
                continue  # relay is still mirroring the video into KV
            try:
                path = gen.fetch_media(t["job"], rec, f"{WORK}/{sid}__{t['job'].split('-')[-1]}")
            except Exception as e:  # noqa: BLE001
                print("fetch failed", sid, e, flush=True); continue
            t["file"] = path[0] if path else None
            t["state"] = "done" if t["file"] else "error"
            if t["file"] and spec.get("audio") == "voc":
                try:
                    mj = t["file"].replace(".mp4", "_mouth.json")
                    r = mouth.track(t["file"])
                    json.dump(r, open(mj, "w"))
                    if r["hit"] < 0.3:
                        raise ValueError(f"face found in only {r['hit']:.0%} of frames (profile/wide shot) - review visually")
                    s = sc.score(r, "/tmp/work/vocals.wav", spec["t0"], max_lag=0.35)
                    t["sync"] = {"hit": round(r["hit"], 3), "lag": s["best_lag_s"], "corr": s["best_corr"], "corr0": s["corr_at_0"]}
                except Exception as e:  # noqa: BLE001
                    t["sync"] = {"error": str(e)}
            print("done", sid, t.get("file"), t.get("sync"), flush=True)
            update_take(sid, t["job"], **{k: t[k] for k in ("file", "state", "sync") if k in t})


def status():
    with locked():
        m = load()
    for sid, entry in m.items():
        print(sid, [(t["state"], t.get("sync")) for t in entry["takes"]])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "submit":
        submit(sys.argv[2:])
    elif cmd == "collect":
        collect()
    else:
        status()
