"""B7 analysis: does the prop market overreact to one game? (research/behavioral-rules.md, B7 + amendment)

Inputs: data/behav/props.parquet (behav_props.py), data/external/nba_traditional.csv (Kaggle szymonjwiak/nba-traditional).
Run:  python behav_props_analyze.py [dev|test]      (test is run ONCE, after the dev choice of k is written down)
"""
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

DEV_END, TEST_START, TEST_END = "2026-02-15", "2026-02-16", "2026-04-28"
STAT = {"points": "PTS", "rebounds": "REB", "assists": "AST"}
KS = (0.5, 1.0, 1.5)
rng = np.random.default_rng(0)


def norm(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()  # Jokić -> Jokic
    k = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "").replace(".", ""))).strip("-")
    k = re.sub(r"-(jr|sr|ii|iii|iv)$", "", k)  # suffixes are used inconsistently between slugs and box scores
    return ALIAS.get(k, k)


ALIAS = {"alexandre-sarr": "alex-sarr", "nicolas-claxton": "nic-claxton"}  # slug name -> box-score name


def boxscores():
    b = pd.read_csv("data/external/nba_traditional.csv", usecols=["date", "player", "MIN", "PTS", "REB", "AST", "season"])
    b = b[b.date >= "2025-10-01"].copy()
    b["pkey"] = b.player.map(norm)
    b = b.sort_values(["pkey", "date"])
    g = b.groupby("pkey")
    for s in ("PTS", "REB", "AST"):  # season-to-date SD over EARLIER games only (no lookahead)
        b[f"{s}_sd"] = g[s].transform(lambda x: x.shift(1).expanding(min_periods=5).std())
    b["MIN_avg"] = g["MIN"].transform(lambda x: x.shift(1).expanding(min_periods=5).mean())
    b["prev_date"] = g["date"].shift(1)
    return b


def main_lines(props):
    """One main line per player-stat-game: most pre-game $, ties broken by price closer to 0.5."""
    p = props.dropna(subset=["p_over"]).copy()
    p["dist"] = (p.p_over - 0.5).abs()
    p = p.sort_values(["usd_pre", "dist"], ascending=[False, True])
    return p.drop_duplicates(["pkey", "stat", "gdate"]).copy()


def cluster_ci(values, clusters, n=2000):
    v = pd.Series(values).reset_index(drop=True); c = pd.Series(clusters).reset_index(drop=True)
    groups = [v[c == k].to_numpy() for k in c.unique()]
    if len(groups) < 2:
        return np.nan, np.nan
    sums = np.array([g.sum() for g in groups]); cnts = np.array([len(g) for g in groups])
    bs = []
    for _ in range(n):
        i = rng.integers(0, len(groups), len(groups))
        bs.append(sums[i].sum() / cnts[i].sum())
    return np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def build_pairs():
    props = pd.read_parquet("data/behav/props.parquet")
    props["pkey"] = props.player.map(norm)
    box = boxscores()
    m = main_lines(props)
    j = m.merge(box, left_on=["pkey", "gdate"], right_on=["pkey", "date"], how="left")
    print(f"props {len(props):,}; priced main lines {len(m):,}; matched to box scores {j.PTS.notna().sum():,} "
          f"({j.PTS.notna().mean():.1%}); unmatched = did not play (over rate {j[j.PTS.isna()].y_over.mean():.3f}) "
          f"or name not in box ({(~j.pkey.isin(set(box.pkey))).sum()})")
    j["dnp"] = j.PTS.isna() & j.pkey.isin(set(box.pkey))
    # previous box-score game before each prop date (also for DNP rows, which have no box row of their own)
    bd = box[["pkey", "date"]].rename(columns={"date": "bdate"})
    j = j.sort_values("gdate")
    j["prev_date"] = pd.merge_asof(j[["pkey", "gdate"]].assign(t=pd.to_datetime(j.gdate)),
                                   bd.assign(t=pd.to_datetime(bd.bdate) + pd.Timedelta(hours=12)).sort_values("t"),
                                   on="t", by="pkey", direction="backward")["bdate"].to_numpy()
    j = j[j.PTS.notna() | j.dnp].copy()
    j["actual"] = [r[STAT[s]] for s, r in zip(j.stat, j.to_dict("records"))]
    j["sd"] = [r[f"{STAT[s]}_sd"] for s, r in zip(j.stat, j.to_dict("records"))]
    j["z"] = (j.actual - j.line) / j.sd  # NaN for DNP rows: they can be game n+1, never game n
    j["short_min"] = j.MIN < 0.6 * j.MIN_avg
    j = j.sort_values(["pkey", "stat", "gdate"])
    nxt = j.groupby(["pkey", "stat"]).shift(-1)
    pairs = pd.DataFrame({
        "player": j.pkey, "stat": j.stat, "date_n": j.gdate, "z_n": j.z, "short_min_n": j.short_min, "line_n": j.line,
        "date_n1": nxt.gdate, "prev_date_n1": nxt.prev_date, "line_n1": nxt.line, "p_over": nxt.p_over,
        "y_over": nxt.y_over, "z_n1": nxt.z, "usd_pre": nxt.usd_pre, "dnp_n1": nxt.dnp})
    pairs = pairs.dropna(subset=["date_n1", "z_n", "p_over"])
    gap = (pd.to_datetime(pairs.date_n1) - pd.to_datetime(pairs.date_n)).dt.days
    # game n must be the player's last game before n+1 (else the market saw a later game we don't model) and 1-5 days back
    pairs = pairs[(gap.between(1, 5)) & (pairs.prev_date_n1 == pairs.date_n)].copy()
    pairs["bucket"] = np.select([pairs.z_n <= -1, pairs.z_n >= 1], ["bad", "great"], "middle")
    pairs["premium"] = pairs.p_over - pairs.y_over
    return pairs


def report(pairs, label):
    print(f"\n==== {label}: {len(pairs):,} pairs, {pairs.player.nunique()} players; next game a DNP in "
          f"{pairs.dnp_n1.astype(bool).sum()} (counted: an over bet loses, an under bet wins) ====")
    normal = pairs[~pairs.short_min_n]
    print("(a) line change after game n, by bucket (normal-minutes games):")
    print(normal.assign(dL=normal.line_n1 - normal.line_n).groupby(["stat", "bucket"]).dL.agg(["mean", "count"]).round(2).to_string())
    print("(b) premium = P(over) − outcome in game n+1 (>0 = over too dear):")
    for b in ("bad", "middle", "great"):
        s = normal[normal.bucket == b]
        lo, hi = cluster_ci(s.premium, s.player)
        print(f"   {b:6} n={len(s):5}  premium {s.premium.mean():+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  "
              f"mean price {s.p_over.mean():.3f}  over rate {s.y_over.mean():.3f}")
    g, b = normal[normal.bucket == "great"], normal[normal.bucket == "bad"]
    diff, bs = g.premium.mean() - b.premium.mean(), []
    players = normal.player.unique()
    for _ in range(2000):
        pick = set(rng.choice(players, len(players)))
        gg, bb = g[g.player.isin(pick)], b[b.player.isin(pick)]
        if len(gg) and len(bb):
            bs.append(gg.premium.mean() - bb.premium.mean())
    print(f"   PRIMARY premium(great) − premium(bad) = {diff:+.4f}  95% CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]")
    c = normal.dropna(subset=["z_n1"])
    print(f"(c) real form: corr(z_n, z_n+1 actual vs line) = {c.z_n.corr(c.z_n1):+.3f} (n={len(c):,}); "
          f"over rate after bad {c[c.bucket=='bad'].y_over.mean():.3f} vs after great {c[c.bucket=='great'].y_over.mean():.3f}")
    print(f"   short-minutes stratum (not traded): n={pairs.short_min_n.sum()}, premium {pairs[pairs.short_min_n].premium.mean():+.4f}")
    rows = []
    for stats_ in (("points", "rebounds", "assists"), ("points",)):
        for k in KS:
            s = normal[(normal.stat.isin(stats_)) & (normal.z_n.abs() >= k)]
            for slip in (0.01, 0.02):
                over = s.z_n <= -k
                entry = np.where(over, s.p_over, 1 - s.p_over) + slip
                win = np.where(over, s.y_over, 1 - s.y_over)
                ret = pd.Series(win / entry - 1, index=s.index)
                ok = entry < 1
                lo, hi = cluster_ci(ret[ok], s.player[ok])
                rows.append(dict(stats="all" if len(stats_) == 3 else "points", k=k, slip=slip, bets=int(ok.sum()),
                                 mean_ret=ret[ok].mean(), ci_lo=lo, ci_hi=hi, win_rate=win[ok].mean()))
    print("S7 fade-the-last-game:"); print(pd.DataFrame(rows).round(4).to_string(index=False))
    rows_b = []
    for name, sel in (("S7b under, every line", normal.index == normal.index),
                      ("S7c under after great (z>=1)", (normal.z_n >= 1).to_numpy())):
        for stats_ in (("points", "rebounds", "assists"), ("points",)):
            s = normal[sel & normal.stat.isin(stats_).to_numpy()]
            for slip in (0.01, 0.02):
                entry = (1 - s.p_over) + slip
                ok = entry < 1
                ret = (1 - s.y_over) / entry - 1
                lo, hi = cluster_ci(ret[ok], s.player[ok])
                rows_b.append(dict(rule=name, stats="all" if len(stats_) == 3 else "points", slip=slip, bets=int(ok.sum()),
                                   mean_ret=ret[ok].mean(), ci_lo=lo, ci_hi=hi, win_rate=(1 - s.y_over[ok]).mean()))
    print("S7b/S7c buy the under:"); print(pd.DataFrame(rows_b).round(4).to_string(index=False))
    return pd.DataFrame(rows)


def main(mode="dev"):
    pairs = build_pairs()
    dev = pairs[pairs.date_n1 <= DEV_END]
    if mode == "dev":
        r = report(dev, "DEVELOPMENT")
        top = (pd.read_parquet("data/behav/props.parquet").assign(pkey=lambda d: d.player.map(norm))
               .query("gdate <= @DEV_END").groupby("pkey").usd_pre.sum().nlargest(20).index)
        panel = dev[dev.player.isin(top) & ~dev.short_min_n].groupby("player").apply(
            lambda s: pd.Series(dict(pairs=len(s), bad=(s.bucket == "bad").sum(), great=(s.bucket == "great").sum(),
                                     prem_bad=s[s.bucket == "bad"].premium.mean(), prem_great=s[s.bucket == "great"].premium.mean())))
        print("\nTop-20 player panel (development; descriptive, small n each):"); print(panel.round(3).to_string())
    else:
        test = pairs[(pairs.date_n1 >= TEST_START) & (pairs.date_n1 <= TEST_END)]
        report(test, "TEST (run once)")


if __name__ == "__main__":
    main(*sys.argv[1:2])
