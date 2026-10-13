"""Append-only side streams (trades, depth): one part file per flush, all markets together.
Layout: {root}/date=YYYY-MM-DD/part-HHMMSS.parquet, market_id is a column. Earlier files are never rewritten.
Read with read_stream(root, market_id, lo, hi)."""
import glob, logging, os, time
import pandas as pd, pyarrow.parquet as pq

RETRY_PAUSE = 0.1  # s; doubles per attempt (tests set it to 0)

def replace_retry(src, dst, tries=4):
    """os.replace, retried with a short growing pause (0.1, 0.2, 0.4 s): on Windows a program that has the target open
    (backup, antivirus, indexer) makes it raise PermissionError, usually for well under a second. Raises after the last try."""
    for k in range(tries):
        try: return os.replace(src, dst)
        except OSError:
            if k == tries - 1: raise
            time.sleep(RETRY_PAUSE * 2 ** k)

def write_part(buf, cols, root, dtypes, now=None, kept=None, fails=None):
    """buf: market_id -> [row tuples]. One part file per UTC day present in the rows. Returns rows written.
    kept (dict) given: a day whose file cannot be written is not raised; its rows are put back into kept (market -> [rows], the
    original tuples) for a later call, its name is appended to fails and one error line is logged."""
    rows = [(m, *r) for m, rs in buf.items() for r in rs]
    if not rows: return 0
    df = pd.DataFrame(rows, columns=["market_id", *cols]).astype(dtypes).sort_values("recv_ns", kind="stable")  # index = position in rows
    stamp = time.strftime("%H%M%S", time.gmtime(now if now is not None else time.time()))
    n, handled = 0, set()                                # handled: days written or kept (a later raise must not re-keep them)
    try:
        for day, g in df.groupby(pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")):
            d = f"{root}/date={day}"; p = f"{d}/part-{stamp}.parquet"
            try:
                os.makedirs(d, exist_ok=True); k = 0
                while os.path.exists(p): k += 1; p = f"{d}/part-{stamp}-{k}.parquet"   # two flushes in one second
                g.to_parquet(p + ".tmp", index=False); replace_retry(p + ".tmp", p)
                n += len(g); handled.add(day)
            except Exception as e:
                if kept is None: raise
                try: os.remove(p + ".tmp")
                except OSError: pass
                fails.append(p); logging.error("flush FAILED %s: %r -- %d rows kept for retry", p, e, len(g))
                for i in g.index: kept.setdefault(rows[i][0], []).append(rows[i][1:])
                handled.add(day)
    except Exception as e:
        if kept is None: raise
        days = pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")   # may itself raise -> caller keeps everything (nothing written yet)
        left = [i for i in df.index if days[i] not in handled]
        fails.append(root); logging.error("flush FAILED %s: %r -- %d rows kept for retry", root, e, len(left))
        for i in left: kept.setdefault(rows[i][0], []).append(rows[i][1:])
    return n

def read_stream(root, market_id, lo_ns, hi_ns):
    """Rows of one market with lo_ns <= recv_ns <= hi_ns, sorted by recv_ns (empty frame if none)."""
    days = pd.date_range(pd.Timestamp(lo_ns, tz="UTC").normalize(), pd.Timestamp(hi_ns, tz="UTC").normalize())
    fs = [f for d in days for f in sorted(glob.glob(f"{root}/date={d:%Y-%m-%d}/part-*.parquet"))]
    ts = [pq.read_table(f, partitioning=None, filters=[("market_id", "=", str(market_id)), ("recv_ns", ">=", lo_ns), ("recv_ns", "<=", hi_ns)]).to_pandas() for f in fs]
    ts = [t for t in ts if len(t)]
    return pd.concat(ts, ignore_index=True).sort_values("recv_ns", kind="stable", ignore_index=True) if ts else pd.DataFrame()
