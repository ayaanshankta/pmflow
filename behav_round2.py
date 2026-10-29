"""Round-2 market-level tests B10-B13, B18 on the snapshot table (research/behavioral-rules.md, round 2).

Run:  python behav_round2.py [dev|test]      (test once; B11's confirmatory period is DEV + 2026-04, see the rules)
"""
import re
import sys

import numpy as np
import pandas as pd

from behav_analyze import DEV, TEST, adjusted, boot_cells, ci, load, period

APR = ("2026-04-06", "2026-04-27")
PROJECT = r"release|launch|pass|passes|sign|signs|approve|approved|ipo|announce|complete|ship|open|reopen|deliver|implement|start|confirm|confirmed"
CRYPTO = r"(?:^|-)(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|dogecoin)(?:-|$)"
UP, DOWN = r"(?:^|-)(?:above|reach|hit|exceed|higher|over|ath|all-time)(?:-|$)", r"(?:^|-)(?:below|dip|fall|drop|under|lower|crash)(?:-|$)"
ROUND = np.array([.10, .20, .25, .30, .40, .50, .60, .70, .75, .80, .90])
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"


def ci_str(pt, d):
    lo, hi = ci(d)
    return f"{pt:+.4f} [{lo:+.4f}, {hi:+.4f}]"


def entries():
    e = pd.read_parquet("data/behav/entry_after_T.parquet")
    return e[["condition_id", "T", "p_mon_vwap"]]


def strat(q, side, label):
    """First qualifying snapshot per market; returns at 1c/2c from the snapshot price, and at Monday VWAP + 1c."""
    q = q.sort_values("T").drop_duplicates("condition_id")
    out = []
    for col, slips in (("p", (0.01, 0.02)), ("p_mon_vwap", (0.01,))):
        g = q.dropna(subset=[col]) if col in q else q.iloc[:0]
        for slip in slips:
            price = (1 - g[col] if side == "NO" else g[col]) + slip
            pay = 1 - g.Y if side == "NO" else g.Y
            ret = (pay / price - 1).to_numpy()
            if len(g) < 2:
                out.append(f"{col}+{slip * 100:.0f}c n={len(g)}")
                continue
            pt, dr = boot_cells(g.condition_id, np.zeros(len(g), int), ret, 1)
            out.append(f"{'snapshot' if col == 'p' else 'MonVWAP'}+{slip * 100:.0f}c n={len(g):,} {ci_str(pt[0], dr[:, 0])}")
    print(f"  {label} buy {side}: " + " | ".join(out))


def group_test(d, mask, name):
    d = d.assign(grp=mask.astype(int))
    pt, dr = adjusted(d, "grp", [1, 0], "condition_id")
    print(f"  {name}: n {mask.sum():,} vs {(~mask).sum():,}; premium {ci_str(pt[0], dr[:, 0])} vs {ci_str(pt[1], dr[:, 1])}; "
          f"diff {ci_str(pt[0] - pt[1], dr[:, 0] - dr[:, 1])}")


def b10(d):
    print("\n-- B10 planning fallacy: planned-completion deadline markets vs other deadline markets --")
    dl = d[d.slug.str.contains(r"-by-|-before-", na=False)]
    proj = dl.slug.str.contains(rf"(?:^|-)(?:{PROJECT})(?:-|$)", na=False)
    group_test(dl, proj, "project vs other deadline")
    strat(dl[proj & dl.p.between(0.10, 0.60)], "NO", "S10 project, Yes 0.10-0.60")


def b11(d):
    print("\n-- B11 crypto upside vs downside --")
    c = d[d.slug.str.contains(CRYPTO, na=False)]
    up, dn = c.slug.str.contains(UP, na=False), c.slug.str.contains(DOWN, na=False)
    c, up = c[up ^ dn], up[up ^ dn]
    if len(c) < 50:
        print("  too few", len(c)); return
    group_test(c, up, "upside vs downside")
    strat(c[up & c.p.between(0.10, 0.60)], "NO", "S11 upside, Yes 0.10-0.60")


def b12(d):
    print("\n-- B12 longshots (Yes 0.02-0.10) by days to close --")
    l = d[d.p.between(0.02, 0.10)]
    for name, m in (("<=2d", l.days_to_close <= 2), ("2-7d", l.days_to_close.between(2, 7, "right")),
                    ("7-30d", l.days_to_close.between(7, 30, "right")), (">30d", l.days_to_close > 30)):
        g = l[m]
        pt, dr = boot_cells(g.condition_id, np.zeros(len(g), int), (g.p - g.Y).to_numpy(), 1)
        print(f"  {name:6} n={len(g):6,} mean p {g.p.mean():.3f} win {g.Y.mean():.3f} premium {ci_str(pt[0], dr[:, 0])}")
    strat(l[l.days_to_close <= 7], "NO", "S12 Yes 0.02-0.10, <=7d")


def b13(d):
    print("\n-- B13 round-number prices (exact last-fill prices only) --")
    x = d[d.p_from_last_fill].copy()
    dist = np.abs(x.p.to_numpy()[:, None] - ROUND[None, :]).min(1)
    x["kind"] = np.select([dist < 0.001, (dist > 0.0095) & (dist < 0.0205)], ["round", "near"], "other")
    k = x.kind.value_counts()
    print(f"  snapshots {len(x):,}: round {k.get('round', 0):,}, neighbours (4 ticks per round price) {k.get('near', 0):,}; "
          f"ratio round/neighbour {k.get('round', 0) / max(k.get('near', 1), 1):.3f} (0.25 if prices ignored round numbers)")
    y = x[x.kind != "other"]
    group_test(y.assign(bin=y.bin), y.kind.eq("round"), "round vs neighbour")


def template(slug):
    s = re.sub(rf"(?:^|-)(?:{MONTHS}|{DAYS})(?=-|$)", "-#", slug)
    s = re.sub(r"\d+(?:pt\d+)?", "#", s)
    return re.sub(r"(?:-?#)+", "-#", s).strip("-")


def b18(s, per):
    print("\n-- B18 recency overreaction in recurring series --")
    s = s[~s.slug.str.match(r"^(nba|wnba|nhl|mlb|nfl)-", na=False)].copy()
    s["tpl"] = s.slug.map(template)
    inst = s.sort_values("T").groupby("condition_id").agg(tpl=("tpl", "first"), close=("close_at", "first"),
                                                        res_ts=("res_ts", "first"), p_last=("p", "last"), Y=("Y", "first"),
                                                        cat=("category", "first"))
    inst["cdate"] = inst.close.dt.date
    per_date = inst.groupby(["tpl", "cdate"]).size()
    single = per_date[per_date == 1].index  # ladders (several markets per template per close) are excluded
    inst = inst.reset_index().set_index(["tpl", "cdate"]).loc[lambda x: x.index.isin(single)].reset_index().sort_values(["tpl", "close"])
    nx = inst.groupby("tpl").shift(-1)
    gap = (nx.close - inst.close).dt.days
    pr = pd.DataFrame({"tpl": inst.tpl, "cat": inst.cat, "surprise": inst.Y - inst.p_last, "res_prev": inst.res_ts,
                       "next_cid": nx.condition_id})
    pr = pr[gap.between(1, 45) & pr.next_cid.notna()]
    # first snapshot of k+1 taken after k resolved
    snap = s[s.condition_id.isin(set(pr.next_cid))][["condition_id", "T", "p", "Y", "p_from_last_fill", "date"]]
    snap = snap.merge(pr[["next_cid", "res_prev", "surprise", "tpl", "cat"]], left_on="condition_id", right_on="next_cid")
    snap = snap[snap["T"].map(lambda t: t.timestamp()) >= snap.res_prev]
    snap = snap.sort_values("T").drop_duplicates("condition_id")
    snap = snap[(snap.date >= per[0]) & (snap.date <= per[1])]
    print(f"  pairs {len(snap):,} in {snap.tpl.nunique():,} templates; top templates "
          f"{snap.tpl.value_counts().head(5).to_dict()}")
    if len(snap) < 30:
        return
    prem = (snap.p - snap.Y).to_numpy(); x = snap.surprise.to_numpy()
    tpls = snap.tpl.to_numpy(); ut = np.unique(tpls); idx = {t: np.where(tpls == t)[0] for t in ut}
    def slope(i):
        X = np.c_[np.ones(len(i)), x[i]]; return np.linalg.lstsq(X, prem[i], rcond=None)[0][1]
    rng = np.random.default_rng(0)
    bs = [slope(np.concatenate([idx[t] for t in rng.choice(ut, len(ut))])) for _ in range(2000)]
    print(f"  slope of premium(k+1) on surprise(k): {ci_str(slope(np.arange(len(x))), np.array(bs))} (>0 = overreaction)")
    for name, m in (("after surprise >= +0.5 (unexpected Yes)", x >= 0.5), ("after surprise <= -0.5 (unexpected No)", x <= -0.5),
                    ("after |surprise| < 0.5", np.abs(x) < 0.5)):
        g = snap[m]
        if len(g) < 2:
            continue
        pt, dr = boot_cells(g.tpl, np.zeros(len(g), int), (g.p - g.Y).to_numpy(), 1)
        print(f"    {name:40} n={len(g):5,} premium {ci_str(pt[0], dr[:, 0])}")
    print("  by category (slope sign check): ", snap.assign(prem=prem).groupby("cat").apply(
        lambda g: round(np.corrcoef(g.surprise, g.prem)[0, 1], 3) if len(g) > 30 else None, include_groups=False).dropna().to_dict())
    snap = snap.merge(entries().assign(T=lambda e: e["T"].astype(snap["T"].dtype)), on=["condition_id", "T"], how="left")
    strat(snap[x >= 0.5], "NO", "S18 after unexpected Yes")
    strat(snap[x <= -0.5], "YES", "S18 after unexpected No")


def main(mode="dev"):
    s = load()
    s = s[~s.updown & s.yesno]
    e = entries(); e["T"] = e["T"].astype(s["T"].dtype)
    s = s.merge(e, on=["condition_id", "T"], how="left")
    per = DEV if mode == "dev" else TEST
    d = period(s, per)
    print(f"\n==== {mode.upper()} {per}: {len(d):,} snapshots ====")
    b10(d); b11(d); b12(d); b13(d); b18(s, per)
    if mode == "test":
        print("\n==== B11 confirmatory extra period 2026-04 (with DEV above) ====")
        b11(period(s, APR))


if __name__ == "__main__":
    main(*sys.argv[1:2])
