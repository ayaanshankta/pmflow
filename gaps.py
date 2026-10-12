"""List recording gaps > 90 s (sleep, network). Run: python3 gaps.py [--days N]   (N = only the last N UTC days; default all).
The full read grows with the recording; scheduled jobs on the recording machine should pass --days 2."""
import glob, re, sys, datetime as dt, pyarrow.parquet as pq, pandas as pd

def recent(files, days, today=None):
    """Keep files whose date=YYYY-MM-DD path part is within the last `days` UTC days (None = all)."""
    if days is None: return list(files)
    lo = (today or dt.datetime.now(dt.timezone.utc).date()) - dt.timedelta(days=days - 1)
    keep = []
    for f in files:
        m = re.search(r"date=(\d{4}-\d{2}-\d{2})", f)
        if m and dt.date.fromisoformat(m.group(1)) >= lo: keep.append(f)
    return keep

DAYS = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else None
_fs = recent(glob.glob("data/tob/polymarket/*/date=*.parquet"), DAYS)
if not _fs: print("no top-of-book files in the window"); sys.exit(0)
t = pd.concat([pq.read_table(f, columns=["recv_ns"]).to_pandas() for f in _fs], ignore_index=True)
s = pd.to_datetime(t.recv_ns.sort_values().reset_index(drop=True), utc=True); g = s.diff().dt.total_seconds()
for i in g[g > 90].index: print("gap %.1f min from %s UTC" % (g[i] / 60, s[i - 1].strftime("%Y-%m-%d %H:%M:%S")))
print("last row", s.iloc[-1].strftime("%Y-%m-%d %H:%M:%S"), "UTC")
tf = recent(glob.glob("data/trades/polymarket/date=*/part-*.parquet"), DAYS)
print("last trade row", pd.to_datetime(max(pq.read_table(f, columns=["recv_ns"]).to_pandas().recv_ns.max() for f in tf), unit="ns", utc=True).strftime("%Y-%m-%d %H:%M:%S") + " UTC" if tf else "none")
