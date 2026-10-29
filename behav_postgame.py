"""B9 data: every NBA prop fill from tip + 2 h onward (research/behavioral-rules.md, B9).

Run:  python behav_postgame.py      Out: data/behav/postgame_fills.parquet (condition_id, ts, p_event, usd)
"""
import datetime as dt
import os
import tempfile

import pandas as pd
from huggingface_hub import hf_hub_download

from behav_props import COLS, PROP, REPO


def main(start="2025-12-07", end="2026-04-28"):
    tmp, out = tempfile.mkdtemp(), []
    d, stop = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    while d <= stop:
        fn = f"daily_aligned/{d:%Y_%m_%d}.parquet"
        cached = os.path.join("data/archive", fn)
        try:
            p = cached if os.path.exists(cached) else hf_hub_download(REPO, fn, repo_type="dataset", local_dir=tmp)
            f = pd.read_parquet(p, columns=COLS)
            if not os.path.exists(cached):
                os.remove(p)
        except Exception as e:
            print(d, type(e).__name__, flush=True)
            d += dt.timedelta(days=1)
            continue
        g = f[f.market_slug.str.match(PROP, na=False)]
        g = g[g.block_timestamp >= g.close_at.astype("int64") // 10**6 + 2 * 3600]  # close_at is tip-off, in us
        out.append(g[["condition_id", "block_timestamp", "p_event", "usdc_amount"]]
                   .rename(columns={"block_timestamp": "ts", "usdc_amount": "usd"}))
        if d.day in (1, 15):
            print(d, "post-game fills so far", sum(map(len, out)), flush=True)
        d += dt.timedelta(days=1)
    pd.concat(out, ignore_index=True).to_parquet("data/behav/postgame_fills.parquet")
    print("fills", sum(map(len, out)))


if __name__ == "__main__":
    main()
