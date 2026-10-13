"""A real open handle on a day file, no mocking: what a backup or antivirus scan does on Windows.
On Windows os.replace onto a file another handle has open raises PermissionError, so the market's rows must be held and
written by a later flush. On macOS/Linux the rename succeeds and nothing is held. Either way: no row lost, none duplicated,
receive-time order kept, no stray .tmp. Run: python test_filelock_real.py  (also collected by pytest)."""
import os, sys, tempfile
import pandas as pd
import record_polymarket as RP, streams
from fixture_stream import DAY1


def _book(tok, px):
    return {"event_type": "book", "asset_id": tok, "bids": [{"price": px, "size": "5"}], "asks": [{"price": "0.60", "size": "5"}]}


def test_open_handle_then_release():
    streams.RETRY_PAUSE = 0.01
    d = tempfile.mkdtemp()
    r = RP.Recorder({"YA": "MA", "YB": "MB"}, out=d + "/tob", conn_file=d + "/c.txt", resolved=d + "/r.jsonl",
                    trades=d + "/trades", depth=d + "/depth", ticks=d + "/t.jsonl")
    r.new_conn()
    r.on_msg(_book("YA", "0.40"), DAY1); r.on_msg(_book("YB", "0.40"), DAY1 + 1)
    assert r.flush() == 2 and r.held_n == 0                      # both day files now exist
    pb = [os.path.join(dp, f) for dp, _, fs in os.walk(d + "/tob") for f in fs if "MB" in dp and f.endswith(".parquet")][0]
    h = open(pb, "rb")                                           # another program has MB's day file open
    try:
        r.on_msg(_book("YA", "0.41"), DAY1 + 10); r.on_msg(_book("YB", "0.41"), DAY1 + 11)
        r.flush()
        locked = r.held_n > 0                                    # True on Windows, False where rename-over-open works
        if locked: assert r.fail_n == 1 and r.held_n == 1
        r.on_msg(_book("YB", "0.42"), DAY1 + 20)
        r.flush()                                                # still open: still held (Windows) or written (POSIX)
        if locked: assert r.held_n == 2
    finally:
        h.close()
    r.on_msg(_book("YA", "0.43"), DAY1 + 30)
    r.flush()                                                    # handle released: everything must be on disk now
    assert r.held_n == 0 and r.fail_n == 0
    a = pd.read_parquet(os.path.join(d, "tob", "MA", os.path.basename(pb))); b = pd.read_parquet(pb)
    assert a.recv_ns.tolist() == [DAY1, DAY1 + 10, DAY1 + 30]
    assert b.recv_ns.tolist() == [DAY1 + 1, DAY1 + 11, DAY1 + 20]   # exactly once each, in receive-time order
    assert b.bid_px.tolist() == [0.40, 0.41, 0.42]
    assert not [f for _, _, fs in os.walk(d) for f in fs if f.endswith(".tmp")]
    return locked


if __name__ == "__main__":
    print("test_filelock_real ok; rename was blocked by the open handle:", test_open_handle_then_release(), "| platform", sys.platform)
