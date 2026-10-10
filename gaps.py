"""List recording gaps > 90 s (sleep, network). Run: python3 gaps.py"""
import glob, pyarrow.parquet as pq, pandas as pd
t = pd.concat([pq.read_table(f, columns=["recv_ns"]).to_pandas() for f in glob.glob("data/tob/polymarket/*/date=*.parquet")], ignore_index=True)
s = pd.to_datetime(t.recv_ns.sort_values().reset_index(drop=True), utc=True); g = s.diff().dt.total_seconds()
for i in g[g > 90].index: print("gap %.1f min from %s UTC" % (g[i] / 60, s[i - 1].strftime("%Y-%m-%d %H:%M:%S")))
print("last row", s.iloc[-1].strftime("%Y-%m-%d %H:%M:%S"), "UTC")
