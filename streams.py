"""Append-only side streams (trades, depth): one part file per flush, all markets together.
Layout: {root}/date=YYYY-MM-DD/part-HHMMSS.parquet, market_id is a column. Earlier files are never rewritten.
Read with read_stream(root, market_id, lo, hi)."""
import glob, os, time
import pandas as pd, pyarrow.parquet as pq

def write_part(buf, cols, root, dtypes, now=None):
    """buf: market_id -> [row tuples]. One part file per UTC day present in the rows. Returns rows written."""
    rows = [(m, *r) for m, rs in buf.items() for r in rs]
    if not rows: return 0
    df = pd.DataFrame(rows, columns=["market_id", *cols]).astype(dtypes).sort_values("recv_ns", kind="stable", ignore_index=True)
    stamp = time.strftime("%H%M%S", time.gmtime(now if now is not None else time.time()))
    for day, g in df.groupby(pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")):
        d = f"{root}/date={day}"; os.makedirs(d, exist_ok=True)
        p, k = f"{d}/part-{stamp}.parquet", 0
        while os.path.exists(p): k += 1; p = f"{d}/part-{stamp}-{k}.parquet"   # two flushes in one second
        g.to_parquet(p + ".tmp", index=False); os.replace(p + ".tmp", p)
    return len(df)

def read_stream(root, market_id, lo_ns, hi_ns):
    """Rows of one market with lo_ns <= recv_ns <= hi_ns, sorted by recv_ns (empty frame if none)."""
    days = pd.date_range(pd.Timestamp(lo_ns, tz="UTC").normalize(), pd.Timestamp(hi_ns, tz="UTC").normalize())
    fs = [f for d in days for f in sorted(glob.glob(f"{root}/date={d:%Y-%m-%d}/part-*.parquet"))]
    ts = [pq.read_table(f, partitioning=None, filters=[("market_id", "=", str(market_id)), ("recv_ns", ">=", lo_ns), ("recv_ns", "<=", hi_ns)]).to_pandas() for f in fs]
    ts = [t for t in ts if len(t)]
    return pd.concat(ts, ignore_index=True).sort_values("recv_ns", kind="stable", ignore_index=True) if ts else pd.DataFrame()
