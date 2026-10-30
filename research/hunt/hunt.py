import sys; sys.path.insert(0, "/Users/ayaanshankta/Downloads/pmflow")
import numpy as np, pandas as pd
import behav_herd as h
from behav_analyze import boot_cells
from behav_round2 import ci_str, CRYPTO
from behav_explore import GROUPS
b = h.load()
meta = pd.read_parquet("data/behav/snapshots.parquet", columns=["condition_id", "slug", "category", "nr_id", "close_at"]).drop_duplicates("condition_id")
b = b.merge(meta, on="condition_id", how="inner")
ca = b.close_at.astype("int64") // (10**3 if b.close_at.dt.unit == "ms" else 10**6 if b.close_at.dt.unit == "us" else 10**9)
b["sched_left"] = (ca - b.last_ts) / 86400
b = b[(b.close_at < pd.Timestamp("2026-04-15", tz="UTC")) & (b.sched_left > 1)].copy()
b["crypto"] = b.slug.str.contains(CRYPTO, na=False) | b.category.isin(["Crypto", "Bitcoin", "Ethereum", "Crypto Prices", "Solana", "XRP", "Up or Down"])
b["sports"] = b.slug.str.match(r"^(nba|nfl|nhl|mlb|wnba|epl|ucl|cbb|cfb|lal|sea|bun|fl1|mls|atp|wta)-", na=False) | b.category.isin(["Sports", "NBA", "NFL", "Soccer", "Tennis", "NHL", "MLB", "Esports"])
b = b[~b.slug.str.contains("up-or-down|updown", na=False)]
g = b.groupby("condition_id")
b["move"] = b.close - b.open
b["prev_close"] = g.close.shift()
b["dmove"] = b.close - b.prev_close
b["vol7"] = g.usd.transform(lambda x: x.shift().rolling(7, min_periods=3).mean())
b["spike"] = b.usd / (b.vol7 + 1)
b["age"] = g.cumcount()
b["dow"] = pd.to_datetime(b.day).dt.dayofweek
# short-horizon exit: close 7 market-days later (or resolution value if it resolves first)
b["c7"] = g.close.shift(-7)
b["res_week"] = pd.to_datetime(b.res_ts, unit="s").dt.to_period("W").astype(str)
b = b[b.next_open.between(0.05, 0.95)]
N = [0]
def cell(x, name, side="NO"):
    N[0] += 1
    x = x.drop_duplicates("condition_id")
    if len(x) < 80: print(f"  {name:50} n={len(x)}"); return
    q = x.next_open
    prem = (q - x.Y) if side == "NO" else (x.Y - q)  # edge in probability points before costs
    r = h.trade(x, side, "next_open").to_numpy()
    pt, dr = boot_cells(x.res_week, np.zeros(len(x), int), prem.to_numpy() - 0.01, 1)
    rt, rd = boot_cells(x.res_week, np.zeros(len(x), int), r, 1)
    t = r < np.quantile(r, 0.99)
    tt, td = boot_cells(x.res_week[t], np.zeros(t.sum(), int), r[t], 1)
    sh = x.c7.where(x.c7.notna(), x.Y)
    s7 = ((q - sh) if side == "NO" else (sh - q)) - 0.02  # 7-day round trip, 1c each way
    st, sd = boot_cells(x.week, np.zeros(len(x), int), s7.to_numpy(), 1)
    print(f"  {name:50} n={len(x):6,} {side} edge-1c {ci_str(pt[0], dr[:,0])} | ret {ci_str(rt[0], rd[:,0])} | trim1% {ci_str(tt[0], td[:,0])} | 7d pts {ci_str(st[0], sd[:,0])}")
liq = b.usd > 1e3
for per, m in (("DEV 2023-24", b.day < "2025"), ("2025-26", b.day >= "2025")):
    print("\n==", per)
    x = b[m & liq]; o = x[~x.crypto & ~x.sports]; ob = o[o.nr_id.isna()]
    print("-- daily jumps (intraday close-open) --")
    for th in (0.10, 0.20):
        cell(o[o.move > th], f"other, jump up > {th}", "NO"); cell(o[o.move < -th], f"other, drop > {th}", "YES")
        cell(x[x.sports & (x.move > th)], f"sports, jump up > {th}", "NO"); cell(x[x.sports & (x.move < -th)], f"sports, drop > {th}", "YES")
    print("-- attention spikes (usd / prior 7-day mean) --")
    for th in (5, 20):
        cell(o[o.spike > th], f"other, spike > {th}x, buy No"); cell(o[(o.spike > th) & (o.move > 0.05)], f"other, spike > {th}x & up, buy No")
        cell(o[(o.spike > th) & (o.move < -0.05)], f"other, spike > {th}x & down, buy Yes", "YES")
    print("-- deadline markets (by/before) --")
    dl = ob[ob.slug.str.contains(r"-by-|-before-|-in-20\d\d", na=False)]
    for lo, hi in ((1, 7), (7, 30), (30, 1e9)):
        for plo, phi in ((0.05, 0.2), (0.2, 0.5), (0.5, 0.95)):
            cell(dl[dl.sched_left.between(lo, hi, "left") & dl.next_open.between(plo, phi, "left")], f"deadline, {lo}-{hi:.0f}d left, Yes {plo}-{phi}")
    print("-- market types (binary other) --")
    for k, rx in GROUPS.items():
        cell(ob[ob.slug.str.contains(rx, na=False)], f"type {k}")
    print("-- age / weekday --")
    cell(ob[ob.age == 0], "binary other, first liquid day"); cell(ob[ob.age >= 10], "binary other, day 10+")
    cell(ob[ob.dow >= 5], "binary other, weekend"); cell(ob[ob.dow < 5], "binary other, weekday")
    print("-- longshot Yes in binary other --")
    for plo, phi in ((0.05, 0.1), (0.1, 0.2), (0.8, 0.9), (0.9, 0.95)):
        cell(ob[ob.next_open.between(plo, phi, "left")], f"binary other, Yes {plo}-{phi}")
print("cells", N[0])
