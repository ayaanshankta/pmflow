"""Entry prices for ALL snapshots (DEV and TEST): first fill at or after T, and the VWAP of fills in [T, T + 2 h),
both only from fills before the market's resolution. Replaces Monday VWAP, which mixed in post-result trades.

Run:  python behav_entry2.py      Out: data/behav/entry2.parquet (condition_id, T, p_next, ts_next, p_vwap2h, n2h)
"""
import shutil
import tempfile
from pathlib import Path

import pandas as pd

import behav_build as bb

OUT = bb.OUT / "entry2.parquet"


def main():
    s = pd.read_parquet(bb.OUT / "snapshots.parquet", columns=["condition_id", "T", "res_ts"])
    tmp, rows = Path(tempfile.mkdtemp(prefix="entry2_")), []
    try:
        for T, g0 in s.groupby("T"):
            f = bb.load_day(T.date(), tmp)
            if f is None:
                print(T.date(), "no archive day", flush=True); continue
            f = f.merge(g0[["condition_id", "res_ts"]], on="condition_id")
            f = f[f.block_timestamp < f.res_ts].sort_values("block_timestamp")  # block_timestamp and res_ts in seconds
            t0 = int(T.timestamp())
            w = f[f.block_timestamp < t0 + 7200]
            g, gw = f.groupby("condition_id"), w.assign(pv=w.p_event * w.usdc_amount).groupby("condition_id")
            a = pd.DataFrame({"p_next": g.p_event.first(), "ts_next": g.block_timestamp.first()})
            a = a.join(pd.DataFrame({"p_vwap2h": gw.pv.sum() / gw.usdc_amount.sum(), "n2h": gw.size()})).reset_index()
            rows.append(a.assign(T=T))
            print(T.date(), len(g0), "next", len(a), "2h", a.n2h.notna().sum(), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pd.concat(rows, ignore_index=True).to_parquet(OUT)


if __name__ == "__main__":
    main()
