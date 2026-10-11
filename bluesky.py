"""Bluesky Jetstream -> data/events.parquet (source 'bluesky', kind 'post'). Long-running; run separately from collect.py.
  python3 bluesky.py            handles in bluesky_accounts.txt -> DIDs cached in data/bluesky_dids.json
t0_utc = record createdAt floored to the second (author-supplied, so can be wrong; first_seen_utc is our receipt time).
"""
import asyncio, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd, requests, websockets
from collect import UA, eid, utc, merge

HERE = Path(__file__).parent
DIDS, LOG = HERE / "data" / "bluesky_dids.json", HERE / "data" / "bluesky.log"
# jetstream2.us-east was observed 2026-10-11 delivering posts ~3700 s late while the other three were real-time (median
# receipt - createdAt 1 s), so it is last; flush lines log lag_s so a stuck instance is visible. Rotates on every reconnect.
HOSTS = ["jetstream1.us-east", "jetstream1.us-west", "jetstream2.us-west", "jetstream2.us-east"]
WS = "wss://{}.bsky.network/subscribe?wantedCollections=app.bsky.feed.post&"
RESOLVE = "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle"
FLUSH_S = 5

def log(*a):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f: print(datetime.now(timezone.utc).strftime("%F %T"), *a, file=f, flush=True)

def resolve():
    """handle -> did, cached; handles that fail to resolve are logged and skipped."""
    cache = json.loads(DIDS.read_text()) if DIDS.exists() else {}
    for h in (l.strip() for l in (HERE / "bluesky_accounts.txt").read_text().splitlines()):
        if not h or h.startswith("#") or h in cache: continue
        try:
            r = requests.get(RESOLVE, params={"handle": h}, headers=UA, timeout=15); r.raise_for_status()
            cache[h] = r.json()["did"]
        except Exception as e: log("resolve FAIL", h, repr(e)[:100])
    DIDS.parent.mkdir(exist_ok=True); DIDS.write_text(json.dumps(cache, indent=1))
    return cache

def parse_msg(msg, did2handle, recv=None):
    """One Jetstream message -> event row or None. Replies are kept (a reply from a wire account is still a post)."""
    m = json.loads(msg) if isinstance(msg, (str, bytes)) else msg
    c = m.get("commit") or {}
    if m.get("kind") != "commit" or c.get("operation") != "create" or c.get("collection") != "app.bsky.feed.post": return None
    h = did2handle.get(m["did"])
    if not h: return None
    rec = c["record"]
    return dict(event_id=eid("bluesky", f"{m['did']}/{c['rkey']}"), source="bluesky", kind="post",
                t0_utc=utc(pd.Timestamp(rec["createdAt"])), first_seen_utc=utc(recv or datetime.now(timezone.utc)),
                title=" ".join((rec.get("text") or "").split()) or "[media]", url=f"https://bsky.app/profile/{h}/post/{c['rkey']}")

async def run(dids):
    d2h, cursor, buf, backoff, hi = {v: k for k, v in dids.items()}, None, [], 1, 0
    while True:
        url = WS.format(HOSTS[hi % len(HOSTS)]) + "&".join(f"wantedDids={d}" for d in d2h) + (f"&cursor={cursor}" if cursor else "")
        try:
            async with websockets.connect(url, max_size=2**22, ping_interval=20) as ws:
                log("connected", HOSTS[hi % len(HOSTS)], "cursor", cursor, "dids", len(d2h)); backoff, last = 1, time.time()
                while True:
                    try: msg = await asyncio.wait_for(ws.recv(), FLUSH_S)
                    except asyncio.TimeoutError: msg = None
                    if msg:
                        m = json.loads(msg); cursor = m.get("time_us", cursor)
                        row = parse_msg(m, d2h)
                        if row: buf.append(row)
                    if buf and time.time() - last >= FLUSH_S:
                        n = merge(buf); lag = int((pd.Timestamp.now("UTC") - max(r["t0_utc"] for r in buf)).total_seconds())
                        log("flush", len(buf), "new", n, "lag_s", lag, "cursor", cursor); buf, last = [], time.time()
        except Exception as e:
            log("disconnect", repr(e)[:150], "retry in", backoff, "s")
            hi += 1; await asyncio.sleep(backoff); backoff = min(backoff * 2, 60)
            if cursor: cursor -= 5_000_000  # rewind 5 s; dedup by event_id makes the overlap harmless

if __name__ == "__main__":
    dids = resolve(); log("start", len(dids), "accounts"); print(len(dids), "accounts; log:", LOG)
    asyncio.run(run(dids))
