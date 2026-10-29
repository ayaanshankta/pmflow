"""B19 aggregate caution after losses (research/behavioral-rules.md, B19).

Run:  python behav_b19.py [dev|test]
"""
import glob
import sys

import numpy as np
import pandas as pd

from behav_analyze import DEV, TEST, adjusted, boot_cells, load, period
from behav_round2 import ci_str, entries, strat

DAY = 86400


def weekly_loss():
    """Per snapshot Monday: sample wallets' hold-to-resolution losses on positions resolving in the prior 7 days / $ resolved."""
    s = pd.concat([pd.read_parquet(f, columns=["wallet", "condition_id", "side", "price", "usd", "v"])
                   for f in sorted(glob.glob("data/behav/wallets/sample_*.parquet"))], ignore_index=True)
    s = s.dropna(subset=["v"])
    vol = s.groupby("wallet").usd.sum()
    s = s[~s.wallet.isin(vol[vol >= vol.quantile(0.99)].index)]  # drop likely market makers
    s["pnl"] = s.side * s.usd * (s.v / s.price - 1)
    pos = s.groupby(["wallet", "condition_id"]).agg(pnl=("pnl", "sum"), usd=("usd", "sum")).reset_index()
    r = pd.read_parquet("data/behav/resolutions.parquet", columns=["condition_id", "res_ts"])
    pos = pos.merge(r, on="condition_id")
    # Monday that opens the 7-day window after resolution: res in [T-7d, T)
    day = pos.res_ts // DAY
    pos["T"] = pd.to_datetime((day + 7 - (day + 3) % 7) * DAY, unit="s")  # 1970-01-01 was a Thursday
    w = pos.groupby("T").agg(loss=("pnl", lambda x: -x[x < 0].sum()), usd=("usd", "sum"))
    w["L"] = w.loss / w.usd
    w.index = w.index.strftime("%Y-%m-%d")
    return w


def main(mode="dev"):
    w = weekly_loss()
    cut = period(w.reset_index().rename(columns={"T": "date"}), DEV).L.median()
    s = load()
    s = s[~s.updown & s.yesno]
    e = entries(); e["T"] = e["T"].astype(s["T"].dtype)
    s = s.merge(e, on=["condition_id", "T"], how="left")
    d = period(s, DEV if mode == "dev" else TEST)
    d = d.assign(high=d.date.map(w.L).gt(cut).astype(int))
    d = d[d.date.isin(w.index)]
    print(f"{mode}: DEV median L {cut:.4f}; weeks {d.date.nunique()} (high-loss {d[d.high == 1].date.nunique()})")
    print("  L by week, deciles:", np.round(w.L.quantile([.1, .5, .9]).to_numpy(), 4))
    f = d[d.p.between(0.70, 0.95)]
    pt, dr = adjusted(f, "high", [1, 0], "date")
    print(f"  favourites n {f.high.sum():,} high vs {(f.high == 0).sum():,}: premium {ci_str(pt[0], dr[:, 0])} vs "
          f"{ci_str(pt[1], dr[:, 1])}; diff {ci_str(pt[0] - pt[1], dr[:, 0] - dr[:, 1])} (cluster = week; prediction > 0)")
    pt, dr = adjusted(d, "high", [1, 0], "date")
    print(f"  all prices: diff {ci_str(pt[0] - pt[1], dr[:, 0] - dr[:, 1])}")
    strat(f[f.high == 1], "NO", "S19 high-loss week, favourites (cluster = market; see week-clustered check below)")
    g = f[f.high == 1].sort_values("T").drop_duplicates("condition_id")
    ret = ((1 - g.Y) / (1 - g.p + 0.01) - 1).to_numpy()
    pt, dr = boot_cells(g.date, np.zeros(len(g), int), ret, 1)
    print(f"  S19 snapshot+1c clustered by week: {ci_str(pt[0], dr[:, 0])} n={len(g):,}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
