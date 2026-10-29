"""B6 analysis: after a team loses game n of a series, is it underpriced for game n+1? (research/behavioral-rules.md, B6)

Input: data/behav/sports_games.parquet (behav_sports.py), data/behav/resolutions.parquet (winner from the payout;
the archive's winner label is often missing). Team ids are the slug abbreviations: slug team 1 = outcome_seq 1 (checked:
the 800 label mismatches on 6,620 games are name variants like "Braves" / "Atlanta Braves").
Run:  python behav_sports_analyze.py [dev|test]
"""
import sys

import numpy as np
import pandas as pd

from behav_analyze import boot_cells, ci

DEV_END, TEST = "2024-12-31", ("2025-01-01", "2026-04-28")


def pairs():
    g = pd.read_parquet("data/behav/sports_games.parquet")
    r = pd.read_parquet("data/behav/resolutions.parquet", columns=["condition_id", "payout"])
    g = g.merge(r, on="condition_id", how="left")
    g["ya"] = g.payout.map({"1,0": 1.0, "0,1": 0.0, "1,1": 0.5})  # team a (slug position 1) won
    x = g.slug.str.extract(r"^[a-z]+-([a-z0-9]+)-([a-z0-9]+)-")
    g["a"], g["b"] = x[0], x[1]
    g["key"] = g.league + ":" + np.where(g.a < g.b, g.a + "-" + g.b, g.b + "-" + g.a)
    g = g.dropna(subset=["ya"]).sort_values(["key", "gdate"])
    g["t"] = pd.to_datetime(g.gdate)
    nx = g.groupby("key").shift(-1)
    gap = (nx.t - g.t).dt.days
    # series id: a new series starts whenever the gap to the previous game of the same pair exceeds 4 days
    g["series"] = g.key + "#" + (g.groupby("key").t.diff().dt.days.gt(4) | g.key.ne(g.key.shift())).cumsum().astype(str)
    p = pd.DataFrame({"league": g.league, "series": g.series, "date_n": g.gdate, "date_n1": nx.gdate, "gap": gap,
                      "ya_n": g.ya, "pa_n": g.p1, "a_n": g.a, "a_n1": nx.a, "pa_n1": nx.p1, "ya_n1": nx.ya,
                      "usd_n1": nx.usd_pre})
    p = p[p.gap.between(1, 4) & p.ya_n.isin([0.0, 1.0]) & p.pa_n1.notna()].copy()
    # L = loser of game n, expressed as a slug abbreviation, then mapped onto game n+1's orientation
    loser = np.where(p.ya_n == 0, g.loc[p.index, "a"], g.loc[p.index, "b"])
    same = loser == p.a_n1
    p["pL"] = np.where(same, p.pa_n1, 1 - p.pa_n1)
    p["yL"] = np.where(same, p.ya_n1, 1 - p.ya_n1)
    p["pL_n"] = np.where(p.ya_n == 0, p.pa_n, 1 - p.pa_n)  # L's own pre-game price in game n
    p["upset"] = p.pL_n > 0.5
    p["prem"] = p.pL - p.yL
    return p


def report(p, label):
    print(f"\n==== {label}: {len(p):,} pairs, {p.series.nunique():,} series; by league {p.league.value_counts().to_dict()} ====")
    for name, s in (("all L", p), ("upset L (favourite lost game n)", p[p.upset]), ("non-upset L", p[p.pL_n <= 0.5])):
        pt, dr = boot_cells(s.series, np.zeros(len(s), int), s.prem.to_numpy(), 1)
        lo, hi = ci(dr[:, 0])
        print(f"  {name:34} n={len(s):5}  premium_L {pt[0]:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
              f"mean pL {s.pL.mean():.3f}  win rate {s.yL.mean():.3f}   (<0 = loser underpriced)")
    print("  S6 buy L before game n+1:")
    for name, s in (("all L", p), ("upset-only L", p[p.upset])):
        for slip in (0.01, 0.02):
            price = s.pL + slip
            ret = (s.yL / price - 1).to_numpy()
            pt, dr = boot_cells(s.series, np.zeros(len(s), int), ret, 1)
            lo, hi = ci(dr[:, 0])
            print(f"    {name:13} slip {slip:.2f}  n={len(s):5}  mean return {pt[0]:+.4f} [{lo:+.4f}, {hi:+.4f}]  "
                  f"median $ pre-game {s.usd_n1.median():,.0f}")
    print("  by league (all L premium):", p.groupby("league").prem.agg(["mean", "count"]).round(4).to_dict("index"))


def main(mode="dev"):
    p = pairs()
    if mode == "dev":
        report(p[p.date_n1 <= DEV_END], "DEVELOPMENT")
    else:
        report(p[(p.date_n1 >= TEST[0]) & (p.date_n1 <= TEST[1])], "TEST (run once)")


if __name__ == "__main__":
    main(*sys.argv[1:2])
