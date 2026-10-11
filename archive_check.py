"""Is the Polymarket-v1 archive (HF TimeSeventeen/Polymarket-v1) second-precise enough for a news-lag backtest?
Run: /opt/anaconda3/bin/python3 archive_check.py   (downloads ~130 MB daily files + 2 raw monthly shards ~0.4 GB into data/archive/)
Writes research/archive-check.md-style tables to stdout."""
import datetime as dt, json
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd, pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
REPO, OUT = "TimeSeventeen/Polymarket-v1", "data/archive"
ET = ZoneInfo("America/New_York")
MON = ["january","february","march","april","may","june","july","august","september","october","november","december"]
FOMC = ["2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10"]
CPI = ["2025-01-15","2025-02-12","2025-03-12","2025-04-10","2025-05-13","2025-06-11","2025-07-15","2025-08-12","2025-09-11","2025-10-24","2025-12-18"]
def t0(date, hh, mm):  # local ET -> UTC epoch (FOMC statement 14:00 ET, CPI 08:30 ET)
    d = dt.datetime.fromisoformat(date).replace(hour=hh, minute=mm, tzinfo=ET)
    return int(d.timestamp())
def day(date, layer):
    p = hf_hub_download(REPO, f"{layer}/{date.replace('-','_')}.parquet", repo_type="dataset", local_dir=OUT)
    return pd.read_parquet(p, columns=["block_timestamp","market_slug","condition_id","outcome_seq","p_event","usdc_amount"])
def fills(date, t):  # +-6h around t may cross UTC midnight -> load neighbours
    ds = {(dt.datetime.fromtimestamp(t+o, dt.UTC)).strftime("%Y-%m-%d") for o in (-21600, 21600)}
    f = pd.concat([day(d, l) for d in sorted(ds) for l in ("daily_aligned","daily_aligned_multi")])
    return f[(f.block_timestamp >= t-21600) & (f.block_timestamp <= t+21600)]
def pick(f, kind, date):
    m = MON[int(date[5:7])-1]
    s = f.market_slug
    if kind == "FOMC":   # the meeting that is being decided today
        return f[s.str.contains(rf"interest-rates-after-{m}-2025-meeting|interest-rates-by-\d+-bps-after-{m}-2025-meeting") & s.str.contains("fed")]
    prev = MON[(int(date[5:7])-2) % 12]  # CPI released this month is for previous month
    return f[s.str.contains(rf"(?:annual|monthly)-inflation.*-in-{prev}") & ~s.str.contains("powell")]
def row(kind, date, hh, mm):
    t = t0(date, hh, mm); f = pick(fills(date, t), kind, date)
    r = dict(kind=kind, date=date, t0_utc=dt.datetime.fromtimestamp(t, dt.UTC).strftime("%H:%M"), n6h=len(f))
    if f.empty: return r
    r["mkts"] = f.condition_id.nunique()
    d = f.block_timestamp - t
    r["pre60"] = int(((d >= -3600) & (d < 0)).sum()); r["post5"] = int(((d >= 0) & (d < 300)).sum())
    r["post1"] = int(((d >= 0) & (d < 60)).sum()); r["pre5"] = int(((d >= -300) & (d < 0)).sum())
    w = d[(d >= -3600) & (d < 3600)]; mins = (w // 60).value_counts()
    r["peak_min"] = int(mins.idxmax()) if len(mins) else None; r["peak_n"] = int(mins.max()) if len(mins) else 0
    # busiest market, reference-axis price before vs 15 min after
    top = f.condition_id.value_counts().idxmax(); g = f[f.condition_id == top].sort_values("block_timestamp")
    pre = g[g.block_timestamp < t]; post = g[(g.block_timestamp >= t+720) & (g.block_timestamp <= t+1080)]
    r["top_slug"] = g.market_slug.iloc[0][:55]
    r["p_pre"] = round(pre.p_event.iloc[-5:].mean(), 3) if len(pre) else None
    r["p_15m"] = round(post.p_event.mean(), 3) if len(post) else None
    # first post-t0 fill that moved >=2 pts from p_pre; seconds after t0
    if r["p_pre"] is not None:
        mv = g[(g.block_timestamp >= t) & ((g.p_event - r["p_pre"]).abs() >= 0.02)]
        r["first_move_s"] = int(mv.block_timestamp.iloc[0] - t) if len(mv) else None
    return r
def block_check(month):
    p = hf_hub_download(REPO, f"OrderFilled/{month}.parquet", repo_type="dataset", local_dir=OUT)
    t = pq.read_table(p, columns=["id","block_timestamp"]).to_pandas()
    t["blk"] = t.id.str.split("_").str[1].astype("int64")
    b = t.groupby("blk").block_timestamp.agg(["min","max"]).sort_index()
    dts = b["min"].diff().dropna(); dblk = b.index.to_series().diff().dropna()
    rate = dts / dblk                      # seconds per block between consecutive observed blocks
    return dict(shard=month, fills=len(t), blocks=len(b), blk_ts_conflicts=int((b["min"] != b["max"]).sum()),
                ts_monotone=bool((dts >= 0).all()), sec_per_block_median=float(rate.median()),
                sec_per_block_p99=float(rate.quantile(.99)), sec_per_block_max=float(rate.max()),
                n_gaps_over_10s=int((rate > 10).sum()), blk_min=int(b.index.min()), blk_max=int(b.index.max()))
if __name__ == "__main__":
    rows = [row("FOMC", d, 14, 0) for d in FOMC] + [row("CPI", d, 8, 30) for d in CPI]
    df = pd.DataFrame(rows); pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
    print(df.to_string(index=False)); df.to_csv("results/archive_check_events.csv", index=False)
    for m in ("2025_04", "2025_06"):
        print(json.dumps(block_check(m)))
