"""Daily bars per market from every fill, both layers, in Yes (outcome_seq 1) terms.

Per (condition_id, day): open, close, vwap, hi, lo, usd, n, imb (taker $ buying Yes-equivalent minus selling),
big_imb (same, fills >= $500 only), first_ts, last_ts, and taker_pnl / taker_pnl_res_usd: hold-to-resolution PnL of
the takers on resolved markets (makers earn the negative; fees ignored), with small (< $100) and big (>= $500) fills
split out. Resumable per month.
Run:  python behav_bars.py      Out: data/behav/bars/bars_YYYY_MM.parquet
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import behav_build as bb

OUT = bb.OUT / "bars"
COLS = ["block_timestamp", "condition_id", "outcome_seq", "p_event", "taker_direction", "usdc_amount"]


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
        return None
    f = pd.concat(frames, ignore_index=True).sort_values("block_timestamp")
    yes_buy = (f.taker_direction.eq("BUY") == f.outcome_seq.eq(1))
    f["signed"] = np.where(yes_buy, f.usdc_amount, -f.usdc_amount)
    f["big"] = np.where(f.usdc_amount >= 500, f.signed, 0.0)
    f["pv"] = f.p_event * f.usdc_amount
    f = f.join(pay, on="condition_id")
    price = np.where(f.outcome_seq == 1, f.p_event, 1 - f.p_event)  # price of the token traded
    v = np.where(f.outcome_seq == 1, f.v1, 1 - f.v1)
    buy = f.taker_direction.eq("BUY").to_numpy()
    pnl = f.usdc_amount * (v / np.clip(price, 1e-3, None) - 1)
    f["tpnl"] = np.where(buy, pnl, -pnl)                # NaN if unresolved
    f["tres"] = np.where(np.isnan(v), 0.0, f.usdc_amount)
    small, bigf = f.usdc_amount < 100, f.usdc_amount >= 500
    f["tpnl_s"], f["tres_s"] = np.where(small, f.tpnl, 0.0), np.where(small, f.tres, 0.0)
    f["tpnl_b"], f["tres_b"] = np.where(bigf, f.tpnl, 0.0), np.where(bigf, f.tres, 0.0)
    g = f.groupby("condition_id")
    b = pd.DataFrame({"open": g.p_event.first(), "close": g.p_event.last(), "hi": g.p_event.max(), "lo": g.p_event.min(),
                      "usd": g.usdc_amount.sum(), "n": g.size(), "imb": g.signed.sum(), "big_imb": g.big.sum(),
                      "first_ts": g.block_timestamp.first(), "last_ts": g.block_timestamp.last(),
                      "taker_pnl": g.tpnl.sum(), "taker_res_usd": g.tres.sum(), "taker_pnl_s": g.tpnl_s.sum(),
                      "taker_res_s": g.tres_s.sum(), "taker_pnl_b": g.tpnl_b.sum(), "taker_res_b": g.tres_b.sum()})
    b["vwap"] = g.pv.sum() / b.usd
    return b.reset_index().assign(day=d.isoformat())


def main(start="2022-11-21", end="2026-04-28"):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(bb.tempfile.mkdtemp(prefix="bars_"))
    r = pd.read_parquet(bb.OUT / "resolutions.parquet", columns=["condition_id", "payout"])
    p = r.payout.str.split(",", expand=True).iloc[:, :2].astype(float)
    pay = pd.DataFrame({"v1": (p[0] / p.sum(1).replace(0, np.nan)).to_numpy()}, index=r.condition_id)
    d, stop = date.fromisoformat(start), date.fromisoformat(end)
    while d <= stop:
        m0 = d.replace(day=1); nxt = (m0 + timedelta(days=32)).replace(day=1)
        out = OUT / f"bars_{m0:%Y_%m}.parquet"
        if out.exists():
            d = nxt; continue
        parts = []
        while d < nxt and d <= stop:
            x = day(d, tmp, pay)
            if x is not None:
                parts.append(x)
            d += timedelta(days=1)
        if parts:
            pd.concat(parts, ignore_index=True).to_parquet(out)
        print(f"{m0:%Y-%m} done", flush=True)


if __name__ == "__main__":
    main()
