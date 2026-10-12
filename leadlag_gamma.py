"""C2 step 1a: fetch Gamma event membership for every 2025-archive market with >= MIN_FILLS fills in 2025. Saves data/leadlag/gamma_markets.jsonl
(one line per looked-up condition id; resumable). No prices are read here beyond the fill COUNT used to bound the lookup list.
Run: /opt/anaconda3/bin/python3 leadlag_gamma.py"""
import glob, json, os, time, urllib.request
import pandas as pd
OUT, MIN_FILLS, BATCH = "data/leadlag/gamma_markets.jsonl", 20, 40
def cands():
    mk = pd.concat([pd.read_parquet(f, columns=["condition_id", "slug", "n"]) for f in sorted(glob.glob("data/leadlag/mk_2025_*.parquet"))])
    g = mk.groupby("condition_id").agg(n=("n", "sum"), slug=("slug", "first"))
    # 5m/15m/hourly "up or down" markets: each is its own single-market event (0 of 902 sampled events had a 2nd member) -> not looked up
    g = g[(g.n >= MIN_FILLS) & ~g.slug.str.contains("up-?or-?down|updown", case=False)]
    return list(g.index)
def get(url):
    for a in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pmflow-research"}), timeout=60))
        except Exception as e: time.sleep(2 ** a)
    raise RuntimeError(url[:120])
if __name__ == "__main__":
    ids = cands(); done = set()
    if os.path.exists(OUT): done = {json.loads(l)["cid"] for l in open(OUT)}
    todo = [c for c in ids if c not in done]; print(len(ids), "candidates", len(todo), "todo", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    q = lambda b: get("https://gamma-api.polymarket.com/markets?closed=true&limit=100&" + "&".join("condition_ids=" + c for c in b))
    with open(OUT, "a") as fh, ThreadPoolExecutor(3) as ex:
        for i, (b, r) in enumerate(zip(batches, ex.map(q, batches))):
            got = {m["conditionId"]: m for m in r}
            for c in b:
                m = got.get(c)
                if m is None: fh.write(json.dumps({"cid": c, "found": False}) + "\n"); continue
                ev = [{k: e.get(k) for k in ("id", "slug", "title", "endDate", "negRisk", "negRiskMarketID")} for e in (m.get("events") or [])]
                fh.write(json.dumps({"cid": c, "found": True, "slug": m.get("slug"), "question": m.get("question"), "endDate": m.get("endDate"),
                                     "negRisk": m.get("negRisk"), "negRiskMarketID": m.get("negRiskMarketID"), "groupItemTitle": m.get("groupItemTitle"),
                                     "groupItemThreshold": m.get("groupItemThreshold"), "events": ev}) + "\n")
            fh.flush()
            if i % 50 == 0: print(i * BATCH, len(todo), flush=True)
