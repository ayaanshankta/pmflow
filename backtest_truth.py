"""Unscheduled-news backtest: Truth Social posts vs Polymarket-v1 fills. Rules: research/backtest-rules.md (pre-registered).
Run: /opt/anaconda3/bin/python3 backtest_truth.py   -> results/backtest_truth_pairs.csv, results/backtest_truth_summary.json, research/backtest-truth.md
Needs data/truth_archive.json (CNN archive; auto-downloaded) and data/archive/{daily_aligned,daily_aligned_multi}/ (auto-downloaded)."""
import datetime as dt, json, os, re, sys
import numpy as np, pandas as pd, requests
TS_URL = "https://ix.cnn.io/data/truth-social/truth_archive.json"
REPO, ARC = "TimeSeventeen/Polymarket-v1", "data/archive"
START, END = int(dt.datetime(2025,1,20,tzinfo=dt.UTC).timestamp()), int(dt.datetime(2026,4,27,23,tzinfo=dt.UTC).timestamp())
CAP, BURST, N_PLACEBO, DAY = 400, 600, 20, 86400
# topic -> (post terms, slug terms); regexes use letter-boundaries (hyphen/space/digit are boundaries)
TOPICS = {
 "tariff": (["tariff","tariffs"], ["tariff","trade-deal","trade-war"]),
 "fed": (["fed","powell","interest rates?","rate cuts?","federal reserve"], ["fed","powell","interest-rates","rate-cut","bps"]),
 "china": (["china","chinese","xi jinping","xi"], ["china","xi","taiwan"]),
 "iran": (["iran","iranian"], ["iran"]),
 "russia_ukraine": (["russia","russian","ukraine","putin","zelensky","zelenskyy","ceasefire","cease-fire"], ["russia","ukraine","putin","zelensky","ceasefire"]),
 "greenland": (["greenland"], ["greenland"]),
 "canada_mexico": (["canada","canadian","mexico","mexican"], ["canada","mexico"]),
 "tiktok": (["tiktok"], ["tiktok"]),
 "shutdown": (["shutdown"], ["shutdown"]),
 "supreme_court": (["supreme court","scotus"], ["supreme-court","scotus"]),
}
for n in "musk elon netanyahu maduro mamdani newsom vance rubio bessent lutnick harris".split(): TOPICS["p_"+n] = ([n], [n])
def rx(terms, flags=re.I): return re.compile(r"(?<![a-z])(?:" + "|".join(terms) + r")(?![a-z])", flags)
POST_RX = {k: rx(v[0]) for k, v in TOPICS.items()}
SLUG_RX = {k: rx([re.escape(t) for t in v[1]]) for k, v in TOPICS.items()}
URL = re.compile(r"https?://\S+")

def clean(c):
    t = URL.sub(" ", c or ""); t = re.sub(r"^\s*RT:?", "", t); return re.sub(r"\s+", " ", t).strip()
def topics_of(text): return [k for k, r in POST_RX.items() if r.search(text)]

def load_posts(path="data/truth_archive.json"):
    if not os.path.exists(path):
        os.makedirs("data", exist_ok=True); open(path, "wb").write(requests.get(TS_URL, timeout=120).content)
    rows = []
    for p in json.load(open(path)):
        t = int(pd.Timestamp(p["created_at"]).timestamp())   # floor to s
        if not START <= t <= END: continue
        text = clean(p.get("content"))
        if sum(c.isalpha() for c in text) < 20: continue
        tp = topics_of(text)
        if tp: rows.append(dict(id=p["id"], t0=t, text=text, topics=tp))
    return pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)

def select_events(m):
    """m = lexicon-matched posts sorted by t0. Burst rule then cap (most recent)."""
    prev = m.t0.shift(1)
    ev = m[~(m.t0 - prev <= BURST)]   # dropped if any matched post in prior 10 min (shift(1) suffices: sorted)
    return ev.tail(CAP).reset_index(drop=True)

def day_str(t): return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y_%m_%d")
CACHE = "data/truth_fills_cache.parquet"   # topic-filtered fills only (shards are ~55 MB/day in 2026; full set ~14 GB)
def load_fills(days, slug_any):
    if os.path.exists(CACHE): return pd.read_parquet(CACHE)
    from huggingface_hub import hf_hub_download
    out = []
    for d in days:
        for layer in ("daily_aligned", "daily_aligned_multi"):
            try: p = hf_hub_download(REPO, f"{layer}/{d}.parquet", repo_type="dataset", local_dir=ARC)
            except Exception as e: print("missing", layer, d, repr(e)[:80], file=sys.stderr); continue
            f = pd.read_parquet(p, columns=["block_timestamp","condition_id","market_slug","p_event","resolved_at"])
            out.append(f[f.market_slug.str.contains(slug_any, regex=True, na=False)])
    f = pd.concat(out).sort_values("block_timestamp", kind="stable").reset_index(drop=True)
    f["resolved_ts"] = f.resolved_at.map(lambda x: x.timestamp() if pd.notna(x) else np.inf)
    f = f.drop(columns="resolved_at"); f.to_parquet(CACHE)
    return f

def measures(ts, ps, t):
    """ts, ps: sorted arrays for one market. Returns dict or None if no fill before t."""
    i0 = np.searchsorted(ts, t, "left")          # fills < t
    if i0 == 0: return None
    p0 = ps[max(0, i0-5):i0].mean()
    lo = np.searchsorted(ts, t-3600, "left"); a = np.searchsorted(ts, t+300, "left"); b = np.searchsorted(ts, t+3600, "right")
    r = dict(p0=p0, pre60=i0-lo, post5=a-i0, post_5_60=b-a, t_first=np.nan, t_move=np.nan, dp15=np.nan)
    if b > i0:
        r["t_first"] = ts[i0]-t
        mv = np.nonzero(np.abs(ps[i0:b]-p0) >= 0.02)[0]
        if len(mv): r["t_move"] = ts[i0+mv[0]]-t
    l15 = np.searchsorted(ts, t+720, "left"); h15 = np.searchsorted(ts, t+1080, "right")
    if h15 > l15: r["dp15"] = abs(ps[h15-1]-p0)
    return r

def placebo_times(rng, t, all_t0, lo_ok, hi_ok, matched):
    out, tries = [], 0
    while len(out) < N_PLACEBO and tries < 5000:
        tries += 1
        c = int(rng.randint(t-3*DAY, t+3*DAY+1))
        if matched and abs((c-t+DAY//2) % DAY - DAY//2) > 3600: continue   # within ±60 min of clock time
        if not lo_ok <= c <= hi_ok: continue
        k = np.searchsorted(all_t0, c)
        if (k < len(all_t0) and all_t0[k]-c < 7200) or (k > 0 and c-all_t0[k-1] < 7200): continue
        out.append(c)
    return out

def build(ev, allm):
    all_t0 = np.sort(allm.t0.values)
    slug_any = "|".join(f"(?:{r.pattern})" for r in SLUG_RX.values())
    days = sorted({day_str(t+o*DAY) for t in ev.t0 for o in range(-10, 4)})
    print(f"loading {len(days)} days", file=sys.stderr)
    # drop days beyond archive end silently via missing-handler
    f = load_fills(days, re.compile(slug_any, re.I).pattern)
    data_lo, data_hi = int(f.block_timestamp.min()), min(int(f.block_timestamp.max()), END)
    g = {c: (d.block_timestamp.values, d.p_event.values, d.market_slug.iloc[0], d.resolved_ts.iloc[0]) for c, d in f.groupby("condition_id")}
    slugs = pd.Series({c: v[2] for c, v in g.items()})
    cache = {}  # topic -> condition_ids
    for k, r in SLUG_RX.items(): cache[k] = set(slugs.index[slugs.map(lambda s: bool(r.search(s)))])
    rows = []; n_rel = 0
    for ei, e in ev.iterrows():
        cands = set().union(*[cache[k] for k in e.topics])
        scored = []
        for c in cands:
            ts, ps, slug, res = g[c]
            if res <= e.t0: continue
            n = np.searchsorted(ts, e.t0, "left") - np.searchsorted(ts, e.t0-7*DAY, "left")
            if n >= 1: scored.append((n, c))
        scored.sort(key=lambda x: (-x[0], x[1]))
        got = 0
        for rank, (n, c) in enumerate(scored[:5]):
            ts, ps, slug, _ = g[c]
            m = measures(ts, ps, e.t0)
            if m is None: continue
            got += 1
            base = dict(event=ei, post_id=e.id, t0=e.t0, topics=",".join(e.topics), cid=c, slug=slug, rank=rank, n7d=n)
            rows.append({**base, "kind": "event", **m})
            for kind, matched in (("placebo", False), ("placebo_tod", True)):
                rng = np.random.RandomState(20261011 + ei*1000 + rank + (500 if matched else 0))
                for pt in placebo_times(rng, e.t0, all_t0, data_lo + 7*DAY, data_hi, matched):
                    pm = measures(ts, ps, pt)
                    if pm is not None: rows.append({**base, "kind": kind, "t0": pt, **pm})
        n_rel += got > 0
    return pd.DataFrame(rows), n_rel

def boot_cluster(df, fn, B=10000, seed=7):
    """cluster bootstrap by event; fn(subdf)->float"""
    rng = np.random.RandomState(seed); groups = [d for _, d in df.groupby("event")]
    out = np.empty(B)
    for b in range(B):
        idx = rng.randint(0, len(groups), len(groups)); out[b] = fn(pd.concat([groups[i] for i in idx]))
    return np.nanpercentile(out, [2.5, 97.5])

def summarize(P, kind_pl="placebo", unpinned=False):
    E = P[P.kind == "event"]; PL = P[P.kind == kind_pl]
    if unpinned: E = E[(E.p0 >= .02) & (E.p0 <= .98)]; PL = PL[(PL.p0 >= .02) & (PL.p0 <= .98)]
    key = ["event", "rank"]
    pm = PL.groupby(key)[["pre60","post5","post_5_60"]].mean().add_suffix("_pl")
    D = E.merge(pm, left_on=key, right_index=True, how="inner")
    D["ex_post5"] = D.post5 - D.post5_pl
    s = dict(kind_pl=kind_pl, unpinned=unpinned, n_events=int(E.event.nunique()), n_pairs=len(E), n_pairs_with_placebo=len(D),
             n_placebo=len(PL), pre60=E.pre60.mean(), post5=E.post5.mean(), post_5_60=E.post_5_60.mean(),
             post5_placebo=PL.post5.mean(), pre60_placebo=PL.pre60.mean(),
             excess_post5=D.ex_post5.mean(), excess_ci=list(boot_cluster(D, lambda d: d.ex_post5.mean())))
    for nm, X in (("event", E), ("placebo", PL)):
        mv = X.t_move.dropna()
        s[f"{nm}_moved"] = len(mv); s[f"{nm}_moved_share"] = len(mv)/max(len(X), 1)
        s[f"{nm}_t_move_median"] = float(mv.median()) if len(mv) else np.nan
        s[f"{nm}_t_first_median"] = float(X.t_first.median())
        s[f"{nm}_dp15_mean"] = X.dp15.mean()
    s["t_move_ci"] = list(boot_cluster(E, lambda d: d.t_move.median()))
    s["moved_share_diff"] = s["event_moved_share"] - s["placebo_moved_share"]
    s["pass1"] = bool(s["event_t_move_median"] < 120); s["pass2"] = bool(s["excess_ci"][0] > 0)
    return s

if __name__ == "__main__" and "--report" not in sys.argv:
    m = load_posts(); ev = select_events(m)
    print(f"matched posts {len(m)}  events {len(ev)}  span {dt.datetime.fromtimestamp(ev.t0.min(), dt.UTC)} .. {dt.datetime.fromtimestamp(ev.t0.max(), dt.UTC)}", file=sys.stderr)
    if "--events-only" in sys.argv: sys.exit()
    P, n_rel = build(ev, m); P.to_csv("results/backtest_truth_pairs.csv", index=False)
    S = dict(matched_posts=len(m), events=len(ev), events_with_pair=int(n_rel), relevance=n_rel/len(ev),
             primary=summarize(P), tod=summarize(P, "placebo_tod"), unpinned=summarize(P, unpinned=True))
    json.dump(S, open("results/backtest_truth_summary.json", "w"), indent=1, default=float)
    print(json.dumps(S, indent=1, default=float))

def report():
    """--report: tables + examples from results/ (verdict paragraph is hand-written in research/backtest-truth.md)."""
    S = json.load(open("results/backtest_truth_summary.json")); P = pd.read_csv("results/backtest_truth_pairs.csv")
    posts = {p["id"]: clean(p.get("content")) for p in json.load(open("data/truth_archive.json"))}
    f = lambda x, n=2: "NaN" if x is None or x != x else f"{x:.{n}f}"
    ci = lambda c, n=1: f"[{c[0]:.{n}f}, {c[1]:.{n}f}]"
    o = [f"matched posts (lexicon, 2025-01-20..2026-04-27): {S['matched_posts']}; events after burst rule + cap: {S['events']}; "
         f"events with >=1 active candidate market: {S['events_with_pair']} (relevance {S['relevance']:.1%})\n",
         "| set | events | pairs | fills [-60m,0) ev / pl | fills [0,+5m) ev / pl | excess [0,+5m) (95% CI) | moved share ev / pl | median t_move s ev (CI) / pl | median t_first s ev / pl | mean abs dp15 ev / pl | pass1 | pass2 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, nm in (("primary", "primary (random +-3d)"), ("tod", "secondary (clock-time matched)"), ("unpinned", "secondary (0.02<=p0<=0.98)")):
        s = S[k]
        o.append(f"| {nm} | {s['n_events']} | {s['n_pairs']} | {f(s['pre60'],1)} / {f(s['pre60_placebo'],1)} | {f(s['post5'],1)} / {f(s['post5_placebo'],1)} | "
                 f"{f(s['excess_post5'],1)} {ci(s['excess_ci'])} | {s['event_moved_share']:.1%} / {s['placebo_moved_share']:.1%} | "
                 f"{f(s['event_t_move_median'],0)} {ci(s['t_move_ci'],0)} / {f(s['placebo_t_move_median'],0)} | {f(s['event_t_first_median'],0)} / {f(s['placebo_t_first_median'],0)} | "
                 f"{f(s['event_dp15_mean'],4)} / {f(s['placebo_dp15_mean'],4)} | {s['pass1']} | {s['pass2']} |")
    E = P[P.kind == "event"].copy(); E["share"] = 0
    best = E.sort_values(["event", "post5", "n7d"], ascending=[True, False, False]).groupby("event").head(1)
    rng = np.random.RandomState(11)
    top = best.sort_values("post5", ascending=False).head(5)
    rnd = best[~best.event.isin(top.event)].iloc[rng.choice(len(best) - 5, 5, replace=False)]
    o += ["", "## 10 example events (best market = most fills in [0,+5m); first 5 = highest-activity, last 5 = seeded random draw, no cherry-picking)",
          "| t0 UTC | post (first 90 chars) | best market slug | p0 | fills -60m / +5m | t_first s | t_move s | dp15 |", "|---|---|---|---|---|---|---|---|"]
    for _, r in pd.concat([top, rnd]).iterrows():
        tt = dt.datetime.fromtimestamp(int(r.t0), dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
        o.append(f"| {tt} | {posts.get(str(r.post_id), '')[:90].replace('|',' ')} | {r.slug[:60]} | {r.p0:.3f} | {int(r.pre60)} / {int(r.post5)} | {f(r.t_first,0)} | {f(r.t_move,0)} | {f(r.dp15,3)} |")
    return "\n".join(o)
if __name__ == "__main__" and "--report" in sys.argv: print(report())
