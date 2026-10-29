"""B20 multi-outcome overround baskets at an achievable price (research/behavioral-rules.md, B20).

Run:  python behav_b20.py [dev|test]
"""
import sys

import numpy as np
import pandas as pd

from behav_analyze import TEST, boot_cells, load
from behav_round2 import ci_str, entries

DEV = ("2023-12-22", "2024-12-30")


def baskets(s, full):
    """One row per complete (nr_id, T): legs, sum of prices, payouts."""
    m = s[s.nr_id.notna()].copy()
    legs = full[full.nr_id.notna()].groupby("nr_id").apply(lambda g: g[["condition_id", "res_ts"]].drop_duplicates("condition_id"),
                                    include_groups=False).reset_index(level=0)
    m["Ts"] = m["T"].astype("int64") // 10**3 if m["T"].dt.unit == "ms" else m["T"].astype("int64") // 10**9
    open_n = (m[["nr_id", "Ts"]].drop_duplicates().merge(legs, on="nr_id")
              .query("res_ts > Ts").groupby(["nr_id", "Ts"]).size().rename("n_open"))
    g = m.groupby(["nr_id", "Ts"])
    b = g.size().rename("k").to_frame().join(open_n)
    print(f"  event-snapshots {len(b):,}; complete {(b.k == b.n_open).sum():,}")
    return m.join(b, on=["nr_id", "Ts"]).query("k == n_open")


def slip(p):
    return np.where((p >= 0.05) & (p <= 0.95), 0.01, 0.001)


def run(m, price, label):
    m = m.dropna(subset=[price]) if price != "p" else m
    if price != "p":  # every leg needs a Monday VWAP
        m = m[m.groupby(["nr_id", "Ts"]).condition_id.transform("size") == m.k]
    p = m[price].clip(0.001, 0.999)
    m = m.assign(pp=p, s=slip(p))
    e = m.groupby(["nr_id", "Ts"]).agg(O=("pp", lambda x: x.sum() - 1), k=("pp", "size"), sY=("Y", "sum"),
                                        no_cost=("pp", lambda x: (1 - x).sum()), yes_cost=("pp", "sum"),
                                        sl=("s", "sum"), last_res=("res_ts", "max"), date=("date", "first")).reset_index()
    e["no_pay"], e["days"] = e.k - e.sY, (e.last_res - e.Ts) / 86400
    print(f"\n  [{label}] complete baskets {len(e):,}; ΣY: {e.sY.round(2).value_counts().head(4).to_dict()}; "
          f"O quantiles {e.O.quantile([.1, .5, .9]).round(3).tolist()}")
    for side, sign in (("NO", 1), ("YES", -1)):
        for th in (0.02, 0.05, 0.10):
            q = e[sign * e.O >= th].sort_values("Ts").drop_duplicates("nr_id")
            if len(q) < 2:
                print(f"    {side} basket O {'>=' if sign > 0 else '<='} {sign * th:+.2f}: n={len(q)}"); continue
            pay, cost = (q.no_pay, q.no_cost) if side == "NO" else (q.sY, q.yes_cost)
            out = []
            for name, c in (("0c", cost), ("slip", cost + q.sl)):
                r = (pay / c - 1).to_numpy()
                pt, dr = boot_cells(q.date, np.zeros(len(q), int), r, 1)
                out.append(f"{name} {ci_str(pt[0], dr[:, 0])}")
            print(f"    {side} basket O {'>=' if sign > 0 else '<='} {sign * th:+.2f}: n={len(q):,} legs med {q.k.median():.0f} "
                  f"days med {q.days.median():.0f}; " + " | ".join(out) + " (cluster = week)")


def main(mode="dev"):
    s = load()
    per = DEV if mode == "dev" else TEST
    m = baskets(s[(s.date >= per[0]) & (s.date <= per[1])], s)  # leg lists come from the whole table
    run(m, "p", "snapshot last-fill prices")
    if mode == "test":
        e = entries(); e["T"] = e["T"].astype(m["T"].dtype)
        run(m.merge(e, on=["condition_id", "T"], how="left"), "p_mon_vwap", "Monday VWAP (executable)")


if __name__ == "__main__":
    main(*sys.argv[1:2])
