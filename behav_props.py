"""B7 data: NBA player-prop markets with pre-game prices (research/behavioral-rules.md, B7).

Run:  python behav_props.py      Out: data/behav/props.parquet (one row per prop market)
"""
import datetime as dt
import os
import tempfile

import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "TimeSeventeen/Polymarket-v1"
PROP = r"^nba-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})-(points|rebounds|assists)-([a-z0-9-]+?)-(\d+)pt(\d)$"
COLS = ["block_timestamp", "market_slug", "condition_id", "p_event", "usdc_amount", "close_at", "winning_outcome_label"]


def main(start="2025-10-15", end="2026-04-28"):
    tmp, acc, meta = tempfile.mkdtemp(), {}, {}
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
        if len(g):
            tip = g.close_at.astype("int64") // 10**6  # us -> s
            w = g[(g.block_timestamp >= tip - 6 * 3600) & (g.block_timestamp < tip - 300)]
            for cid, h in w.groupby("condition_id"):
                a = acc.setdefault(cid, [0.0, 0.0, 0])
                a[0] += (h.p_event * h.usdc_amount).sum(); a[1] += h.usdc_amount.sum(); a[2] += len(h)
            for cid, h in g.groupby("condition_id"):
                if cid not in meta:
                    x = pd.Series(h.market_slug.iloc[0]).str.extract(PROP).iloc[0]
                    meta[cid] = dict(slug=h.market_slug.iloc[0], team_a=x[0], team_b=x[1], gdate=x[2], stat=x[3],
                                     player=x[4], line=float(f"{x[5]}.{x[6]}"), tip=h.close_at.iloc[0],
                                     y_over=int(h.winning_outcome_label.iloc[0] == "Yes"))
        if d.day in (1, 15):
            print(d, "prop markets", len(meta), "priced", len(acc), flush=True)
        d += dt.timedelta(days=1)
    out = pd.DataFrame([dict(condition_id=c, **m, p_over=(acc[c][0] / acc[c][1]) if c in acc and acc[c][1] > 0 else None,
                             usd_pre=acc.get(c, [0, 0, 0])[1], n_pre=acc.get(c, [0, 0, 0])[2]) for c, m in meta.items()])
    out.to_parquet("data/behav/props.parquet")
    print("props", len(out), "with pre-game price", out.p_over.notna().sum(), "players", out.player.nunique(),
          "dates", out.gdate.min(), "..", out.gdate.max())


if __name__ == "__main__":
    main()
