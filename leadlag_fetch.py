"""C2 step 0: month-by-month pull of Polymarket-v1 daily_aligned(+multi) for 2024-12-31..2025-12-31 (all markets, not lexicon-filtered),
keep (ts, cid, p_event, usd, neg_risk_market_id) -> data/leadlag/fills_YYYY_MM.parquet and one markets table; delete each raw shard right after reading.
Run: /opt/anaconda3/bin/python3 leadlag_fetch.py   (resumable; 2 GB raw cap, disk check per month)"""
import datetime as dt, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
REPO, ARC, RAW, OUT = "TimeSeventeen/Polymarket-v1", "data/archive", "data/raw/leadlag", "data/leadlag"
COLS = ["block_timestamp", "condition_id", "market_slug", "p_event", "usdc_amount", "close_at", "outcome_seq"]
def free_gb(): return shutil.disk_usage("/").free / 1e9
def one(layer, d):
    from huggingface_hub import hf_hub_download
    name = f"{layer}/{d:%Y_%m_%d}.parquet"; own = os.path.join(ARC, name); keep = os.path.exists(own); p = own
    if not keep:
        for a in range(4):
            try: p = hf_hub_download(REPO, name, repo_type="dataset", local_dir=RAW); break
            except Exception as e:
                if "404" in repr(e) or "EntryNotFound" in repr(e): return None
                time.sleep(2 ** a)
        else: print("FAILED", name, file=sys.stderr); return None
    try:
        cols = COLS + (["neg_risk_market_id"] if layer.endswith("multi") else [])
        f = pd.read_parquet(p, columns=cols)
        if "neg_risk_market_id" not in f: f["neg_risk_market_id"] = None
        f["multi"] = layer.endswith("multi")
        return f
    finally:
        if not keep and os.path.exists(p): os.remove(p)
def month(y, m):
    days = [d for d in (dt.date(y, m, 1) + dt.timedelta(i) for i in range(31)) if d.month == m and d >= dt.date(2024, 12, 31)]
    if (y, m) == (2025, 1): days = [dt.date(2024, 12, 31)] + days
    jobs = [(l, d) for d in days for l in ("daily_aligned", "daily_aligned_multi")]
    with ThreadPoolExecutor(4) as ex: parts = [r for r in ex.map(lambda j: one(*j), jobs) if r is not None]
    f = pd.concat(parts).sort_values("block_timestamp", kind="stable")
    mk = f.groupby("condition_id").agg(slug=("market_slug", "first"), nr_mid=("neg_risk_market_id", "first"), multi=("multi", "max"),
                                       close_at=("close_at", "first"), n=("p_event", "size"), usd=("usdc_amount", "sum")).reset_index()
    out = pd.DataFrame({"ts": f.block_timestamp.astype("int64").values, "cid": f.condition_id.astype("category").values,
                        "p": f.p_event.astype("float32").values, "usd": f.usdc_amount.astype("float32").values})
    out.to_parquet(f"{OUT}/fills_{y}_{m:02d}.parquet"); mk.to_parquet(f"{OUT}/mk_{y}_{m:02d}.parquet")
    return len(out)
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); os.makedirs(RAW, exist_ok=True)
    for m in range(1, 13):
        if os.path.exists(f"{OUT}/mk_2025_{m:02d}.parquet"): continue
        assert free_gb() > 10, f"disk low {free_gb():.1f} GB"
        t = time.time(); n = month(2025, m)
        raw = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(RAW) for f in fs) / 1e6
        print(f"2025-{m:02d} {n:,} fills {time.time()-t:.0f}s free {free_gb():.1f} GB raw_left {raw:.0f} MB", flush=True)
