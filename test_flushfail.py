"""Failed file writes (Windows: another program holds the file) must lose nothing and never kill the flusher.
The rename is made to raise PermissionError for chosen paths; everything else is the real code."""
import asyncio, logging, os, tempfile, time, pandas as pd
import record_polymarket as RP, streams, collect
from fixture_stream import DAY1, BOOK, S, pc
from streams import read_stream

streams.RETRY_PAUSE = 0                       # no sleeping in tests
REAL = os.replace
BAD = set()                                   # substrings of destination paths whose rename fails
def fake_replace(src, dst, *a, **k):
    if any(b in str(dst) for b in BAD): raise PermissionError(13, "in use by another process", str(dst))
    return REAL(src, dst, *a, **k)
os.replace = fake_replace

class Cap(logging.Handler):
    def __init__(self): super().__init__(); self.lines = []
    def emit(self, r): self.lines.append((r.levelname, r.getMessage()))
cap = Cap(); logging.getLogger().addHandler(cap); logging.getLogger().setLevel(logging.INFO)

def mk():
    d = tempfile.mkdtemp()
    return d, RP.Recorder({"Y1": "M1", "Y2": "M2", "Y3": "M3"}, out=d + "/tob", conn_file=d + "/c.txt", resolved=d + "/r.jsonl",
                          trades=d + "/trades", depth=d + "/depth", ticks=d + "/t.jsonl")
def book(tok, px="0.40"):
    return {"event_type": "book", "asset_id": tok, "bids": [{"price": px, "size": "5"}], "asks": [{"price": "0.60", "size": "5"}]}
def bid(tok, px, ns, r): r.on_msg({"event_type": "price_change", "price_changes": [{"asset_id": tok, "price": px, "size": "3", "side": "BUY"}]}, ns)
def trade(tok, px, ns, r): r.on_msg({"event_type": "last_trade_price", "asset_id": tok, "price": px, "size": "1", "side": "BUY", "timestamp": "1"}, ns)
rd = lambda d, m: pd.read_parquet(f"{d}/tob/{m}/date=2025-10-09.parquet")

# ---- top-of-book: M2's rename fails for one flush ----
d, r = mk(); r.new_conn()
for i, t in enumerate(("Y1", "Y2", "Y3")): r.on_msg(book(t), DAY1 + i)
BAD.add("/M2/")
assert r.flush() == 2                                              # M1 and M3 written, M2 not
assert r.held_n == 1 and r.fail_n == 1 and not os.path.exists(f"{d}/tob/M2/date=2025-10-09.parquet")
assert not glob_tmp if (glob_tmp := [f for _, _, fs in os.walk(d) for f in fs if f.endswith(".tmp")]) else True   # no stray tmp
assert any(l == "ERROR" and "M2" in m and "PermissionError" in m for l, m in cap.lines), cap.lines
assert len(rd(d, "M1")) == 1 and len(rd(d, "M3")) == 1
bid("Y2", "0.41", DAY1 + 10, r); bid("Y1", "0.41", DAY1 + 11, r)   # more rows arrive; M2 still failing -> held rows must keep order
assert r.flush() == 1 and r.held_n == 2 and r.fail_n == 1
BAD.clear()
bid("Y2", "0.42", DAY1 + 20, r)
assert r.flush() == 3 and r.held_n == 0 and r.fail_n == 0         # held (2) + new (1)
m2 = rd(d, "M2")
assert m2.recv_ns.tolist() == [DAY1 + 1, DAY1 + 10, DAY1 + 20] and m2.bid_px.tolist() == [.40, .41, .42], m2   # sorted, nothing lost or duplicated
assert len(rd(d, "M1")) == 2 and len(rd(d, "M3")) == 1
# rows kept for retry sort with rows that arrived out of order relative to them: held (older) first, in recv order
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1 + 5); BAD.add("/M2/"); r.flush(); BAD.clear()
r.buf = {"M2": [(DAY1 + 3, 1, .1, .2, 1., 1.)]}                    # an earlier-stamped row in the next batch must still end up sorted
r.flush(); assert rd(d, "M2").recv_ns.tolist() == [DAY1 + 3, DAY1 + 5]
# day boundary: only the failing day's rows are held
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1); bid("Y2", "0.45", DAY1 + 86_400 * S, r)
BAD.add("date=2025-10-10"); assert r.flush() == 1 and r.held_n == 1; BAD.clear(); r.flush()
assert len(rd(d, "M2")) == 1 and len(pd.read_parquet(f"{d}/tob/M2/date=2025-10-10.parquet")) == 1
# a failure while READING the existing day file (corrupt/locked) is held too, then recovers
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1); r.flush()
p = f"{d}/tob/M2/date=2025-10-09.parquet"; good = open(p, "rb").read(); open(p, "wb").write(b"junk")
bid("Y2", "0.41", DAY1 + 9, r); assert r.flush() == 0 and r.held_n == 1
open(p, "wb").write(good); r.flush(); assert rd(d, "M2").recv_ns.tolist() == [DAY1, DAY1 + 9]
# rename that fails only twice is retried within the same flush
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1); n = {"k": 0}
def flaky(src, dst, *a, **k):
    n["k"] += 1
    if n["k"] <= 2: raise PermissionError(13, "busy")
    return REAL(src, dst)
os.replace = flaky; assert r.flush() == 1 and r.held_n == 0 and n["k"] == 3; os.replace = fake_replace

# ---- an exception from inside _write after some markets were written: every row exactly once, in order ----
real_w = RP.Recorder._write
def run_case(patch):
    d, r = mk(); r.new_conn()
    for i, t in enumerate(("Y1", "Y2", "Y3")): r.on_msg(book(t), DAY1 + i)
    r._write = patch; r.flush(); assert 0 <= r.held_n <= 2
    del r._write
    for t_, k in (("Y1", 10), ("Y2", 11), ("Y3", 12)): bid(t_, "0.41", DAY1 + k, r)
    r.flush(); r.flush(); assert r.held_n == 0
    for m, k in (("M1", 0), ("M2", 1), ("M3", 2)): assert rd(d, m).recv_ns.tolist() == [DAY1 + k, DAY1 + 10 + k], (m, rd(d, m))
def partial(buf, cols, out, dt_, kept=None, fails=None, done=None):       # M1 written, then the machinery itself raises
    real_w({"M1": buf["M1"]}, cols, out, dt_, kept, fails, done); raise RuntimeError("late boom")
run_case(partial)
calls = {"n": 0}
real_gb = pd.DataFrame.groupby
def gb(self, *a, **k):                                                   # raises outside the per-file try, on the 2nd market
    calls["n"] += 1
    if calls["n"] == 2: raise RuntimeError("grouping boom")
    return real_gb(self, *a, **k)
pd.DataFrame.groupby = gb
try: run_case(real_w)
finally: pd.DataFrame.groupby = real_gb
# same for the part files: raise after one day was written
d, r = mk(); r.new_conn(); trade("Y1", "0.50", DAY1, r); trade("Y1", "0.51", DAY1 + 86_400 * S, r)
calls["n"] = 0; real_to_pq = pd.DataFrame.to_parquet
def tp(self, path, *a, **k):
    calls["n"] += 1
    if calls["n"] == 2: raise RuntimeError("disk boom")
    return real_to_pq(self, path, *a, **k)
pd.DataFrame.to_parquet = tp
try: r.flush()
finally: pd.DataFrame.to_parquet = real_to_pq
assert r.held_n == 1; r.flush()
assert read_stream(d + "/trades", "M1", DAY1, DAY1 + 2 * 86_400 * S).price.tolist() == [.50, .51]

# ---- trades part file ----
d, r = mk(); r.new_conn(); trade("Y1", "0.50", DAY1 + 1, r); trade("Y2", "0.51", DAY1 + 2, r)
BAD.add("/trades/"); r.flush()
assert r.held_n == 2 and r.fail_n == 1 and not [f for _, _, fs in os.walk(d + "/trades") for f in fs]
trade("Y1", "0.52", DAY1 + 3, r); BAD.clear(); r.flush(); assert r.held_n == 0
x = read_stream(d + "/trades", "M1", DAY1, DAY1 + 9)
assert x.price.tolist() == [.50, .52] and read_stream(d + "/trades", "M2", DAY1, DAY1 + 9).price.tolist() == [.51]
assert x.exch_ts_ms.dtype == "Int64" and x.recv_ns.dtype == "int64"

# ---- flusher survives, prints its line with the new fields, watchdog reports not-recording ----
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1)
RP.FLUSH_S, RP.LIVE_AGE_S = 0.15, 0.3
real_take, real_w, boom, wb = r.take, RP.Recorder._write, {"n": 0}, {"n": 0}
def take_boom():                                                   # unexpected error in the loop part of an iteration: logged, loop goes on
    boom["n"] += 1
    if boom["n"] == 1: raise RuntimeError("boom")
    return real_take()
def write_boom(*a, **k):                                           # unexpected error inside the writer: every row stays held
    wb["n"] += 1
    if wb["n"] == 1: raise RuntimeError("boom2")
    return real_w(*a, **k)
r.take, r._write = take_boom, write_boom
async def run():
    dl = time.time() + 30
    tasks = [asyncio.create_task(RP.flusher(r, dl)), asyncio.create_task(RP.watchdog(r, dl, asyncio.current_task(), every=0.05))]
    await asyncio.sleep(0.5)
    BAD.add("/M2/"); r.on_msg(book("Y2", "0.41"), DAY1 + 5)
    await asyncio.sleep(1.2); BAD.clear(); r.on_msg(book("Y2", "0.42"), DAY1 + 6); await asyncio.sleep(0.5)
    assert not any(t.done() for t in tasks)
    for t in tasks: t.cancel()
asyncio.run(run()); BAD.clear()
msgs = [m for _, m in cap.lines]
assert any("flusher iteration error" in m for m in msgs) and any("tob flush error" in m for m in msgs)
assert any(m.startswith("rows/min=") and m.endswith("held=0 failed_files=0") for m in msgs)
assert any(m.startswith("rows/min=") and "held=1 failed_files=1" in m for m in msgs), msgs[-10:]
assert any(m.startswith("NOT RECORDING: no successful flush for") and "rows held in memory=" in m for m in msgs)
assert rd(d, "M2").recv_ns.tolist() == [DAY1, DAY1 + 5, DAY1 + 6], rd(d, "M2")

# ---- final flush on cancellation includes held rows; stop file ----
d, r = mk(); r.new_conn(); r.on_msg(book("Y2"), DAY1); BAD.add("/M2/"); r.flush(); BAD.clear(); bid("Y2", "0.41", DAY1 + 1, r)
async def stopped():
    RP.STOP_FILE = d + "/STOP"
    async def sess(*a): await asyncio.sleep(3600)
    RP.run_sessions = lambda rec, tokens, dl: sess()
    real_rp = pd.read_parquet; pd.read_parquet = lambda p: pd.DataFrame({"token_id_yes": ["Y2"], "market_id": ["M2"]})
    RP.Recorder = lambda t2m: r
    os.makedirs("data", exist_ok=True)
    t = asyncio.create_task(RP.main()); await asyncio.sleep(0.2); pd.read_parquet = real_rp; open(RP.STOP_FILE, "w").close()
    await asyncio.wait_for(asyncio.shield(asyncio.gather(t, return_exceptions=True)), 10)
cwd, saved = os.getcwd(), (RP.Recorder, RP.run_sessions, RP.STOP_FILE, RP.FLUSH_S, RP.LIVE_AGE_S)
os.chdir(d)
try: asyncio.run(stopped())
finally: os.chdir(cwd); RP.Recorder, RP.run_sessions, RP.STOP_FILE, RP.FLUSH_S, RP.LIVE_AGE_S = saved
assert rd(d, "M2").recv_ns.tolist() == [DAY1, DAY1 + 1] and r.held_n == 0 and not os.path.exists(d + "/STOP")

# ---- collector events file ----
now = pd.Timestamp("2025-10-09T12:00:00Z")
ev = lambda k: dict(event_id=f"e{k}", source="s", t0_utc=now, title=f"t{k}", url="u", kind="article")
d = tempfile.mkdtemp(); out = collect.Path(d) / "events.parquet"
assert collect.merge([ev(1)], out, now=now) == 1
BAD.add("events.parquet")
assert collect.merge([ev(2)], out, now=now) == 0                    # fails: kept, no raise
assert not out.with_suffix(".lock").exists() and not out.with_suffix(".tmp").exists()
assert len(pd.read_parquet(out)) == 1
BAD.clear()
assert collect.merge([ev(3)], out, now=now + pd.Timedelta(seconds=30)) == 2   # e2 (kept) + e3
df = pd.read_parquet(out)
assert sorted(df.event_id) == ["e1", "e2", "e3"] and not out.with_suffix(".lock").exists()
assert df.set_index("event_id").first_seen_utc["e2"] == now          # first_seen is when it was first seen, not when finally written
assert collect.merge([ev(2)], out, now=now) == 0                    # no duplicates
os.replace = REAL; logging.getLogger().removeHandler(cap)   # leave nothing patched for other test modules
print("test_flushfail ok")
