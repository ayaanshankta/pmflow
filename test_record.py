import os, tempfile, pandas as pd
from record_polymarket import Recorder

d = tempfile.mkdtemp()
r = Recorder({"YES1": "M1", "YES2": "M2"}, out=d + "/tob", conn_file=d + "/conn.txt")
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
# restart resumes conn_id from file
assert Recorder({"YES1": "M1"}, out=d, conn_file=d + "/conn.txt").conn_id == 2
print("test_record ok")
