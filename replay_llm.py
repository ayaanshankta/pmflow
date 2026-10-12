"""LLM-direction replay arm. Rules: research/ml-rules.md addendum B2 (+ "B2 addition"); prompt: research/replay-llm-prompt.md.
Engine (fill/exit/pnl/bootstrap) is replay_truth.py; this file only adds: the model call + cache, the entry variant,
the taker-fee row, event-minus-placebo and the date split.
Run: /opt/anaconda3/bin/python3 replay_llm.py   (calls the model for uncached pairs, cap $2; then replays and prints/writes tables)
     /opt/anaconda3/bin/python3 replay_llm.py --no-calls   (replay only what is cached)"""
import json, os, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
import replay_truth as R

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_MD = os.path.join(HERE, "research", "replay-llm-prompt.md")
CACHE = os.path.join(HERE, "data", "replay_llm_dirs.jsonl")
CLAUDE = os.path.expanduser("~/.local/bin/claude")
MODEL, CAP_USD = "haiku", 2.0
SPLIT = int(pd.Timestamp("2026-02-01", tz="UTC").timestamp())
TAKER_RATE = 0.04
FEE_COLS = ["0", "0.01", "0.02", "tk"]


def _block(label):
    return re.search(re.escape(label) + r".*?\n```\n(.*?)\n```", open(PROMPT_MD).read(), re.S).group(1)


SYSTEM, USER_T = _block("System prompt (exact):"), _block("User message template (exact;")


def user_message(post, slug):
    return USER_T.replace("{post}", post).replace("{question}", slug.replace("-", " "))


def parse_dir(reply):
    """-> +1/-1/0 for up/down/none, or None if the reply is not exactly one of the three words."""
    m = re.fullmatch(r"\W*(up|down|none)\W*", (reply or "").lower())
    return None if not m else {"up": 1, "down": -1, "none": 0}[m.group(1)]


def call(msg):
    """-> (reply|None, cost, model, latency, error|None). error means the call itself failed (retried on a later run)."""
    t = time.time()
    try:
        out = subprocess.run([CLAUDE, "-p", msg, "--model", MODEL, "--system-prompt", SYSTEM, "--output-format", "json",
                              "--tools", "", "--safe-mode", "--no-session-persistence", "--max-budget-usd", "0.05"],
                             stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        return None, 0.0, None, time.time() - t, "timeout"
    try:
        env = json.loads(out)
    except ValueError:
        return None, 0.0, None, time.time() - t, "stdout not JSON: " + out[:150]
    cost, model = env.get("total_cost_usd") or 0.0, ",".join(env.get("modelUsage") or {})
    if env.get("is_error"):
        return None, cost, model, time.time() - t, "is_error: " + str(env.get("result"))[:150]
    return str(env.get("result", "")), cost, model, time.time() - t, None


def read_cache():
    """key f'{event}|{cid}' -> latest record. Append-only file; last line wins."""
    if not os.path.exists(CACHE): return {}
    return {r["key"]: r for r in map(json.loads, open(CACHE))}


def get_dirs(pairs, text_of, workers=4, calls=True):
    """pairs: DataFrame event/cid/slug/post_id (liquid event pairs). Returns (dict key->+1/-1/0/None, stats).
    A pair is final once cached with ok=True (incl. parse failures, dir None); call errors are retried next run."""
    cache = read_cache()
    todo = [r for r in pairs.itertuples() if not (f"{r.event}|{r.cid}" in cache and cache[f"{r.event}|{r.cid}"]["final"])]
    spent, lock, stopped = [sum(r.get("cost", 0.0) for r in cache.values())], threading.Lock(), [False]
    print(f"pairs {len(pairs)}  cached-final {len(pairs) - len(todo)}  to call {len(todo)}  spent so far ${spent[0]:.4f}", file=sys.stderr)

    def work(r):
        if stopped[0]: return
        msg, cost, tl = user_message(text_of[r.post_id], r.slug), 0.0, 0.0
        for attempt in (1, 2):   # one retry, on call error or unparseable reply
            with lock:
                if spent[0] + 0.05 > CAP_USD:   # next call could breach the cap: stop cleanly
                    stopped[0] = True; return
            reply, c, model, l, err = call(msg)
            with lock: spent[0] += c
            cost, tl = cost + c, tl + l
            d = None if err else parse_dir(reply)
            if d is not None: break
        rec = dict(key=f"{r.event}|{r.cid}", event=int(r.event), cid=r.cid, slug=r.slug, post_id=r.post_id, raw=reply, dir=d,
                   error=err, final=err is None, cost=cost, latency=round(tl, 2), attempts=attempt, model=model)
        with lock, open(CACHE, "a") as f: f.write(json.dumps(rec) + "\n")

    if calls and todo:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with ThreadPoolExecutor(workers) as ex: list(ex.map(work, todo))
    if stopped[0]: print(f"SPEND CAP: stopped before exceeding ${CAP_USD}", file=sys.stderr)
    cache = read_cache()
    dirs = {f"{p.event}|{p.cid}": cache.get(f"{p.event}|{p.cid}", {}).get("dir", "uncalled") for p in pairs.itertuples()}
    return dirs, dict(spent=sum(r.get("cost", 0.0) for r in cache.values()), cap_hit=stopped[0])


# ---- replay -------------------------------------------------------------------------------------------------------

def entry(ts, ps, t0, delta, k):
    """k=0: first trade at/after t0+delta (== replay_truth.fill_exit); k=1: the trade after that one. Same 60 s no-fill rule
    (applied to the trade actually used) and same exit. -> (reason, p_in, p_out)."""
    t = t0 + delta
    i = int(np.searchsorted(ts, t, "left")) + k
    if i >= len(ts) or ts[i] > t + R.FILL_WITHIN: return "nofill", np.nan, np.nan
    lo, hi = int(np.searchsorted(ts, t0 + R.EXIT_LO, "left")), int(np.searchsorted(ts, t0 + R.EXIT_HI, "right"))
    if hi <= lo: return "noexit", ps[i], np.nan
    return "ok", float(ps[i]), float(ps[hi - 1])


def pnl_taker(sign, p_in, p_out, notional=R.NOTIONAL):
    """As replay_truth.pnl but fee per side = TAKER_RATE * p * (1-p) * traded value (p = YES-axis price at that trade;
    p(1-p) is symmetric so the NO side pays the same rate). -> (pts, usd)."""
    c_in, v_out = (p_in, p_out) if sign > 0 else (1 - p_in, 1 - p_out)
    if c_in <= 0: return np.nan, np.nan
    sh = notional / c_in
    usd = sh * (v_out - c_in) - TAKER_RATE * p_in * (1 - p_in) * notional - TAKER_RATE * p_out * (1 - p_out) * sh * v_out
    return 100 * usd / sh, usd


def run(P, g, dirs, deltas=R.DELTAS):
    """P: event/placebo rows (event, rank, cid, kind, t0, slug, post_id). dirs: 'event|cid' -> +1/-1 (0/None/'uncalled' skipped).
    The direction belongs to the (post, market) pair and is held fixed at placebo times. -> (trades df, counts dict)."""
    rows, cnt = [], {}
    bump = lambda k, c: cnt.__setitem__((k, c), cnt.get((k, c), 0) + 1)
    for r in P.itertuples():
        ts, ps = g[r.cid]; k = r.kind; bump(k, "pairs")
        if np.searchsorted(ts, r.t0, "left") - np.searchsorted(ts, r.t0 - 3600, "left") < R.LIQ_MIN:
            bump(k, "illiquid"); continue
        bump(k, "liquid")
        d = dirs.get(f"{r.event}|{r.cid}")
        if d not in (1, -1): bump(k, "no_direction"); continue
        for ent in (0, 1):
            for dl in deltas:
                why, p_in, p_out = entry(ts, ps, r.t0, dl, ent)
                if why != "ok": bump((k, ent, dl), why); continue
                row = dict(kind=k, entry=ent, delta=dl, event=r.event, rank=r.rank, t0=r.t0, sign=d, p_in=p_in, p_out=p_out)
                for f in R.FEES: row[f"pts_{f:g}"], row[f"usd_{f:g}"] = R.pnl(d, p_in, p_out, f)
                row["pts_tk"], row["usd_tk"] = pnl_taker(d, p_in, p_out)
                rows.append(row)
    return pd.DataFrame(rows), cnt


def _ci(sums, ns, rng):
    return R.boot(sums, ns, rng)


def table(T, post_t0=None):
    """One row per (kind, entry, delta, fee) with trade-weighted mean + event-cluster bootstrap CI (RandomState(0) each, as
    replay_truth.table), plus event-minus-placebo rows (kind='diff'): per bootstrap draw of events, mean(event trades) -
    mean(placebo trades) over the same drawn events (same RandomState(0)). Events with trades in only one set contribute to that
    set only."""
    out = []
    for (ent, dl), d in T.groupby(["entry", "delta"]):
        for f in FEE_COLS:
            col, ucol = f"pts_{f}", f"usd_{f}"
            per = {}
            for kind, x in d.groupby("kind"):
                g = x.assign(p=x[col], u=x[ucol]).groupby("event").agg(s=("p", "sum"), n=("p", "count"), u=("u", "sum"))
                per[kind] = g
                lo, hi = R.boot(g.s.values, g.n.values, np.random.RandomState(R.SEED))
                ulo, uhi = R.boot(g.u.values, g.n.values, np.random.RandomState(R.SEED))
                out.append(dict(kind=kind, entry=ent, delta=dl, fee=f, n=len(x), n_events=len(g), hit=float((x[ucol] > 0).mean()),
                                pts=float(x[col].mean()), lo=lo, hi=hi, usd=float(x[ucol].mean()), ulo=ulo, uhi=uhi))
            if "event" in per and "placebo" in per:
                ev, pl = per["event"], per["placebo"]
                ids = sorted(set(ev.index) | set(pl.index))
                a = ev.reindex(ids).fillna(0); b = pl.reindex(ids).fillna(0)
                rng = np.random.RandomState(R.SEED); idx = rng.randint(0, len(ids), (R.B, len(ids)))
                es, en, ps_, pn = (a.s.values[idx].sum(1), a.n.values[idx].sum(1), b.s.values[idx].sum(1), b.n.values[idx].sum(1))
                ok = (en > 0) & (pn > 0)
                m = es[ok] / en[ok] - ps_[ok] / pn[ok]
                lo, hi = np.percentile(m, [2.5, 97.5])
                us, upl = a.u.values, b.u.values
                um = us[idx].sum(1)[ok] / en[ok] - upl[idx].sum(1)[ok] / pn[ok]
                ulo, uhi = np.percentile(um, [2.5, 97.5])
                pe, pp = ev.s.sum() / ev.n.sum(), pl.s.sum() / pl.n.sum()
                ue, up_ = ev.u.sum() / ev.n.sum(), pl.u.sum() / pl.n.sum()
                out.append(dict(kind="diff", entry=ent, delta=dl, fee=f, n=int(ev.n.sum()), n_events=len(ev), hit=np.nan,
                                pts=float(pe - pp), lo=float(lo), hi=float(hi), usd=float(ue - up_), ulo=float(ulo), uhi=float(uhi)))
    return pd.DataFrame(out)


def verdict(Rt):
    """Bar: event kind, mean > 0, CI lo > 0, n >= 100; at flat 1 % and at the taker fee; per entry variant and delta."""
    v = {}
    for ent in (0, 1):
        for dl in R.DELTAS:
            for f in ("0.01", "tk"):
                x = Rt[(Rt.kind == "event") & (Rt.entry == ent) & (Rt.delta == dl) & (Rt.fee == f)]
                v[f"entry{ent}|d{dl}|fee{f}"] = bool(len(x) and x.pts.iloc[0] > 0 and x.lo.iloc[0] > 0 and x.n.iloc[0] >= 100)
    return v


def fmt(Rt):
    lab = {"0": "0%", "0.01": "1%", "0.02": "2%", "tk": "taker 0.04*p(1-p)"}
    o = ["| set | entry | Δ s | fee/side | n trades | events | hit | mean PnL pts (95% CI) | mean PnL $ (95% CI) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in Rt.itertuples():
        hit = "" if r.hit != r.hit else f"{r.hit:.1%}"
        o.append(f"| {r.kind} | {'first' if r.entry == 0 else 'next'} | {r.delta} | {lab[r.fee]} | {r.n} | {r.n_events} | {hit} | "
                 f"{r.pts:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}] | {r.usd:+.2f} [{r.ulo:+.2f}, {r.uhi:+.2f}] |")
    return "\n".join(o)


def main():
    import backtest_truth as BT
    m = BT.load_posts(); ev = BT.select_events(m)
    P, _ = BT.build(ev, m)
    P = P[P.kind.isin(["event", "placebo"])]
    f = pd.read_parquet(BT.CACHE)
    g = {c: (d.block_timestamp.values, d.p_event.values) for c, d in f.groupby("condition_id")}
    text_of = dict(zip(ev.id, ev.text))
    E = P[P.kind == "event"]
    liquid = E[[int(np.searchsorted(g[r.cid][0], r.t0, "left") - np.searchsorted(g[r.cid][0], r.t0 - 3600, "left")) >= R.LIQ_MIN
                for r in E.itertuples()]]
    print(f"liquid event pairs: {len(liquid)}", file=sys.stderr)
    dirs, st = get_dirs(liquid, text_of, calls="--no-calls" not in sys.argv)
    cache = read_cache()
    liq_keys = [f"{r.event}|{r.cid}" for r in liquid.itertuples()]
    c = {"up": 0, "down": 0, "none": 0, "parse_fail": 0, "call_error": 0, "uncalled": 0}
    for k in liq_keys:
        d = dirs[k]
        if d == "uncalled": c["uncalled"] += 1
        elif d is None: c["call_error" if cache[k]["error"] else "parse_fail"] += 1
        else: c[{1: "up", -1: "down", 0: "none"}[d]] += 1
    lat = [cache[k]["latency"] / cache[k]["attempts"] for k in liq_keys if k in cache]
    info = dict(liquid=len(liq_keys), dir_counts=c, spent_usd=st["spent"], cap_hit=st["cap_hit"],
                mean_latency_s=float(np.mean(lat)) if lat else None)
    print(json.dumps(info, indent=1))
    dirs = {k: v for k, v in dirs.items() if v in (1, -1, 0)}
    T, cnt = run(P, g, dirs)
    ev_t0 = E.set_index("event").t0.to_dict()
    T["late"] = T.event.map(ev_t0) >= SPLIT
    T.to_csv("results/replay_llm_trades.csv", index=False)
    Rt = table(T)
    parts = {"all": Rt}
    for nm, sub in (("before 2026-02-01", T[~T.late]), ("on/after 2026-02-01", T[T.late])):
        parts[nm] = table(sub) if len(sub) else pd.DataFrame()
    V = verdict(Rt)
    C = {f"{'|'.join(map(str, k)) if isinstance(k, tuple) else k}:{c_}": n for (k, c_), n in cnt.items()}
    json.dump(dict(info=info, counts=C, verdict=V, table={k: v.to_dict("records") for k, v in parts.items()}),
              open("results/replay_llm_summary.json", "w"), indent=1, default=float)
    with open("results/replay_llm_table.md", "w") as fh:
        for nm, t in parts.items():
            if len(t): fh.write(f"## {nm}\n\n{fmt(t)}\n\n")
    print(fmt(Rt)); print(json.dumps(C, indent=1)); print("verdict", json.dumps(V, indent=1))
    for nm in list(parts)[1:]:
        print(nm); print(fmt(parts[nm]) if len(parts[nm]) else "(no trades)")


if __name__ == "__main__":
    main()
