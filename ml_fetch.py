"""Step 1 of ml_dataset: month-by-month pull of Polymarket-v1 daily_aligned(+multi) shards, keep only lexicon-matched markets,
write data/ml_fills/YYYY_MM.parquet (ts,cid,p) + .markets.parquet (cid,slug,resolved_ts); delete each raw shard right after filtering.
Run: /opt/anaconda3/bin/python3 ml_fetch.py   (resumable: finished months are skipped)"""
import datetime as dt, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
from lexicon import slug_ok
REPO, ARC, RAW, OUT = "TimeSeventeen/Polymarket-v1", "data/archive", "data/raw/ml", "data/ml_fills"
FIRST, LAST = dt.date(2022, 11, 14), dt.date(2026, 4, 28)   # archive starts 2022-11-21; 7 d lookback margin
def free_gb(): return shutil.disk_usage("/").free / 1e9
def one(layer, d):
    from huggingface_hub import hf_hub_download
    name = f"{layer}/{d:%Y_%m_%d}.parquet"; own = os.path.join(ARC, name); keep = os.path.exists(own)
    p = own
    if not keep:
        for a in range(4):
            try: p = hf_hub_download(REPO, name, repo_type="dataset", local_dir=RAW); break
            except Exception as e:
                if "404" in repr(e) or "EntryNotFound" in repr(e): return None, 0
                time.sleep(2 ** a)
        else: print("FAILED", name, file=sys.stderr); return None, 0
    try:
        f = pd.read_parquet(p, columns=["block_timestamp", "condition_id", "market_slug", "p_event", "resolved_at"])
        n = len(f); ok = {s: slug_ok(s) for s in f.market_slug.dropna().unique()}
        f = f[f.market_slug.map(ok).fillna(False).astype(bool)]
        f = f.assign(resolved_ts=f.resolved_at.map(lambda x: x.timestamp() if pd.notna(x) else np.inf)).drop(columns="resolved_at")
        return f, n
    finally:
        if not keep and os.path.exists(p): os.remove(p)     # delete raw shard immediately
def month(y, m):
    days = [d for d in (dt.date(y, m, 1) + dt.timedelta(i) for i in range(31)) if d.month == m and FIRST <= d <= LAST]
    jobs = [(l, d) for d in days for l in ("daily_aligned", "daily_aligned_multi")]
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda j: one(*j), jobs))
    parts = [r[0] for r in res if r[0] is not None]; raw = sum(r[1] for r in res)
    if not parts: return 0, raw
    f = pd.concat(parts).sort_values("block_timestamp", kind="stable")
    mk = f.groupby("condition_id").agg(slug=("market_slug", "first"), resolved_ts=("resolved_ts", "first")).reset_index().rename(columns={"condition_id": "cid"})
    f = pd.DataFrame({"ts": f.block_timestamp.astype("int64").values, "cid": f.condition_id.values, "p": f.p_event.astype("float32").values})
    f.to_parquet(f"{OUT}/{y}_{m:02d}.parquet"); mk.to_parquet(f"{OUT}/{y}_{m:02d}.markets.parquet")
    return len(f), raw
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); os.makedirs(RAW, exist_ok=True)
    y, m = FIRST.year, FIRST.month
    while dt.date(y, m, 1) <= LAST:
        if not os.path.exists(f"{OUT}/{y}_{m:02d}.markets.parquet"):
            assert free_gb() > 10, f"disk low: {free_gb():.1f} GB"
            t = time.time(); n, raw = month(y, m)
            print(f"{y}-{m:02d} kept {n:,} of {raw:,} fills  {time.time()-t:.0f}s  free {free_gb():.1f} GB  raw_dir {sum(os.path.getsize(os.path.join(r,f)) for r,_,fs in os.walk(RAW) for f in fs)/1e6:.0f} MB", flush=True)
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
