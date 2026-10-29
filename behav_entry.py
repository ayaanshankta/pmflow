"""Executable entry prices for test snapshots: the first fill at or after T (Monday 00:00 UTC) on that Monday, and
Monday's VWAP. S1 as pre-registered enters at the VWAP of the 24 h BEFORE T, which no one could trade at; this checks
whether the S1 edge survives an entry that was actually available.

Run:  python behav_entry.py      Out: data/behav/entry_after_T.parquet (condition_id, T, p_next, ts_next, p_mon_vwap)
"""
import shutil
import tempfile
from pathlib import Path

import pandas as pd

import behav_build as bb

OUT = bb.OUT / "entry_after_T.parquet"


def main():
    s = pd.read_parquet(bb.OUT / "snapshots.parquet", columns=["condition_id", "T"])
    s = s[(s["T"] >= "2025-01-06") & (s["T"] <= "2026-03-30")]
    tmp, rows = Path(tempfile.mkdtemp(prefix="entry_")), []
    try:
        for T, ids in s.groupby("T").condition_id:
            f = bb.load_day(T.date(), tmp)
            f = f[f.condition_id.isin(set(ids))].sort_values("block_timestamp")
            g = f.assign(pv=f.p_event * f.usdc_amount).groupby("condition_id")
            a = pd.DataFrame({"p_next": g.p_event.first(), "ts_next": g.block_timestamp.first(),
                              "p_mon_vwap": g.pv.sum() / g.usdc_amount.sum()}).reset_index()
            rows.append(a.assign(T=T))
            print(T.date(), len(ids), "with a Monday fill", len(a), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pd.concat(rows, ignore_index=True).to_parquet(OUT)


if __name__ == "__main__":
    main()
