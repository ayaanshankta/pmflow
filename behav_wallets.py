"""Wallet-level data for B14-B17 (research/behavioral-rules.md, round 2).

One pass over both layers. Per fill: buyer/seller of the token, hold-to-resolution PnL from the on-chain payout
(buyer usdc*(v/price - 1), seller the negative; fees ignored). Writes per month (resumable; existing parts are skipped):
  data/behav/wallets/agg_YYYY_MM.parquet     wallet, month, res_month, usd, pnl, n, buy_usd, buy_px_usd
  data/behav/wallets/sample_YYYY_MM.parquet  every fill of sample wallets (int(addr,16) % 50 == 0), one row per side
  data/behav/wallets/px_YYYY_MM.parquet      last p_event per (day, condition_id), for marking sample positions
Run:  python behav_wallets.py
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import behav_build as bb

OUT = bb.OUT / "wallets"
COLS = ["block_timestamp", "condition_id", "outcome_seq", "price", "p_event", "maker", "taker", "taker_direction", "usdc_amount"]
_sample = {}


def in_sample(a):
    if a not in _sample:
        _sample[a] = int(a, 16) % 50 == 0
    return _sample[a]


def payouts():
    r = pd.read_parquet(bb.OUT / "resolutions.parquet", columns=["condition_id", "payout", "res_ts"])
    p = r.payout.str.split(",", expand=True).iloc[:, :2].astype(float)
    tot = p.sum(1).replace(0, np.nan)
    r["v1"], r["v2"] = p[0] / tot, p[1] / tot  # payout per share of outcome_seq 1 / 2
    r["res_month"] = pd.to_datetime(r.res_ts, unit="s").dt.strftime("%Y-%m")
    return r.set_index("condition_id")[["v1", "v2", "res_month"]]


def day(d, tmp, pay):
    frames = []
    for layer in bb.LAYERS:
        fn = f"{layer}/{d:%Y_%m_%d}.parquet"
        cached = Path(__file__).parent / "data" / "archive" / fn
        try:
            p = cached if cached.exists() else Path(bb.hf_hub_download(bb.REPO, fn, repo_type="dataset", local_dir=tmp))
        except Exception as e:
            print(f"  {fn}: {type(e).__name__}", flush=True)
            continue
        frames.append(pd.read_parquet(p, columns=COLS))
        if not cached.exists():
            p.unlink()
    if not frames:
        return None, None, None
    f = pd.concat(frames, ignore_index=True)
    f = f[f.price > 0].join(pay, on="condition_id")
    v = np.where(f.outcome_seq == 1, f.v1, f.v2)
    pnl_buy = f.usdc_amount * (v / f.price - 1)  # NaN for unresolved markets
    buy = f.taker_direction.eq("BUY")
    m = f"{d:%Y-%m}"
    base = dict(month=m, res_month=f.res_month.fillna("none").to_numpy(), usd=f.usdc_amount.to_numpy(), n=1)
    b = pd.DataFrame(dict(wallet=np.where(buy, f.taker, f.maker), pnl=pnl_buy.to_numpy(), side=1, **base))
    s = pd.DataFrame(dict(wallet=np.where(buy, f.maker, f.taker), pnl=-pnl_buy.to_numpy(), side=-1, **base))
    sides = pd.concat([b, s], ignore_index=True)
    price = np.r_[f.price.to_numpy(), f.price.to_numpy()]
    sides["buy_usd"] = np.where(sides.side == 1, sides.usd, 0)
    sides["buy_px_usd"] = np.where(sides.side == 1, sides.usd * price, 0)
    agg = sides.groupby(["wallet", "month", "res_month"], sort=False)[["usd", "pnl", "n", "buy_usd", "buy_px_usd"]].sum().reset_index()
    smp = sides.wallet.map(in_sample).to_numpy()
    meta = pd.concat([f, f], ignore_index=True)
    sample = pd.DataFrame({"wallet": sides.wallet[smp], "ts": meta.block_timestamp[smp], "condition_id": meta.condition_id[smp],
                           "outcome_seq": meta.outcome_seq[smp], "price": price[smp], "side": sides.side[smp],
                           "usd": sides.usd[smp], "v": np.r_[v, v][smp]})
    px = f.sort_values("block_timestamp").groupby("condition_id").p_event.last().astype("float32").reset_index().assign(day=d.isoformat())
    return agg, sample, px


def main(start="2022-11-21", end="2026-04-28"):
    OUT.mkdir(parents=True, exist_ok=True)
    pay, tmp = payouts(), Path(bb.tempfile.mkdtemp(prefix="wal_"))
    d, stop = date.fromisoformat(start), date.fromisoformat(end)
    while d <= stop:
        m0, parts = d.replace(day=1), {"agg": [], "sample": [], "px": []}
        nxt = (m0 + timedelta(days=32)).replace(day=1)
        if (OUT / f"agg_{m0:%Y_%m}.parquet").exists():
            d = nxt
            continue
        while d < nxt and d <= stop:
            for k, x in zip(parts, day(d, tmp, pay)):
                if x is not None:
                    parts[k].append(x)
            d += timedelta(days=1)
        a = pd.concat(parts["agg"]).groupby(["wallet", "month", "res_month"])[["usd", "pnl", "n", "buy_usd", "buy_px_usd"]].sum().reset_index()
        pd.concat(parts["sample"]).to_parquet(OUT / f"sample_{m0:%Y_%m}.parquet")
        pd.concat(parts["px"]).to_parquet(OUT / f"px_{m0:%Y_%m}.parquet")
        a.to_parquet(OUT / f"agg_{m0:%Y_%m}.parquet")  # written last: its existence marks the month done
        print(f"{m0:%Y-%m} wallets {a.wallet.nunique():,} fills {int(a.n.sum()) // 2:,}", flush=True)


if __name__ == "__main__":
    main()
