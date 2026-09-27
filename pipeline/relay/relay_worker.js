// Rare Earth (techno remix) generation relay.
//
// The sandbox that drives this project can only reach api.cloudflare.com, and requests through it
// are cut at ~30 s, so long generations (Seedance video, music) cannot be awaited directly.
// This Worker provides two paths, both reporting into KV (read back via the Cloudflare KV API):
//
// 1. Webhook sink:  /ai/run requests are sent with options.background=true and
//    webhookUrl=https://<this worker>/hook/<HOOK_SECRET>/<jobId>. AI Gateway POSTs the finished run
//    here; we store it as "res:<jobId>" and mirror small media files into "media:<jobId>:<n>".
//
// 2. Cron queue (fallback): the client writes "job:<minuteBucket>:<jobId>" -> {model, input}.
//    The cron invocation whose scheduled minute equals <minuteBucket> runs exactly those jobs,
//    so overlapping cron runs can never claim (and pay for) the same job twice.

const MAX_MIRROR_BYTES = 24 * 1024 * 1024;

function mediaUrls(r) {
  const out = [];
  const visit = (v) => {
    if (!v) return;
    if (typeof v === "string") { if (/^https?:\/\//.test(v)) out.push(v); return; }
    if (Array.isArray(v)) { v.forEach(visit); return; }
    if (typeof v === "object") {
      for (const k of ["video", "image", "images", "audio", "result", "output"]) visit(v[k]);
    }
  };
  visit(r);
  return [...new Set(out)];
}

async function mirror(env, jobId, result) {
  const urls = mediaUrls(result);
  const mirrored = [];
  for (let i = 0; i < urls.length; i++) {
    try {
      const resp = await fetch(urls[i]);
      if (!resp.ok) { mirrored.push({ url: urls[i], error: "fetch " + resp.status }); continue; }
      const buf = await resp.arrayBuffer();
      if (buf.byteLength > MAX_MIRROR_BYTES) { mirrored.push({ url: urls[i], error: "too big", bytes: buf.byteLength }); continue; }
      const key = `media:${jobId}:${i}`;
      await env.JOBS.put(key, buf, { expirationTtl: 14 * 86400,
        metadata: { type: resp.headers.get("content-type") || "", bytes: buf.byteLength } });
      mirrored.push({ url: urls[i], key, bytes: buf.byteLength, type: resp.headers.get("content-type") || "" });
    } catch (e) {
      mirrored.push({ url: urls[i], error: String((e && e.message) || e) });
    }
  }
  return mirrored;
}

async function runJob(env, jobKey, jobId) {
  const job = await env.JOBS.get(jobKey, "json");
  if (!job) return;
  const t0 = Date.now();
  await env.JOBS.put("state:" + jobId, JSON.stringify({ state: "running", t0 }), { expirationTtl: 14 * 86400 });
  let rec;
  try {
    const r = await env.AI.run(job.model, job.input);
    const media = await mirror(env, jobId, r);
    rec = { state: "done", via: "cron", model: job.model, result: r, media, t0, t1: Date.now() };
  } catch (e) {
    rec = { state: "error", via: "cron", model: job.model, error: String((e && e.message) || e), t0, t1: Date.now() };
  }
  await env.JOBS.put("res:" + jobId, JSON.stringify(rec), { expirationTtl: 14 * 86400 });
  await env.JOBS.delete(jobKey);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const parts = url.pathname.split("/").filter(Boolean);
    if (request.method === "POST" && parts[0] === "hook" && parts[1] === env.HOOK_SECRET && parts[2]) {
      const jobId = parts[2].replace(/[^A-Za-z0-9_.-]/g, "");
      const body = await request.text();
      let payload;
      try { payload = JSON.parse(body); } catch { payload = { raw: body }; }
      const rec = { state: payload.error ? "error" : "done", via: "webhook", payload, t1: Date.now() };
      await env.JOBS.put("res:" + jobId, JSON.stringify(rec), { expirationTtl: 14 * 86400 });
      ctx.waitUntil((async () => {
        if (!payload.error) {
          const media = await mirror(env, jobId, payload.result);
          await env.JOBS.put("res:" + jobId, JSON.stringify({ ...rec, media }), { expirationTtl: 14 * 86400 });
        }
      })());
      return new Response("ok");
    }
    return new Response("rare earth remix relay", { status: parts.length ? 404 : 200 });
  },

  async scheduled(event, env, ctx) {
    const bucket = Math.floor(event.scheduledTime / 60000);
    const list = await env.JOBS.list({ prefix: `job:${bucket}:` });
    ctx.waitUntil(Promise.all(list.keys.map((k) => runJob(env, k.name, k.name.split(":")[2]))));
  },
};
