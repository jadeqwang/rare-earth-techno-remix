"""Generation client for the Rare Earth remix pipeline.

All traffic goes to api.cloudflare.com (the only reachable Cloudflare host from the sandbox).
Long jobs run as AI Gateway background runs whose webhook lands in the relay Worker
(pipeline/relay/relay_worker.js), which writes results into KV; we poll KV here.

Usage:
    from gen import submit, wait, fetch_media
    jid = submit("bytedance/seedance-2.5", {...}, tag="shot12")
    rec = wait(jid)
    paths = fetch_media(jid, rec, "out/shot12")
"""
import base64
import json
import mimetypes
import os
import sys
import time
import uuid
import urllib.request
import urllib.error

ACC = "78885e7db58a4c34423a7e62c8471b75"
NS = "3b9378c43d144959bee96654397fa40e"
API = f"https://api.cloudflare.com/client/v4/accounts/{ACC}"
RELAY = "https://rare-earth-remix-relay.jadewang.workers.dev"
SECRET_FILE = os.environ.get(
    "RELAY_SECRET_FILE",
    "/tmp/claude-0/-home-user-rare-earth-techno-remix/50721f55-bfba-55f7-80f0-cb98bf267d0d/scratchpad/hook_secret",
)
LEDGER = os.environ.get("GEN_LEDGER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.jsonl"))


def _req(method, url, data=None, headers=None, timeout=60, raw=False):
    headers = dict(headers or {})
    body = None
    if data is not None:
        if isinstance(data, (bytes, bytearray)):
            body = data
        else:
            body = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return (r.status, b) if raw else (r.status, json.loads(b.decode() or "null"))
    except urllib.error.HTTPError as e:
        b = e.read()
        if raw:
            return e.code, b
        try:
            return e.code, json.loads(b.decode())
        except Exception:
            return e.code, {"raw": b[:2000].decode(errors="replace")}


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if path.endswith(".mp3"):
        mime = "audio/mpeg"
    elif path.endswith(".wav"):
        mime = "audio/wav"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def _ledger(entry):
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **entry}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _summarize_input(inp):
    out = {}
    for k, v in inp.items():
        if isinstance(v, str) and v.startswith("data:"):
            out[k] = f"<data {len(v)//1024}KB>"
        elif isinstance(v, list):
            out[k] = [f"<data {len(x)//1024}KB>" if isinstance(x, str) and x.startswith("data:") else x for x in v]
        else:
            out[k] = v
    return out


def run_sync(model, inp, timeout=28):
    """Direct call for fast models (< ~28 s)."""
    st, d = _req("POST", f"{API}/ai/run", {"model": model, "input": inp}, timeout=timeout)
    _ledger({"kind": "sync", "model": model, "input": _summarize_input(inp), "status": st})
    return st, d


def submit(model, inp, tag="", job_id=None):
    """Background run; result arrives via webhook into KV res:<job_id>."""
    secret = open(SECRET_FILE).read().strip()
    job_id = job_id or f"{tag + '-' if tag else ''}{uuid.uuid4().hex[:10]}"
    body = {"model": model, "input": inp,
            "options": {"background": True, "webhookUrl": f"{RELAY}/hook/{secret}/{job_id}"}}
    st, d = _req("POST", f"{API}/ai/run", body, timeout=60)
    _ledger({"kind": "bg", "job": job_id, "model": model, "input": _summarize_input(inp), "status": st,
             "resp": d})
    if st not in (200, 202) or not (d or {}).get("success", False):
        raise RuntimeError(f"submit failed {st}: {json.dumps(d)[:1500]}")
    return job_id


def submit_cron(model, inp, tag="", job_id=None, delay_min=2):
    """Fallback: queue for the relay's cron runner (runs ~delay_min minutes from now)."""
    job_id = job_id or f"{tag + '-' if tag else ''}{uuid.uuid4().hex[:10]}"
    bucket = int(time.time() // 60) + delay_min
    key = f"job:{bucket}:{job_id}"
    st, d = _req("PUT", f"{API}/storage/kv/namespaces/{NS}/values/{key}",
                 json.dumps({"model": model, "input": inp}).encode(), {"Content-Type": "application/json"}, timeout=60)
    _ledger({"kind": "cron", "job": job_id, "model": model, "input": _summarize_input(inp), "status": st})
    if st != 200:
        raise RuntimeError(f"kv put failed {st}: {d}")
    return job_id


def kv_get(key, raw=False, timeout=120):
    st, b = _req("GET", f"{API}/storage/kv/namespaces/{NS}/values/{key}", timeout=timeout, raw=True)
    if st == 404:
        return None
    if st != 200:
        raise RuntimeError(f"kv get {key} -> {st}: {b[:300]}")
    return b if raw else json.loads(b.decode())


def poll(job_id):
    return kv_get(f"res:{job_id}")


def wait(job_id, timeout=1800, every=10, quiet=False):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rec = poll(job_id)
        if rec is not None:
            # webhook path mirrors media asynchronously; give it a moment to land
            if rec.get("via") == "webhook" and rec.get("state") == "done" and "media" not in rec:
                time.sleep(5)
                rec = poll(job_id) or rec
            return rec
        if not quiet:
            print(f"  .. waiting {job_id} {int(time.time()-t0)}s", file=sys.stderr, flush=True)
        time.sleep(every)
    raise TimeoutError(job_id)


def media_urls(r):
    out = []

    def visit(v):
        if not v:
            return
        if isinstance(v, str):
            if v.startswith("http"):
                out.append(v)
        elif isinstance(v, list):
            for x in v:
                visit(x)
        elif isinstance(v, dict):
            for k in ("video", "image", "images", "audio", "result", "output"):
                visit(v.get(k))

    visit(r)
    return list(dict.fromkeys(out))


def result_of(rec):
    if rec.get("via") == "webhook":
        return (rec.get("payload") or {}).get("result")
    return rec.get("result")


def fetch_media(job_id, rec, dest_prefix):
    """Download each output media file; prefer the KV mirror, fall back to the presigned URL."""
    paths = []
    os.makedirs(os.path.dirname(dest_prefix) or ".", exist_ok=True)
    media = rec.get("media") or []
    if not media:
        media = [{"url": u} for u in media_urls(result_of(rec))]
    for i, m in enumerate(media):
        data = None
        if m.get("key"):
            try:
                data = kv_get(m["key"], raw=True)
            except Exception as e:
                print("kv mirror fetch failed", e, file=sys.stderr)
        if data is None and m.get("url"):
            st, data = _req("GET", m["url"], timeout=300, raw=True)
            if st != 200:
                data = None
        if data is None:
            continue
        ext = ".bin"
        head = data[:16]
        if head[4:8] == b"ftyp":
            ext = ".mp4" if b"qt" not in head[8:12] else ".mov"
        elif head[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif head[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif head[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ext = ".webp"
        elif head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            ext = ".mp3"
        elif head[:4] == b"RIFF":
            ext = ".wav"
        p = f"{dest_prefix}{'' if len(media) == 1 else f'_{i}'}{ext}"
        with open(p, "wb") as f:
            f.write(data)
        paths.append(p)
    return paths
