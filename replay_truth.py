"""Latency replay on fills only (Truth Social posts, Result-2 pairs). Rules: research/ml-rules.md section B (pre-registered).
Run: /opt/anaconda3/bin/python3 replay_truth.py  -> results/replay_trades.csv, results/replay_summary.json, prints the table.
Point-in-time: the entry reads only trades at/after t0+delta, the direction signal reads only the post text (lexicon) or,
for the oracle, the first post-t0 trade (deliberate look-ahead = upper bound). Nothing else is peeked at."""
import json, sys
import numpy as np, pandas as pd

DELTAS, FEES, NOTIONAL = (2, 10, 30), (0.0, 0.01, 0.02), 500.0
LIQ_MIN, FILL_WITHIN, EXIT_LO, EXIT_HI = 50, 60, 720, 1080   # fills in prior hour; s; s after t0
B, SEED = 1000, 0


def fill_exit(ts, ps, t0, delta):
    """-> (reason, p_in, p_out). reason in {'ok','nofill','noexit'}. ts sorted trade times (s), ps prices on the p_event axis."""
    t = t0 + delta
    i = int(np.searchsorted(ts, t, "left"))
    if i >= len(ts) or ts[i] > t + FILL_WITHIN:
        return "nofill", np.nan, np.nan
    lo, hi = int(np.searchsorted(ts, t0 + EXIT_LO, "left")), int(np.searchsorted(ts, t0 + EXIT_HI, "right"))
    if hi <= lo:
        return "noexit", ps[i], np.nan
    return "ok", float(ps[i]), float(ps[hi - 1])


def pnl(sign, p_in, p_out, fee, notional=NOTIONAL):
    """sign +1 = buy YES at p_in, -1 = buy NO at 1-p_in (the same move, mirrored). Fee = fee x traded value on each side.
    -> (points per share in cents after fees, dollars on `notional`)."""
    c_in, v_out = (p_in, p_out) if sign > 0 else (1 - p_in, 1 - p_out)
    if c_in <= 0: return np.nan, np.nan
    sh = notional / c_in
    usd = sh * (v_out - c_in) - fee * notional - fee * sh * v_out
    return 100 * usd / sh, usd


def oracle_dir(ts, ps, t0):
    """sign of (first trade at/after t0) - (mean of last 5 trades before t0); 0 if none/equal."""
    i = int(np.searchsorted(ts, t0, "left"))
    if i == 0 or i >= len(ts): return 0
    return int(np.sign(ps[i] - ps[max(0, i - 5):i].mean()))


def lexicon_dir(text, slug):
    """LABELS.md keyword baseline (map.keyword_dir) on the post text and the slug as the question; backtest_truth.py's
    lexicon only gives topics, not direction, so this is the repo's only committed text->direction rule."""
    import map as M
    t = text.lower()
    themes = [k for k, (ev, _) in M.LEXICON.items() if M.re.search(ev, t)]
    return {"up": 1, "down": -1, "none": 0}[M.keyword_dir(text, "unscheduled", themes, slug.replace("-", " "))]


def boot(ev_sum, ev_n, rng):
    """cluster bootstrap over events of the trade-weighted mean; ev_sum/ev_n per event (arrays)."""
    k = len(ev_n)
    if k == 0 or ev_n.sum() == 0: return [np.nan, np.nan]
    idx = rng.randint(0, k, (B, k))
    n = ev_n[idx].sum(1)
    m = ev_sum[idx].sum(1)[n > 0] / n[n > 0]
    return list(np.percentile(m, [2.5, 97.5]))


def run(P, g, text_of):
    """P: rows event/rank/cid/kind/t0/slug/post_id. g: cid -> (ts, ps). Returns (trades df, counts df)."""
    rows, cnt = [], {}
    bump = lambda k, c: cnt.__setitem__((k, c), cnt.get((k, c), 0) + 1)
    for r in P.itertuples():
        ts, ps = g[r.cid]
        k = r.kind
        bump(k, "pairs")
        if np.searchsorted(ts, r.t0, "left") - np.searchsorted(ts, r.t0 - 3600, "left") < LIQ_MIN:
            bump(k, "illiquid"); continue
        bump(k, "liquid")
        # the lexicon direction is a property of the (post, market): it is held fixed at the placebo times
        dirs = {"lexicon": lexicon_dir(text_of[r.post_id], r.slug), "oracle": oracle_dir(ts, ps, r.t0)}
        for arm, d in dirs.items():
            if d == 0: bump((k, arm), "no_direction"); continue
            for dl in DELTAS:
                why, p_in, p_out = fill_exit(ts, ps, r.t0, dl)
                if why != "ok": bump((k, arm, dl), why); continue
                row = dict(kind=k, arm=arm, delta=dl, event=r.event, rank=r.rank, t0=r.t0, sign=d, p_in=p_in, p_out=p_out)
                for f in FEES:
                    row[f"pts_{f:g}"], row[f"usd_{f:g}"] = pnl(d, p_in, p_out, f)
                rows.append(row)
    return pd.DataFrame(rows), cnt


def table(T):
    rng = np.random.RandomState(SEED); out = []
    for (kind, arm, dl, f), d in ((k + (f,), d) for k, d in T.groupby(["kind", "arm", "delta"]) for f in FEES):
        pts, usd = d[f"pts_{f:g}"], d[f"usd_{f:g}"]
        g = d.assign(p=pts).groupby("event").p.agg(["sum", "count"])
        gu = d.assign(p=usd).groupby("event").p.sum()
        lo, hi = boot(g["sum"].values, g["count"].values, np.random.RandomState(SEED))
        ulo, uhi = boot(gu.values, g["count"].values, np.random.RandomState(SEED))
        out.append(dict(kind=kind, arm=arm, delta=dl, fee=f, n=len(d), n_events=len(g), hit=float((usd > 0).mean()),
                        pts=float(pts.mean()), pts_lo=lo, pts_hi=hi, usd=float(usd.mean()), usd_lo=ulo, usd_hi=uhi))
    return pd.DataFrame(out)


def verdict(R):
    """Pre-registered bar: lexicon arm, event kind, fee 1 %: mean > 0, CI excludes 0 (lo > 0), n >= 100. Per delta."""
    v = {}
    for dl in DELTAS:
        x = R[(R.kind == "event") & (R.arm == "lexicon") & (R.fee == 0.01) & (R.delta == dl)]
        v[dl] = bool(len(x) and x.pts.iloc[0] > 0 and x.pts_lo.iloc[0] > 0 and x.n.iloc[0] >= 100)
    return v


def main():
    import backtest_truth as BT
    m = BT.load_posts(); ev = BT.select_events(m)
    P, _ = BT.build(ev, m)   # same events, pairs, placebo generator and seeds as Result 2
    P = P[P.kind.isin(["event", "placebo"])]
    f = pd.read_parquet(BT.CACHE)
    g = {c: (d.block_timestamp.values, d.p_event.values) for c, d in f.groupby("condition_id")}
    text_of = dict(zip(ev.id, ev.text))
    T, cnt = run(P, g, text_of)
    T.to_csv("results/replay_trades.csv", index=False)
    R = table(T); V = verdict(R)
    C = {f"{'|'.join(map(str, k)) if isinstance(k, tuple) else k}:{c}": n for (k, c), n in cnt.items()}
    json.dump(dict(counts=C, table=R.to_dict("records"), verdict={str(k): v for k, v in V.items()}),
              open("results/replay_summary.json", "w"), indent=1, default=float)
    print(R.to_string()); print(json.dumps(C, indent=1)); print("verdict", V)


if __name__ == "__main__":
    main()
