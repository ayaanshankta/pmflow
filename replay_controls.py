"""Memorisation controls for the LLM-direction arm (rules: research/ml-rules.md B3; prompts: research/replay-llm-controls.md).
Reuses replay_llm.py for the model call, cache, replay and bootstrap; only the prompt, cache file and post substitution differ.
Run: /opt/anaconda3/bin/python3 replay_controls.py [--no-calls]"""
import json, os, sys
import numpy as np, pandas as pd
import replay_llm as L, replay_truth as R

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS_MD = os.path.join(HERE, "research", "replay-llm-controls.md")
GAP = 7 * 86400
CACHES = {"c1": os.path.join(HERE, "data", "controls_c1_dirs.jsonl"), "c2": os.path.join(HERE, "data", "controls_c2_dirs.jsonl")}


def draw_wrong(pair_events, ev_t0, seed=0, gap=GAP):
    """For each pair's event index, the index of another event drawn uniformly (one RandomState(seed) stream, pair order) from
    events whose post time is >= gap seconds from the pair's own event's. The own event is never eligible (distance 0)."""
    ev_t0 = np.asarray(ev_t0); rng = np.random.RandomState(seed); out = []
    for e in pair_events:
        elig = np.flatnonzero(np.abs(ev_t0 - ev_t0[e]) >= gap)
        if not len(elig): raise ValueError(f"no event >= {gap}s from event {e}")
        out.append(int(elig[rng.randint(len(elig))]))
    return out


def set_prompt(name):
    """Point replay_llm at control 1's prompt+cache, or control 2's cache with the unchanged B2 prompt."""
    L.CACHE = CACHES[name]
    if name == "c1":
        L.PROMPT_MD = CONTROLS_MD
        L.SYSTEM = L._block("System prompt (exact):")
        t = L._block("User message template (exact;")
        L.user_message = lambda post, slug: t.replace("{question}", slug.replace("-", " "))


def counts(dirs, keys):
    c = {"up": 0, "down": 0, "none": 0, "failed_or_uncalled": 0}
    for k in keys:
        d = dirs.get(k)
        if d in (1, -1, 0): c[{1: "up", -1: "down", 0: "none"}[d]] += 1
        else: c["failed_or_uncalled"] += 1
    return c


def main():
    import backtest_truth as BT
    calls = "--no-calls" not in sys.argv
    m = BT.load_posts(); ev = BT.select_events(m)
    P, _ = BT.build(ev, m)
    P = P[P.kind.isin(["event", "placebo"])]
    f = pd.read_parquet(BT.CACHE)
    g = {c: (d.block_timestamp.values, d.p_event.values) for c, d in f.groupby("condition_id")}
    text_of = dict(zip(ev.id, ev.text))
    E = P[P.kind == "event"]
    liquid = E[[int(np.searchsorted(g[r.cid][0], r.t0, "left") - np.searchsorted(g[r.cid][0], r.t0 - 3600, "left")) >= R.LIQ_MIN
                for r in E.itertuples()]].reset_index(drop=True)
    keys = [f"{r.event}|{r.cid}" for r in liquid.itertuples()]
    print("liquid pairs", len(liquid), file=sys.stderr)
    b2c = L.read_cache()   # original arm, before any patching
    b2 = {k: b2c[k]["dir"] for k in keys if k in b2c}
    L.CAP_USD = 0.5        # two controls, $1 combined
    res, models = {"b2": b2}, {}
    for name in ("c1", "c2"):
        set_prompt(name)
        pairs = liquid.copy()
        if name == "c2":
            w = draw_wrong(pairs.event.values, ev.t0.values, seed=0)
            pairs["post_id"] = ev.id.values[w]
            assert (np.abs(ev.t0.values[w] - ev.t0.values[pairs.event.values]) >= GAP).all()
        d, st = L.get_dirs(pairs, text_of, calls=calls)
        res[name] = {k: v for k, v in d.items() if v in (1, -1, 0)}
        cache = L.read_cache()
        mc = {}
        for k in keys:
            if k in cache: mc[cache[k]["model"]] = mc.get(cache[k]["model"], 0) + 1
        models[name] = dict(spent=st["spent"], cap_hit=st["cap_hit"], served_by=mc,
                            failures=sum(1 for k in keys if cache.get(k, {}).get("dir", "x") is None))
    out = dict(models=models, counts={n: counts(res[n], keys) for n in res})
    # agreement with B2
    nz = [k for k in keys if res["b2"].get(k) in (1, -1)]
    out["agreement"] = {n: dict(same_nonnone_over_all_pairs=sum(res[n].get(k) == res["b2"].get(k) and res["b2"].get(k) in (1, -1) for k in keys) / len(keys),
                                same_over_b2_nonnone=sum(res[n].get(k) == res["b2"][k] for k in nz) / len(nz),
                                n_all=len(keys), n_b2_nonnone=len(nz)) for n in ("c1", "c2")}
    # replay
    rows = []
    for n in ("b2", "c1", "c2"):
        T, cnt = L.run(P, g, res[n])
        Rt = L.table(T)
        for dl in R.DELTAS:
            x = Rt[(Rt.kind == "diff") & (Rt.entry == 0) & (Rt.delta == dl) & (Rt.fee == "0")]
            e = Rt[(Rt.kind == "event") & (Rt.entry == 0) & (Rt.delta == dl) & (Rt.fee == "0")]
            pl = Rt[(Rt.kind == "placebo") & (Rt.entry == 0) & (Rt.delta == dl) & (Rt.fee == "0")]
            rows.append(dict(arm=n, delta=dl, n_event=int(e.n.iloc[0]) if len(e) else 0, event_pts=float(e.pts.iloc[0]) if len(e) else None,
                             n_placebo=int(pl.n.iloc[0]) if len(pl) else 0, placebo_pts=float(pl.pts.iloc[0]) if len(pl) else None,
                             diff=float(x.pts.iloc[0]) if len(x) else None, lo=float(x.lo.iloc[0]) if len(x) else None,
                             hi=float(x.hi.iloc[0]) if len(x) else None))
        T.to_csv(f"results/replay_controls_{n}_trades.csv", index=False)
    out["table"] = rows
    json.dump(out, open("results/replay_controls_summary.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
