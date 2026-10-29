"""B6 data: pre-game prices for two-way league moneyline markets (research/behavioral-rules.md, B6).

Streams the binary layer of the Polymarket-v1 archive day by day and keeps only game markets
`{league}-{a}-{b}-{YYYY-MM-DD}`; for each, the VWAP of the seq-1 team's win probability in the pre-game window
[00:00 ET day before, 11:00 ET game day), plus labels and winner.

Run:  python behav_sports.py      Out: data/behav/sports_games.parquet
"""
import datetime as dt
import os
import tempfile
from zoneinfo import ZoneInfo

import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "TimeSeventeen/Polymarket-v1"
ET = ZoneInfo("America/New_York")
GAME = r"^(nba|wnba|nhl|mlb)-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})$"
COLS = ["block_timestamp", "market_slug", "condition_id", "p_event", "usdc_amount", "outcome_seq", "outcome_label",
        "winning_outcome_label"]


def window(game_date):
    d = dt.date.fromisoformat(game_date)
    lo = dt.datetime.combine(d - dt.timedelta(days=1), dt.time(0, 0), ET)
    hi = dt.datetime.combine(d, dt.time(11, 0), ET)
    return int(lo.timestamp()), int(hi.timestamp())


def main(start="2022-11-21", end="2026-04-28"):
    tmp, acc, meta = tempfile.mkdtemp(), {}, {}
    d, stop = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    local = "data/archive/daily_aligned"
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
        g = f[f.market_slug.str.match(GAME, na=False)]
        if len(g):
            parts = g.market_slug.str.extract(GAME)
            g = g.assign(league=parts[0], gdate=parts[3])
            bounds = {gd: window(gd) for gd in g.gdate.unique()}
            lo = g.gdate.map(lambda x: bounds[x][0]); hi = g.gdate.map(lambda x: bounds[x][1])
            w = g[(g.block_timestamp >= lo) & (g.block_timestamp < hi)]
            for cid, h in w.groupby("condition_id"):
                a = acc.setdefault(cid, [0.0, 0.0, 0])
                a[0] += (h.p_event * h.usdc_amount).sum(); a[1] += h.usdc_amount.sum(); a[2] += len(h)
            for cid, h in g.groupby("condition_id"):
                if cid not in meta or meta[cid]["seq1"] is None:
                    s1 = h[h.outcome_seq == 1].outcome_label
                    s2 = h[h.outcome_seq != 1].outcome_label
                    meta[cid] = dict(slug=h.market_slug.iloc[0], league=h.league.iloc[0], gdate=h.gdate.iloc[0],
                                     seq1=s1.iloc[0] if len(s1) else None, seq2=s2.iloc[0] if len(s2) else None,
                                     winner=h.winning_outcome_label.iloc[0])
        if d.day == 1:
            print(d, "game markets", len(meta), flush=True)
        d += dt.timedelta(days=1)
    rows = [dict(condition_id=c, **m, p1=(acc[c][0] / acc[c][1]) if c in acc and acc[c][1] > 0 else None,
                 usd_pre=acc.get(c, [0, 0, 0])[1], n_pre=acc.get(c, [0, 0, 0])[2]) for c, m in meta.items()]
    out = pd.DataFrame(rows)
    out.to_parquet("data/behav/sports_games.parquet")
    print("games", len(out), "with pre-game price", out.p1.notna().sum(), out.league.value_counts().to_dict())


if __name__ == "__main__":
    main()
