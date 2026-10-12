"""Build (headline, market) pairs with labels dp15 / y_move / y_dir + placebo rows + fixed time split. Rules: research/ml-rules.md section A.
Run: /opt/anaconda3/bin/python3 ml_fetch.py && /opt/anaconda3/bin/python3 ml_dataset.py    -> data/ml_pairs.parquet
Labels: dp15 = last fill p_event in [t0+12m, t0+18m] - mean of last 5 fills before t0 (NaN -> drop); y_move = |dp15| >= 0.02; y_dir = sign(dp15) on movers."""
import datetime as dt, glob, json, os, sys
import numpy as np, pandas as pd
import lexicon as L
DAY, TOP, MIN_FILLS, THR = 86400, 5, 20, 0.02
TS = lambda y, m, d, H=0: int(dt.datetime(y, m, d, H, tzinfo=dt.UTC).timestamp())
T_LO, T_END = TS(2022, 11, 1), TS(2026, 4, 27, 23)          # headline window (last hour margin: archive ends 2026-04-28)
SPLITS = [("train", TS(2022, 11, 1), TS(2025, 10, 1)), ("val", TS(2025, 10, 1), TS(2026, 1, 1)), ("test", TS(2026, 1, 1), T_END + 1)]
def split_of(t):
    """UTC-time split rule, fixed in ml-rules.md: train 2022-11-01..2025-09-30, val 2025-10-01..2025-12-31, test 2026-01-01..2026-04-27."""
    for n, a, b in SPLITS:
        if a <= t < b: return n
    return None

def label_times(ts, ps, T):
    """ts sorted int seconds, ps prices (same market); T array of reference times. Returns dict of arrays (NaN where undefined)."""
    T = np.asarray(T, dtype=np.int64); cs = np.concatenate([[0.0], np.cumsum(ps, dtype=np.float64)])
    i0 = np.searchsorted(ts, T, "left"); n = np.minimum(5, i0)
    with np.errstate(invalid="ignore", divide="ignore"): p0 = np.where(n > 0, (cs[i0] - cs[i0 - n]) / np.maximum(n, 1), np.nan)
    lo = np.searchsorted(ts, T + 720, "left"); hi = np.searchsorted(ts, T + 1080, "right")
    plast = np.where(hi > lo, ps[np.maximum(hi - 1, 0)], np.nan)
    return dict(p0=p0, dp15=plast - p0, n7d=i0 - np.searchsorted(ts, T - 7 * DAY, "left"), pre60=i0 - np.searchsorted(ts, T - 3600, "left"))

def recent_move_rate(ts, ps, T, step=6 * 3600, k=28):
    """Share of the k past reference times (T - step*j, j=1..k; label window ends <= T) whose |dp15| >= THR; NaN if none defined."""
    T = np.asarray(T, dtype=np.int64); G = (T[:, None] - step * np.arange(1, k + 1)[None, :]).ravel()
    d = np.abs(label_times(ts, ps, G)["dp15"]).reshape(len(T), k)
    ok = ~np.isnan(d)
    with np.errstate(invalid="ignore", divide="ignore"): return np.where(ok.sum(1) > 0, ((d >= THR) & ok).sum(1) / ok.sum(1), np.nan)

def draw_placebo(rng, t0, ts, exclude_sorted, hi_ok, tries=10):
    """Random time within +-3d of t0 on this market: >=1 h from any matched headline, <= hi_ok, liquidity rule (>=20 fills in prior 7d), label window non-empty. None if none valid."""
    c = rng.randint(t0 - 3 * DAY, t0 + 3 * DAY + 1, size=tries).astype(np.int64)
    k = np.searchsorted(exclude_sorted, c)
    near = np.zeros(tries, bool)
    if len(exclude_sorted):
        a = exclude_sorted[np.minimum(k, len(exclude_sorted) - 1)]; b = exclude_sorted[np.maximum(k - 1, 0)]
        near = (np.abs(a - c) < 3600) | (np.abs(c - b) < 3600)
    n7 = np.searchsorted(ts, c, "left") - np.searchsorted(ts, c - 7 * DAY, "left")
    w = np.searchsorted(ts, c + 1080, "right") > np.searchsorted(ts, c + 720, "left")   # label defined (same NaN-drop rule as real rows)
    ok = ~near & (c <= hi_ok) & (c >= T_LO) & (n7 >= MIN_FILLS) & w
    return int(c[np.argmax(ok)]) if ok.any() else None

def load_headlines():
    import backtest_truth as bt
    fs = sorted(glob.glob("data/archive/alpaca_news_*.parquet"))
    b = pd.concat([pd.read_parquet(f, columns=["t0_utc", "title"]) for f in fs]); b = b.dropna(subset=["title"])
    b = pd.DataFrame({"src": "benzinga", "t0": b.t0_utc.dt.tz_convert(None).values.astype("datetime64[s]").astype("int64"), "text": b.title.str.strip().values})
    p = "data/truth_archive.json"
    if not os.path.exists(p):
        import requests; os.makedirs("data", exist_ok=True); open(p, "wb").write(requests.get(bt.TS_URL, timeout=180).content)
    rows = []
    for x in json.load(open(p)):
        t = int(pd.Timestamp(x["created_at"]).timestamp()); tx = L.clean(x.get("content"))
        if sum(c.isalpha() for c in tx) >= 20: rows.append(("truth", t, tx))
    tr = pd.DataFrame(rows, columns=["src", "t0", "text"])
    h = pd.concat([b, tr]); h = h[(h.t0 >= T_LO) & (h.t0 <= T_END)]
    h = h.drop_duplicates(["src", "text", "t0"]).sort_values("t0", kind="stable").reset_index(drop=True)
    h["topics"] = h.text.map(L.topics_of)
    return h[h.topics.str.len() > 0].reset_index(drop=True)

def load_fills():
    mk = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/ml_fills/*.markets.parquet"))])
    mk = mk.groupby("cid").agg(slug=("slug", "first"), resolved_ts=("resolved_ts", "first")).reset_index()   # a market's resolved_at is constant
    code = pd.Index(mk.cid)
    parts = []
    for f in sorted(glob.glob("data/ml_fills/????_??.parquet")):
        d = pd.read_parquet(f); parts.append((code.get_indexer(d.cid).astype("int32"), d.ts.values, d.p.values))
    c = np.concatenate([x[0] for x in parts]); t = np.concatenate([x[1] for x in parts]); p = np.concatenate([x[2] for x in parts])
    o = np.lexsort((t, c)); c, t, p = c[o], t[o], p[o]
    cuts = np.flatnonzero(np.diff(c)) + 1; st = np.concatenate([[0], cuts]); en = np.concatenate([cuts, [len(c)]])
    return mk, {int(c[a]): (t[a:b], p[a:b]) for a, b in zip(st, en)}

def build(seed=20261011):
    h = load_headlines(); print(f"headlines matched: {len(h):,}  ({h.src.value_counts().to_dict()})", flush=True)
    mk, fills = load_fills(); print(f"markets with fills: {len(fills):,}  fills: {sum(len(v[0]) for v in fills.values()):,}", flush=True)
    t0 = h.t0.values; by_topic = {}
    for k in L.ALL:
        ix = np.flatnonzero(h.topics.map(lambda x: k in x).values); by_topic[k] = (t0[ix], ix)
    cand = []
    for c, (ts, ps) in fills.items():
        slug, res = mk.slug.iat[c], mk.resolved_ts.iat[c]
        tps = [k for k, r in L.SLUG_RX.items() if r.search(slug)]
        if not tps: continue
        lo, hi = ts[0], min(ts[-1] + 7 * DAY, res)
        ix = np.unique(np.concatenate([by_topic[k][1][np.searchsorted(by_topic[k][0], lo, "left"):np.searchsorted(by_topic[k][0], hi, "right")] for k in tps]))
        if not len(ix): continue
        n7 = label_times(ts, ps, t0[ix])["n7d"]; ok = (n7 >= MIN_FILLS) & (res > t0[ix])
        if ok.any(): cand.append(pd.DataFrame({"h": ix[ok], "c": c, "n7d": n7[ok]}))
    C = pd.concat(cand).sort_values(["h", "n7d", "c"], ascending=[True, False, True]); C = C.groupby("h").head(TOP).reset_index(drop=True)
    print(f"candidate pairs after liquidity rule + top-{TOP}: {len(C):,} for {C.h.nunique():,} headlines", flush=True)
    rows, rng = [], np.random.RandomState(seed)
    topics_of_cid = {c: [k for k, r in L.SLUG_RX.items() if r.search(mk.slug.iat[c])] for c in C.c.unique()}
    for c, g in C.groupby("c"):
        ts, ps = fills[c]; T = t0[g.h.values]
        lab = label_times(ts, ps, T); rate = recent_move_rate(ts, ps, T)
        excl = np.sort(np.unique(np.concatenate([by_topic[k][0] for k in topics_of_cid[c]])))
        base = pd.DataFrame({"h": g.h.values, "cid": c, "t_head": T, "t": T, "n7d": lab["n7d"], "pre60": lab["pre60"], "p0": lab["p0"], "dp15": lab["dp15"], "rate": rate, "is_placebo": False})
        pl = []
        for hh, tt in zip(g.h.values, T):
            s = draw_placebo(rng, tt, ts, excl, T_END)
            if s is not None: pl.append((hh, tt, s))
        if pl:
            S = np.array([x[2] for x in pl]); lp = label_times(ts, ps, S); rp = recent_move_rate(ts, ps, S)
            base = pd.concat([base, pd.DataFrame({"h": [x[0] for x in pl], "cid": c, "t_head": [x[1] for x in pl], "t": S, "n7d": lp["n7d"], "pre60": lp["pre60"],
                                                  "p0": lp["p0"], "dp15": lp["dp15"], "rate": rp, "is_placebo": True})])
        rows.append(base)
    D = pd.concat(rows, ignore_index=True)
    n_all = len(D); D = D.dropna(subset=["dp15", "p0"])        # label NaN -> drop (rule)
    D = D[(D.t <= T_END)]
    key = D.h.astype("int64") * 10**6 + D.cid; D = D[~D.is_placebo | key.isin(set(key[~D.is_placebo]))]   # 1 placebo per SURVIVING real pair
    D["slug"] = mk.slug.values[D.cid.values]; hh = h.iloc[D.h.values]
    D["src"], D["text"], D["topics"] = hh.src.values, hh.text.values, hh.topics.map(",".join).values
    D["polarity"] = [L.polarity(x) for x in D.text.values]
    D["split"] = [split_of(t) for t in D.t_head.values]; D = D.dropna(subset=["split"])
    D["y_move"] = (D.dp15.abs() >= THR).astype(int)
    D["y_dir"] = np.where(D.y_move == 1, np.sign(D.dp15), np.nan)
    D["hour"] = ((D.t % DAY) // 3600).astype(int)
    D = D.rename(columns={"h": "hid"}).reset_index(drop=True)
    print(f"rows before NaN drop {n_all:,}, after {len(D):,}")
    return D

if __name__ == "__main__":
    D = build(); D.to_parquet("data/ml_pairs.parquet")
    print("\ncounts per split / kind / source, base rates (y_move = |dp15|>=0.02; y_dir up-share among movers)")
    D["kind"] = np.where(D.is_placebo, "placebo", "real")
    g = D.groupby(["split", "kind"]).agg(n=("y_move", "size"), headlines=("hid", "nunique"), markets=("cid", "nunique"), y_move=("y_move", "mean"), movers=("y_move", "sum"), up_share=("y_dir", lambda s: (s.dropna() > 0).mean()))
    print(g.to_string(float_format=lambda x: f"{x:.3f}"))
    print("\nby source (real only):"); print(D[~D.is_placebo].groupby(["split", "src"]).agg(n=("y_move", "size"), y_move=("y_move", "mean")).to_string(float_format=lambda x: f"{x:.3f}"))
