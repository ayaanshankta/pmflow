"""Exploration on DEV only (2023-01-02..2024-12-30): which observable features predict the premium p - Y?

Every feature and group tried is printed, and every one is listed in DECISIONS (the multiple-testing count).
Nothing here is a result; survivors are pre-registered and confirmed once on TEST.
Run:  python behav_explore.py [dev|test]
"""
import sys

import numpy as np
import pandas as pd

from behav_analyze import DEV, TEST, adjusted, load, period
from behav_round2 import ci_str

GROUPS = {  # slug regexes for market types where a human bias is plausible
    "mention/say": r"(?:^|-)(?:say|says|mention|mentions)(?:-|$)",
    "tweets count": r"tweet",
    "temperature": r"temperature|highest-temp",
    "box office/charts": r"box-office|opening-weekend|spotify|billboard|top-song|app-store|netflix",
    "deadline by/before": r"-by-|-before-",
    "elections/win": r"election|win-the-|nominee|primary",
    "out/resign/fired": r"(?:^|-)(?:out|resign|fired|leave|ousted|impeach)(?:-|$)",
    "war/strike/invade": r"invade|strike|ceasefire|war|attack|missile|nuclear",
    "launch/release": r"release|launch|announce",
    "celebrity/culture": r"taylor|kanye|drake|kardashian|beyonce|swift|mrbeast|diddy",
    "crypto price": r"bitcoin|btc|ethereum|eth-|solana|xrp|doge",
    "fed/rates/cpi": r"fed-|interest-rate|cpi|inflation|rate-cut|rates",
}


def features(s):
    s = s.sort_values(["condition_id", "T"]).copy()
    Ts = s["T"].astype("int64") // (10**3 if s["T"].dt.unit == "ms" else 10**9)
    s["prev_p"] = s.groupby("condition_id").p.shift()
    s["mom_w"] = s.p - s.prev_p
    s["mom_24"] = s.p - s.p_24h
    s["attn"] = s.usd_24h / (s.V + 1)
    s["stale_d"] = (Ts - s.last_ts) / 86400
    s["age_w"] = s.groupby("condition_id").cumcount()
    s["logV"] = np.log10(s.V + 1)
    return s


def show(d, mask, name):
    m = mask.fillna(False).astype(bool)
    if m.sum() < 200 or (~m).sum() < 200:
        print(f"  {name:44} n={m.sum():6,} (too few)"); return
    pt, dr = adjusted(d.assign(g=m.astype(int)), "g", [1, 0], "date")
    print(f"  {name:44} n={m.sum():6,} prem {ci_str(pt[0], dr[:, 0])}  diff vs rest {ci_str(pt[0] - pt[1], dr[:, 0] - dr[:, 1])}")


def main(mode="dev"):
    s = features(load())
    s = s[~s.updown]
    d = period(s, DEV if mode == "dev" else TEST)
    print(f"{mode}: {len(d):,} snapshots, {d.condition_id.nunique():,} markets, {d.date.nunique()} weeks; cluster = week")
    print("\n-- quintiles of continuous features (price-bin-adjusted premium; diff vs all other quintiles) --")
    for f in ("mom_w", "mom_24", "attn", "stale_d", "age_w", "logV", "days_to_close"):
        x = d[f]
        q = pd.qcut(x.rank(method="first"), 5, labels=False)
        for k in range(5):
            m = q == k
            show(d, m, f"{f} Q{k + 1} [{x[m].min():.3g}, {x[m].max():.3g}]")
    print("\n-- signed moves (week change) --")
    for lo, hi in ((-1, -0.2), (-0.2, -0.05), (0.05, 0.2), (0.2, 1)):
        show(d, d.mom_w.between(lo, hi, "right"), f"mom_w in ({lo}, {hi}]")
    print("\n-- market types --")
    for g, rx in GROUPS.items():
        show(d, d.slug.str.contains(rx, na=False), g)
    print("\n-- layers / structure --")
    show(d, d.nr_id.notna(), "neg-risk leg")
    show(d, d.p_from_last_fill, "price from exact last fill")
    show(d, d.stale_d > 7, "no fill for > 7 days")
    show(d, d.age_w == 0, "first snapshot of market")
    print("\n-- category (top 25) --")
    for c in d.category.value_counts().head(25).index:
        show(d, d.category == c, f"cat {c}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
