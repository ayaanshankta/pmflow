"""Wallet tests B14-B17 (research/behavioral-rules.md, round 2) on data/behav/wallets (behav_wallets.py).

Run:  python behav_wallet_analyze.py
"""
import glob
from collections import defaultdict

import numpy as np
import pandas as pd

from behav_analyze import boot_cells, ci

W = "data/behav/wallets"
DAY = 86400


def mean_ci(v, cluster=None):
    v = np.asarray(v, float)
    pt, dr = boot_cells(np.arange(len(v)) if cluster is None else cluster, np.zeros(len(v), int), v, 1)
    lo, hi = ci(dr[:, 0])
    return f"{pt[0]:+.4f} [{lo:+.4f}, {hi:+.4f}] n={len(v):,}"


def per_period(a, year):
    """Per wallet in a calendar year of trading: $ and fills (all), return = PnL / $ on resolved fills."""
    x = a[a.month.str.startswith(year)]
    res = x[x.res_month != "none"]
    g = x.groupby("wallet")[["usd", "n"]].sum()
    r = res.groupby("wallet")[["usd", "pnl"]].sum()
    g["ret"] = r.pnl / r.usd
    g["pnl"] = r.pnl
    return g.dropna(subset=["ret"])


def b15_b16(a):
    p1, p2 = per_period(a, "2024"), per_period(a, "2025")
    print("\n-- B15 illusion of skill: 2024 return vs 2025 return (wallets >= $1,000 and >= 20 fills in both) --")
    ok = lambda p: p[(p.usd >= 1000) & (p.n >= 20)]
    j = ok(p1).join(ok(p2), lsuffix="1", rsuffix="2", how="inner")
    rng = np.random.default_rng(0)
    rho = j.ret1.corr(j.ret2, method="spearman")
    rk1, rk2 = j.ret1.rank().to_numpy(), j.ret2.rank().to_numpy()
    bs = [np.corrcoef(rk1[i], rk2[i])[0, 1] for i in (rng.integers(0, len(j), len(j)) for _ in range(2000))]
    lo, hi = ci(np.array(bs))
    print(f"  wallets {len(j):,}; Spearman {rho:+.3f} [{lo:+.3f}, {hi:+.3f}] (rank-corr bootstrap over wallets)")
    j["dec1"] = pd.qcut(j.ret1.rank(method="first"), 10, labels=False)
    for d in (0, 9):
        g = j[j.dec1 == d]
        print(f"  P1 decile {d + 1:2}: P1 mean ret {g.ret1.mean():+.3f}; P2 mean ret {mean_ci(g.ret2)}; "
              f"P2 pooled PnL/$ {g.pnl2.sum() / g.usd2.sum():+.4f}")
    print(f"  all joined wallets: P2 mean ret {mean_ci(j.ret2)}")
    hit = j[j.dec1 == 9]
    print(f"  P1 top decile still above P2 median: {(hit.ret2 > j.ret2.median()).mean():.1%} (50% = no persistence)")

    print("\n-- B16 overtrading: 2025 return by decile of fill count (wallets >= $1,000) --")
    q = p2[p2.usd >= 1000].copy()
    top = q.usd >= q.usd.quantile(0.99)
    print(f"  top 1% by $ (likely market makers) n={top.sum():,}: mean ret {mean_ci(q.ret[top])}; "
          f"pooled PnL/$ {q.pnl[top].sum() / q.usd[top].sum():+.4f}; share of $ {q.usd[top].sum() / q.usd.sum():.1%}")
    r = q[~top].copy()
    r["dec"] = pd.qcut(r.n.rank(method="first"), 10, labels=False)
    for d, g in r.groupby("dec"):
        print(f"  decile {d + 1:2} fills {int(g.n.min()):>7,}-{int(g.n.max()):>9,}  mean ret {mean_ci(g.ret)}  "
              f"median {g.ret.median():+.4f}  pooled {g.pnl.sum() / g.usd.sum():+.4f}")
    lo_, hi_ = r[r.dec == 0].ret.to_numpy(), r[r.dec == 9].ret.to_numpy()
    d = [rng.choice(hi_, len(hi_)).mean() - rng.choice(lo_, len(lo_)).mean() for _ in range(2000)]
    print(f"  top - bottom decile mean ret {hi_.mean() - lo_.mean():+.4f} [{ci(np.array(d))[0]:+.4f}, {ci(np.array(d))[1]:+.4f}] "
          f"(prediction < 0)")


def b14_b17(s, px, res):
    """Average-cost positions per (wallet, token) from the sample wallets' fills, in time order."""
    s = s.sort_values(["wallet", "ts"], kind="stable")
    w, ts, cid, seq = s.wallet.to_numpy(), s.ts.to_numpy(), s.condition_id.to_numpy(), s.outcome_seq.to_numpy()
    price, side, usd, v = s.price.to_numpy(), s.side.to_numpy(), s.usd.to_numpy(), s.v.to_numpy()
    days = (ts // DAY).astype(np.int64)
    code = pd.factorize(cid)[0]  # condition id as a number, to drop the resolving market's own buys (B17 post-hoc)
    pgr = defaultdict(lambda: np.zeros(4))  # realized gain, realized loss, paper gain, paper loss
    events, buys = [], defaultdict(list)    # resolved-position events; per wallet (ts, price, usd)
    starts = np.r_[0, np.flatnonzero(w[1:] != w[:-1]) + 1, len(w)]
    for a, b in zip(starts[:-1], starts[1:]):
        wal, pos = w[a], {}                # token -> [shares, cost, payout]
        i = a
        while i < b:
            j = i
            while j < b and days[j] == days[i]:
                j += 1
            sold = set()
            for k in range(i, j):          # one day of fills
                tok, sh = (cid[k], seq[k]), usd[k] / price[k]
                p = pos.setdefault(tok, [0.0, 0.0, v[k], code[k]])
                if side[k] == 1:
                    p[0] += sh; p[1] += usd[k]
                    buys[wal].append((ts[k], price[k], usd[k], code[k]))
                elif p[0] > 1e-9:          # sells with no long position (minted inventory) are skipped
                    avg, q = p[1] / p[0], min(sh, p[0])
                    pgr[wal][0 if price[k] > avg else 1] += 1
                    sold.add(tok)
                    p[1] -= q * avg; p[0] -= q
            if sold:                       # paper gains/losses: other open positions with a price that day
                for tok, p in pos.items():
                    if tok in sold or p[0] <= 1e-9:
                        continue
                    pe = px.get((days[i], tok[0]))
                    if pe is None:
                        continue
                    cur = pe if tok[1] == 1 else 1 - pe
                    if cur != p[1] / p[0]:
                        pgr[wal][2 if cur > p[1] / p[0] else 3] += 1
            i = j
        for tok, p in pos.items():         # held to resolution
            rt = res.get(tok[0])
            if rt is None or p[0] <= 1e-9 or p[1] < 20:
                continue
            if not np.isnan(p[2]):
                events.append((wal, rt, p[2] * p[0] > p[1], p[3]))

    print("\n-- B14 disposition effect (sample wallets; PGR vs PLR) --")
    t = pd.DataFrame.from_dict(pgr, orient="index", columns=["rg", "rl", "pg", "pl"])
    tot = t.sum()
    print(f"  wallets {len(t):,}; realized gains {tot.rg:,.0f} losses {tot.rl:,.0f}; paper gains {tot.pg:,.0f} losses {tot.pl:,.0f}")
    print(f"  pooled PGR {tot.rg / (tot.rg + tot.pg):.4f}  PLR {tot.rl / (tot.rl + tot.pl):.4f}")
    t = t[(t.rg + t.pg > 0) & (t.rl + t.pl > 0)]
    diff = (t.rg / (t.rg + t.pg) - t.rl / (t.rl + t.pl)).to_numpy()
    print(f"  per-wallet PGR - PLR (wallets with both): {mean_ci(diff)}  (prediction > 0)")
    S, N = t[["rg", "rl", "pg", "pl"]].to_numpy(), len(t)
    rng = np.random.default_rng(0)
    pooled = lambda x: x[0] / (x[0] + x[2]) - x[1] / (x[1] + x[3])
    bs = [pooled(S[rng.integers(0, N, N)].sum(0)) for _ in range(2000)]
    print(f"  pooled PGR - PLR over these wallets {pooled(S.sum(0)):+.4f} [{ci(np.array(bs))[0]:+.4f}, {ci(np.array(bs))[1]:+.4f}] (bootstrap over wallets)")

    print("\n-- B17 break-even effect: $-weighted buy price 7 d after vs 7 d before a resolved >= $20 position --")
    rows = []
    bw = {k: np.array(x) for k, x in buys.items()}
    m = lambda y: (y[:, 1] * y[:, 2]).sum() / y[:, 2].sum()
    for wal, rt, win, c in events:
        x = bw[wal]
        bef, aft = x[(x[:, 0] >= rt - 7 * DAY) & (x[:, 0] < rt)], x[(x[:, 0] > rt) & (x[:, 0] <= rt + 7 * DAY)]
        if len(bef) and len(aft):
            other = bef[bef[:, 3] != c]  # post-hoc: before-window without the resolving market's own buys
            rows.append((wal, win, m(aft) - m(bef), m(aft) - m(other) if len(other) else np.nan))
    e = pd.DataFrame(rows, columns=["wallet", "win", "d", "d_other"])
    print(f"  events with buys on both sides: {len(e):,} (wins {e.win.sum():,}, losses {(~e.win).sum():,}) in {e.wallet.nunique():,} wallets")
    for name, g in (("after loss", e[~e.win]), ("after win", e[e.win])):
        print(f"  {name:10} mean change in buy price {mean_ci(g.d, g.wallet)} (cluster = wallet)")
    pw = e.groupby(["wallet", "win"]).d.mean().unstack().dropna()
    print(f"  paired within wallet (after loss - after win): {mean_ci(pw[False] - pw[True])}  (prediction < 0)")
    print("  POST-HOC (pre-registered 'before' includes the resolving market's own buys, so losers - cheap longshots - "
          "mechanically pull 'before' down): before-window excluding that market")
    e = e.dropna(subset=["d_other"])
    for name, g in (("after loss", e[~e.win]), ("after win", e[e.win])):
        print(f"  {name:10} {mean_ci(g.d_other, g.wallet)}")
    pw = e.groupby(["wallet", "win"]).d_other.mean().unstack().dropna()
    print(f"  paired within wallet (after loss - after win): {mean_ci(pw[False] - pw[True])}")


def main():
    cols = ["wallet", "month", "res_month", "usd", "pnl", "n"]
    a = pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(glob.glob(f"{W}/agg_202[45]_*.parquet"))], ignore_index=True)
    b15_b16(a)
    del a
    s = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{W}/sample_*.parquet"))], ignore_index=True)
    p = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{W}/px_*.parquet"))], ignore_index=True)
    p["d"] = pd.to_datetime(p.day).values.astype("datetime64[D]").astype(np.int64)
    px = dict(zip(zip(p.d.to_numpy(), p.condition_id.to_numpy()), p.p_event.to_numpy()))
    r = pd.read_parquet("data/behav/resolutions.parquet", columns=["condition_id", "res_ts"])
    b14_b17(s, px, dict(zip(r.condition_id, r.res_ts)))


if __name__ == "__main__":
    main()
