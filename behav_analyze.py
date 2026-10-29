"""B1/B2/B4/B5 + strategy S1 on the weekly snapshot table (research/behavioral-rules.md).

Inputs: data/behav/snapshots.parquet (behav_build.py), data/behav/resolutions.parquet (behav_resolutions.py).
Run:  python behav_analyze.py [dev|test]      (test is run ONCE, after the S1 cell is chosen on dev and written down)
"""
import sys

import numpy as np
import pandas as pd

DEV = ("2023-01-02", "2024-12-30")
TEST = ("2025-01-06", "2026-03-30")
BINS = [0, .02, .05, .10, .20, .30, .40, .50, .60, .70, .80, .90, .95, .98, 1.0001]
GRID = [(0.05, 0.20), (0.10, 0.40), (0.20, 0.50), (0.05, 0.50)]
B = 2000


def load():
    s = pd.read_parquet("data/behav/snapshots.parquet")
    r = pd.read_parquet("data/behav/resolutions.parquet", columns=["condition_id", "payout"])
    s = s.merge(r, on="condition_id", how="left")
    # outcome from the on-chain payout vector (index 0 = outcome_seq 1); a 1,1 split pays 0.5 each
    s["Y"] = s.payout.map({"1,0": 1.0, "0,1": 0.0, "1,1": 0.5})
    s["updown"] = s.slug.str.contains("up-or-down|updown", na=False)
    s["yesno"] = s.seq1_label.eq("Yes")
    s["bin"] = pd.cut(s.p, BINS, right=False, labels=False)
    s["event"] = s.nr_id.fillna(s.condition_id)
    s["date"] = s["T"].dt.strftime("%Y-%m-%d")
    print(f"snapshots {len(s):,}; no payout {s.Y.isna().sum()}; up-or-down {s.updown.sum():,}; "
          f"seq-1 label not Yes {(~s.yesno).sum():,} (of which unknown {s.seq1_label.isna().sum():,})")
    return s.dropna(subset=["Y", "p"])


def period(s, p):
    return s[(s.date >= p[0]) & (s.date <= p[1])]


def boot_cells(cluster, cell, value, n_cells, seed=0):
    """Cluster bootstrap of per-cell means. Returns (point (n_cells,), draws (B, n_cells))."""
    cl, ci = pd.factorize(np.asarray(cluster))[0], np.asarray(cell)
    nc = cl.max() + 1
    S = np.zeros((nc, n_cells)); N = np.zeros((nc, n_cells))
    np.add.at(S, (cl, ci), value); np.add.at(N, (cl, ci), 1)
    rng = np.random.default_rng(seed)
    draws = np.empty((B, n_cells))
    for b in range(B):
        w = np.bincount(rng.integers(0, nc, nc), minlength=nc)
        with np.errstate(invalid="ignore"):
            draws[b] = (w @ S) / (w @ N)
    with np.errstate(invalid="ignore"):
        return S.sum(0) / N.sum(0), draws


def ci(x):
    x = x[~np.isnan(x)]
    return np.percentile(x, 2.5), np.percentile(x, 97.5)


def fmt(pt, d):
    lo, hi = ci(d)
    return f"{pt:+.4f} [{lo:+.4f}, {hi:+.4f}]"


def adjusted(d, group, groups, cluster):
    """Price-bin-adjusted premium per group: bin-cell premiums weighted by the pooled bin distribution."""
    nb = len(BINS) - 1
    g = pd.Categorical(d[group], categories=groups).codes
    cell = g * nb + d.bin.to_numpy()
    pt, dr = boot_cells(d[cluster], cell, (d.p - d.Y).to_numpy(), len(groups) * nb)
    w = np.bincount(d.bin, minlength=nb) / len(d)
    def adj(m):  # empty cells (nan) drop out and the weights renormalise
        m = m.reshape(-1, len(groups), nb)
        ok = ~np.isnan(m)
        return np.where(ok, m, 0) @ w / (ok @ w)
    return adj(pt)[0], adj(dr)


def logit_slope(p, y):
    x = np.log(np.clip(p, .005, .995) / (1 - np.clip(p, .005, .995)))
    X, beta = np.c_[np.ones_like(x), x], np.zeros(2)
    for _ in range(25):  # Newton / IRLS
        mu = 1 / (1 + np.exp(-X @ beta))
        beta += np.linalg.solve(X.T @ (X * (mu * (1 - mu))[:, None]), X.T @ (y - mu))
    return beta[1]


def b1(d):
    print("\n-- B1 calibration (all markets except up-or-down; p on the outcome-1 axis) --")
    lab = [f"{BINS[i]:.2f}-{min(BINS[i + 1], 1):.2f}" for i in range(len(BINS) - 1)]
    one = d.groupby("condition_id").sample(1, random_state=0)
    t = pd.DataFrame({"n": d.groupby("bin").size(), "mean_p": d.groupby("bin").p.mean(), "win": d.groupby("bin").Y.mean(),
                      "win_per_mkt": one.groupby("bin").Y.mean(), "n_mkt": one.groupby("bin").size()})
    t.index = [lab[i] for i in t.index]
    print(t.round(4).to_string())
    print(f"logit slope: per snapshot {logit_slope(d.p.to_numpy(), d.Y.to_numpy()):.3f}, "
          f"one snapshot per market {logit_slope(one.p.to_numpy(), one.Y.to_numpy()):.3f}  (1 = calibrated; <1 = longshots overpriced)")
    hz = pd.cut(d.days_to_close, [-np.inf, 1, 7, 30, np.inf], labels=["<=1d", "1-7d", "7-30d", ">30d"])
    for name, key in (("layer", d.layer), ("horizon", hz), ("category (top 8)", d.category)):
        keep = key.value_counts().index[:8]
        rows = {k: dict(n=len(g), slope=logit_slope(g.p.to_numpy(), g.Y.to_numpy()), prem=(g.p - g.Y).mean())
                for k, g in d.groupby(key, observed=True) if k in keep}
        print(f"by {name}:"); print(pd.DataFrame(rows).T.round(3).to_string())


def b2(d, cuts):
    print("\n-- B2 PRIMARY: Yes premium by volume-to-date tercile (Yes/No markets) --")
    d = d.assign(terc=np.digitize(d.V, cuts))
    print(f"tercile cut points (dev): ${cuts[0]:,.0f}, ${cuts[1]:,.0f}")
    for k in range(3):
        g = d[d.terc == k]
        pt, dr = boot_cells(g.condition_id, np.zeros(len(g), int), (g.p - g.Y).to_numpy(), 1)
        print(f"  tercile {k} raw: n={len(g):,} mkts={g.condition_id.nunique():,} mean p {g.p.mean():.3f} premium {fmt(pt[0], dr[:, 0])}")
    for cl in ("condition_id", "event"):
        pt, dr = adjusted(d, "terc", [0, 1, 2], cl)
        print(f"  price-bin-adjusted (cluster={cl}): low {fmt(pt[0], dr[:, 0])}  mid {fmt(pt[1], dr[:, 1])}  "
              f"high {fmt(pt[2], dr[:, 2])}  low−high {fmt(pt[0] - pt[2], dr[:, 0] - dr[:, 2])}")
    t = d.groupby(["bin", "terc"]).apply(lambda g: g.p.mean() - g.Y.mean(), include_groups=False).unstack().round(4)
    t.index = [f"{BINS[i]:.2f}" for i in t.index]
    print("  premium by price bin (rows) × tercile (cols):"); print(t.to_string())


def b4(d):
    print("\n-- B4 deadline markets (-by- / -before-) vs others, Yes/No, price-bin-adjusted --")
    d = d.assign(dl=d.slug.str.contains(r"-by-|-before-", na=False).astype(int))
    pt, dr = adjusted(d, "dl", [1, 0], "condition_id")
    print(f"  n deadline {d.dl.sum():,} / other {(1 - d.dl).sum():,}: deadline {fmt(pt[0], dr[:, 0])}  other {fmt(pt[1], dr[:, 1])}  "
          f"diff {fmt(pt[0] - pt[1], dr[:, 0] - dr[:, 1])}")


def b5(d):
    print("\n-- B5 after a ≥10-pt move in the previous 24 h: premium signed by the move (>0 = overshot) --")
    g = d[(d.p - d.p_24h).abs().ge(0.10) & ~d.p_from_last_fill]
    v = np.sign(g.p - g.p_24h) * (g.p - g.Y)
    pt, dr = boot_cells(g.condition_id, np.zeros(len(g), int), v.to_numpy(), 1)
    print(f"  n={len(g):,} mkts={g.condition_id.nunique():,}: signed premium {fmt(pt[0], dr[:, 0])}")
    for side, m in (("up moves", g.p > g.p_24h), ("down moves", g.p < g.p_24h)):
        print(f"    {side}: n={m.sum():,} premium p−Y {(g.p - g.Y)[m].mean():+.4f}")


def s1(d, cuts):
    """Fade Yes (buy NO) on first qualifying snapshot per market. Returns the result table."""
    d = d.assign(terc=np.digitize(d.V, cuts)).sort_values("T")
    rows = []
    for terc_name, tsel in (("low", [0]), ("all", [0, 1, 2])):
        for side in ("NO", "YES"):
            for lo, hi in GRID:
                for stale in (True, False):
                    q = d[d.terc.isin(tsel) & d.p.between(lo, hi) & (stale | ~d.p_from_last_fill)]
                    q = q.drop_duplicates("condition_id")
                    for slip in (0.01, 0.02):
                        price = (1 - q.p if side == "NO" else q.p) + slip
                        pay = 1 - q.Y if side == "NO" else q.Y
                        fee = np.where(q.fee > 0, 0.04 * price * (1 - price), 0)  # documented taker fee, per share
                        for fee_name, f in (("0", 0), ("doc", fee)):
                            ret = (pay / price - 1 - f / price).to_numpy()
                            pt, dr = boot_cells(q.condition_id, np.zeros(len(q), int), ret, 1)
                            lo_, hi_ = ci(dr[:, 0])
                            elo, ehi = ci(boot_cells(q.event, np.zeros(len(q), int), ret, 1)[1][:, 0])
                            rows.append(dict(terc=terc_name, side=side, band=f"{lo:.2f}-{hi:.2f}", incl_stale=stale,
                                             slip=slip, fee=fee_name, n=len(q), mean_ret=pt[0], ci_lo=lo_, ci_hi=hi_, ev_lo=elo, ev_hi=ehi,
                                             win=pay.mean(), cap_med_24h=q.usd_24h.median()))
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("\n-- S1 fade Yes (terc=low, side=NO, incl_stale=True, fee=0 rows are the pre-registered rule) --")
    print(t.round(4).to_string(index=False))
    return t


def main(mode="dev"):
    s = load()
    s = s[~s.updown]
    yn = s[s.yesno]
    cuts = np.percentile(period(yn, DEV).V, [100 / 3, 200 / 3])
    d = period(s, DEV if mode == "dev" else TEST)
    print(f"\n==== {mode.upper()} {DEV if mode == 'dev' else TEST}: {len(d):,} snapshots, {d.condition_id.nunique():,} markets ====")
    b1(d)
    b2(d[d.yesno], cuts)
    b4(d[d.yesno])
    b5(d)
    t = s1(d[d.yesno], cuts)
    if mode == "dev":
        c = t[(t.terc == "low") & (t.side == "NO") & t.incl_stale & (t.slip == 0.01) & (t.fee == "0") & (t.ci_lo > 0)]
        print("\nS1 dev choice:", c.sort_values("mean_ret").iloc[-1].to_dict() if len(c) else "NO STRATEGY (no cell's CI excludes 0)")


if __name__ == "__main__":
    main(*sys.argv[1:2])
