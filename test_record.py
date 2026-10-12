import os, json, tempfile, pandas as pd
from record_polymarket import Recorder

d = tempfile.mkdtemp()
r = Recorder({"YES1": "M1", "YES2": "M2"}, out=d + "/tob", conn_file=d + "/conn.txt", resolved=d + "/res.jsonl",
             trades=d + "/trades", depth=d + "/depth", ticks=d + "/ticks.jsonl")
day1 = 1_760_000_000 * 10**9                    # 2025-10-09 UTC
assert r.new_conn() == 1
book = {"event_type": "book", "asset_id": "YES1", "market": "M1",
        "bids": [{"price": "0.40", "size": "10"}, {"price": "0.45", "size": "5"}],
        "asks": [{"price": "0.55", "size": "7"}, {"price": "0.60", "size": "9"}]}
r.on_msg([book, {"event_type": "book", "asset_id": "OTHER", "bids": [], "asks": []}], day1)  # unknown token ignored
pc = lambda px, sz, side: {"event_type": "price_change", "price_changes": [
    {"asset_id": "YES1", "price": px, "size": sz, "side": side}]}
r.on_msg(pc("0.46", "3", "BUY"), day1 + 1)      # new best bid
r.on_msg(pc("0.46", "3", "BUY"), day1 + 2)      # identical state -> no row
r.on_msg(pc("0.20", "8", "BUY"), day1 + 3)      # deep level -> TOB unchanged -> no row
r.on_msg(pc("0.46", "0", "BUY"), day1 + 4)      # remove -> back to 0.45
r.on_msg(pc("0.55", "0", "SELL"), day1 + 5)     # ask moves to 0.60
assert r.rows_min == 4, r.rows_min
assert r.new_conn() == 2                        # reconnect -> conn_id++, books reset
r.on_msg(book, day1 + 10**9)                    # fresh snapshot, new conn
r.on_msg(book, day1 + 2 * 10**9 + 86_400 * 10**9)  # same book next UTC day: no change -> no row
assert r.rows_min == 5
assert r.flush() == 5
r.on_msg(pc("0.50", "1", "BUY"), day1 + 3 * 10**9 + 86_400 * 10**9)  # next day, after a flush: must append
r.flush()
f1 = f"{d}/tob/M1/date=2025-10-09.parquet"; f2 = f"{d}/tob/M1/date=2025-10-10.parquet"
a, b = pd.read_parquet(f1), pd.read_parquet(f2)
assert list(a.columns) == ["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"]
assert len(a) == 5 and a.conn_id.tolist() == [1, 1, 1, 1, 2], a
assert a.iloc[0][["bid_px", "ask_px", "bid_sz", "ask_sz"]].tolist() == [0.45, 0.55, 5.0, 7.0]
assert a.iloc[3][["bid_px", "ask_px"]].tolist() == [0.45, 0.60]
assert len(b) == 1 and b.conn_id.iloc[0] == 2 and b.bid_px.iloc[0] == 0.50
assert a.bid_px.between(0, 1).all() and a.recv_ns.is_monotonic_increasing
# append-safe: second flush on same day keeps earlier rows
r.on_msg(pc("0.51", "1", "BUY"), day1 + 4 * 10**9 + 86_400 * 10**9); r.flush()
assert len(pd.read_parquet(f2)) == 2
r.on_msg({"event_type": "market_resolved", "market": "M1", "assets_ids": ["NO1", "YES1"], "winning_outcome": "Yes"}, 7)
r.on_msg({"event_type": "market_resolved", "market": "X", "assets_ids": ["A", "B"]}, 8)  # not ours
assert len(open(d + "/res.jsonl").read().splitlines()) == 1
# restart resumes conn_id from file
assert Recorder({"YES1": "M1"}, out=d, conn_file=d + "/conn.txt", depth=d + "/depth").conn_id == 2

# ---- recorder2: trades, depth, ticks; tob output pinned to the pre-change recorder on the same stream ----
from fixture_stream import STREAM, DAY1, BOOK, TICK, pc, S
mk = lambda: (lambda d: (d, Recorder({"YES1": "M1"}, out=d + "/tob", conn_file=d + "/c.txt", resolved=d + "/r.jsonl",
              trades=d + "/trades", depth=d + "/depth", ticks=d + "/ticks.jsonl")))(tempfile.mkdtemp())
d, r = mk(); r.new_conn()
for m, ns in STREAM: r.on_msg(m, ns)
assert r.flush() == 6
PIN = {"date=2025-10-09": [[DAY1, 1, .45, .55, 5., 7.], [DAY1 + 1, 1, .46, .55, 3., 7.], [DAY1 + 6, 1, .45, .55, 5., 7.],
                           [DAY1 + 7, 1, .45, .6, 5., 9.], [DAY1 + 3 * S, 1, .45, .55, 5., 7.]],
       "date=2025-10-10": [[DAY1 + 86_400 * S, 1, .5, .55, 1., 7.]]}  # captured from the pre-change code (pin.py)
for day, rows in PIN.items():
    g = pd.read_parquet(f"{d}/tob/M1/{day}.parquet")
    assert list(g.columns) == ["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"]
    assert g.to_dict("split")["data"] == rows and g.recv_ns.dtype == "int64" and g.conn_id.dtype == "int64", (day, g)
# trade: one row, exchange timestamp kept
tr = pd.read_parquet(f"{d}/trades/M1/date=2025-10-09.parquet")
assert len(tr) == 1 and tr.iloc[0][["recv_ns", "conn_id", "price", "size", "side", "exch_ts_ms"]].tolist() == [DAY1 + 2, 1, .46, 12.5, "SELL", 1760000000123]
assert tr.tx_hash.iloc[0] == "0xabc"
# tick change: jsonl with recv_ns
tk = [json.loads(l) for l in open(d + "/ticks.jsonl")]
assert len(tk) == 1 and tk[0]["new_tick_size"] == "0.001" and tk[0]["recv_ns"] == DAY1 + 5
r.on_msg({**TICK, "asset_id": "NOPE"}, 1); assert len(open(d + "/ticks.jsonl").read().splitlines()) == 1

# depth on a hand-built book: mid 0.51; bands 1/2/5 c = [bid,ask] per band
d, r = mk(); r.new_conn()
hb = {"event_type": "book", "asset_id": "YES1", "bids": [{"price": p, "size": s} for p, s in (("0.50", "10"), ("0.48", "5"), ("0.46", "7"), ("0.40", "20"))],
      "asks": [{"price": p, "size": s} for p, s in (("0.52", "4"), ("0.53", "6"), ("0.55", "8"), ("0.60", "9"))]}
t0 = DAY1
r.on_msg(hb, t0)
assert r.dbuf["M1"] == [(t0, 1, 10., 4., 10., 10., 22., 18., t0)], r.dbuf          # first state: written at once
# throttle: two changes inside 1 s -> pending, nothing written; the latest state is emitted on the next tick at/after +1 s
r.on_msg(pc("0.50", "11", "BUY"), t0 + S // 5)                                  # bid1c 10 -> 11
r.on_msg(pc("0.50", "12", "BUY"), t0 + 2 * S // 5)                              # -> 12 (replaces pending)
r.on_msg(pc("0.10", "99", "BUY"), t0 + 3 * S // 5)                              # outside 5c, tob same: no depth change
assert len(r.dbuf["M1"]) == 1 and r.dpend["YES1"][0] == t0 + 2 * S // 5
r.drain(t0 + 9 * S // 10); assert len(r.dbuf["M1"]) == 1                        # 0.9 s: still held
r.drain(t0 + S)
assert r.dbuf["M1"][1] == (t0 + S, 1, 12., 4., 12., 10., 24., 18., t0 + 2 * S // 5) and not r.dpend  # recv_ns = emit time, state_ns = arrival
r.on_msg(pc("0.50", "12", "BUY"), t0 + 3 * S)                                   # same state -> no row
r.drain(t0 + 5 * S); assert len(r.dbuf["M1"]) == 2
r.on_msg(pc("0.50", "0", "BUY"), t0 + 6 * S)                                    # >1 s since last write: emitted at once
assert len(r.dbuf["M1"]) == 3
r.on_msg(pc("0.50", "12", "BUY"), t0 + 6 * S + 1)                               # restore inside the window: pending
r.on_msg(pc("0.50", "0", "BUY"), t0 + 6 * S + 2)                                # back to last written state: pending dropped
r.drain(t0 + 8 * S); assert len(r.dbuf["M1"]) == 3 and not r.dpend
assert r.flush() == r.rows_min == 6  # tob: book + 5 best-level changes (unaffected by depth)
dp = pd.read_parquet(f"{d}/depth/M1/date=2025-10-09.parquet")
assert list(dp.columns) == ["recv_ns", "conn_id", "bid_1c", "ask_1c", "bid_2c", "ask_2c", "bid_5c", "ask_5c", "state_ns"] and len(dp) == 3
assert (dp.recv_ns.diff().dropna() >= S).all() and (dp.state_ns <= dp.recv_ns).all()
# one-sided book: nothing before any two-sided state; a NaN row when a two-sided book loses a side, not repeated
d, r = mk(); r.new_conn()
r.on_msg({**hb, "asks": []}, t0); r.drain(t0 + 2 * S); assert "M1" not in r.dbuf
r.on_msg(hb, t0 + 3 * S); r.on_msg({**hb, "asks": []}, t0 + 5 * S); r.on_msg({**hb, "asks": []}, t0 + 7 * S); r.drain(t0 + 9 * S)
assert len(r.dbuf["M1"]) == 2 and all(v != v for v in r.dbuf["M1"][1][2:8])
print("test_record ok")
