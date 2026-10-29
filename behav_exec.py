"""Executable check for exploration candidates: buy the named side at the first fill after T (within 24 h) and at
the VWAP of [T, T+2h), +1c, first qualifying snapshot per market, CI clustered by week.

Run:  python behav_exec.py [dev|test]
"""
import sys

import numpy as np
import pandas as pd

from behav_analyze import DEV, TEST, boot_cells, load, period
from behav_explore import GROUPS, features
from behav_round2 import ci_str

SLIP = 0.01


def ret(g, side, col):
    q = g[col].clip(0.001, 0.999)
    return ((1 - g.Y) / (1 - q + SLIP) - 1) if side == "NO" else (g.Y / (q + SLIP) - 1)


def evaluate(d, mask, side, name):
    g = d[mask.fillna(False).astype(bool)].sort_values("T").drop_duplicates("condition_id")
    out = []
    for col, ok in (("p", g.p.notna()), ("p_next", g.p_next.notna() & (g.ts_next - g.Ts < 86400)), ("p_vwap2h", g.p_vwap2h.notna())):
        h = g[ok]
        if len(h) < 30:
            out.append(f"{col} n={len(h)}"); continue
        pt, dr = boot_cells(h.date, np.zeros(len(h), int), ret(h, side, col).to_numpy(), 1)
        out.append(f"{col} n={len(h):,} {ci_str(pt[0], dr[:, 0])}")
    print(f"  {name:34} buy {side}: " + " | ".join(out))


def candidates(d):
    yes_mid = d.p.between(0.05, 0.60)
    return [
        ("up-move > 0.2", d.mom_w > 0.2, "NO"),
        ("up-move > 0.2, usd_24h > 100", (d.mom_w > 0.2) & (d.usd_24h > 100), "NO"),
        ("up-move > 0.2, persisted 24h", (d.mom_w > 0.2) & ((d.p_24h - d.prev_p) > 0.15), "NO"),
        ("up-move (0.05, 0.2]", d.mom_w.between(0.05, 0.2, "right"), "NO"),
        ("drop < -0.2", d.mom_w < -0.2, "YES"),
        ("MOMENTUM up > 0.2, usd_24h > 100", (d.mom_w > 0.2) & (d.usd_24h > 100), "YES"),
        ("MOMENTUM up > 0.1, usd_24h > 1000", (d.mom_w > 0.1) & (d.usd_24h > 1000), "YES"),
        ("MOMENTUM up (0.05,0.2], usd > 1000", d.mom_w.between(0.05, 0.2, "right") & (d.usd_24h > 1000), "YES"),
        ("MOMENTUM drop < -0.1, usd > 1000", (d.mom_w < -0.1) & (d.usd_24h > 1000), "NO"),
        ("MOMENTUM drop < -0.2, usd > 100", (d.mom_w < -0.2) & (d.usd_24h > 100), "NO"),
        ("war/strike, Yes 0.05-0.60", d.slug.str.contains(GROUPS["war/strike/invade"], na=False) & yes_mid, "NO"),
        ("celebrity, Yes 0.05-0.60", d.slug.str.contains(GROUPS["celebrity/culture"], na=False) & yes_mid, "NO"),
        ("cat Airdrops, Yes 0.05-0.60", (d.category == "Airdrops") & yes_mid, "NO"),
        ("cat US-current-affairs, 0.05-0.60", (d.category == "US-current-affairs") & yes_mid, "NO"),
        ("> 160 d to close, Yes 0.05-0.60", (d.days_to_close > 160) & yes_mid, "NO"),
        ("low attention Q1, Yes 0.05-0.60", (d.attn < d.attn.quantile(0.2)) & yes_mid, "NO"),
        ("deadline by/before, 0.05-0.60", d.slug.str.contains(GROUPS["deadline by/before"], na=False) & yes_mid, "NO"),
    ]


def main(mode="dev"):
    s = features(load())
    s = s[~s.updown]
    e = pd.read_parquet("data/behav/entry2.parquet"); e["T"] = e["T"].astype(s["T"].dtype)
    s = s.merge(e, on=["condition_id", "T"], how="left")
    s["Ts"] = s["T"].astype("int64") // (10**3 if s["T"].dt.unit == "ms" else 10**9)
    d = period(s, DEV if mode == "dev" else TEST)
    print(f"{mode}: entry coverage p_next {d.p_next.notna().mean():.1%}, vwap2h {d.p_vwap2h.notna().mean():.1%}")
    for name, m, side in candidates(d):
        evaluate(d, m, side, name)


if __name__ == "__main__":
    main(*sys.argv[1:2])
