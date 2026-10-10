"""Order-book reaction around a time t0: mid returns at +1/5/15/60 min, spread, update rate and
realised vol before vs after. Window definitions: DECISIONS.md "Reaction windows".

Reads market-maker's tob parquet in place (read-only).
Run:  /opt/anaconda3/bin/python3 -W ignore reaction.py   (20 placebo times, coinbase BTC 2026-10-01)
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DERIVED = Path.home() / "Downloads/market-maker/derived"
S = 1_000_000_000  # ns per second
HORIZONS = {"1m": 60, "5m": 300, "15m": 900, "60m": 3600}  # seconds
WIN = 900       # pre/post window length, s
STALE = 60      # a quote older than this is not "the price now", s
KEYS = ["mid0"] + [f"ret_{h}" for h in HORIZONS] + [
    f"{m}_{w}" for m in ("spread", "rate", "vol") for w in ("pre", "post")] + ["conn_break"]


def _ns(t):
    t = pd.Timestamp(t)
    return (t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")).value


def load_tob(venue, coin, t0_utc, before_min=16, after_min=60, root=DERIVED):  # 16: one extra minute so the first 1 s vol tick at t0-15m has a quote
    """Rows with recv_ns in [t0-before, t0+after], from every UTC date file that window touches."""
    lo, hi = _ns(t0_utc) - before_min * 60 * S, _ns(t0_utc) + after_min * 60 * S
    days = pd.date_range(pd.Timestamp(lo, tz="UTC").normalize(), pd.Timestamp(hi, tz="UTC").normalize())
    fs = [f for d in days if (f := Path(root) / venue / f"{coin}-USD" / "tob" / f"date={d:%Y-%m-%d}.parquet").exists()]
    if not fs:
        return pd.DataFrame(columns=["recv_ns", "conn_id", "bid_px", "ask_px", "mid"])
    t = pd.concat([pq.read_table(f, filters=[("recv_ns", ">=", lo), ("recv_ns", "<=", hi)]).to_pandas() for f in fs],
                  ignore_index=True).sort_values("recv_ns", kind="stable", ignore_index=True)
    t["mid"] = (t.bid_px + t.ask_px) / 2
    return t


def _vol(ns, mid, conn, start):
    """Std of 1 s log-mid returns on the grid start, start+1s, ..., start+WIN (last quote at or before
    each tick). Returns spanning a conn_id change, or ticks with no quote yet, are dropped."""
    i = np.searchsorted(ns, start + np.arange(WIN + 1) * S, side="right") - 1
    ok = i >= 0
    lm, c = np.log(mid[i]), conn[i]
    r = np.diff(lm)[ok[1:] & ok[:-1] & (c[1:] == c[:-1])]
    return float(np.std(r, ddof=1)) if len(r) > 1 else np.nan


def measure(tob, t0):
    t0 = _ns(t0)
    ns, mid, conn = tob.recv_ns.to_numpy(), tob.mid.to_numpy(float), tob.conn_id.to_numpy()
    out = dict.fromkeys(KEYS, np.nan)
    i0 = np.searchsorted(ns, t0, side="right") - 1
    if i0 < 0 or t0 - ns[i0] > STALE * S:
        return out
    out["mid0"] = mid[i0]
    for h, sec in HORIZONS.items():
        j = np.searchsorted(ns, t0 + sec * S, side="right") - 1
        # ponytail: conn check spans the quote standing at t0 through the last quote <= t0+h
        if t0 + sec * S - ns[j] <= STALE * S and (conn[i0:j + 1] == conn[i0]).all():
            out[f"ret_{h}"] = np.log(mid[j] / mid[i0])
    rel = ((tob.ask_px - tob.bid_px) / tob.mid).to_numpy(float)
    for w, a in (("pre", t0 - WIN * S), ("post", t0)):
        m = (ns >= a) & (ns < a + WIN * S)
        out[f"spread_{w}"] = float(np.median(rel[m])) if m.any() else np.nan
        out[f"rate_{w}"] = m.sum() / WIN
        out[f"vol_{w}"] = _vol(ns, mid, conn, a)
    w = (ns >= t0 - WIN * S) & (ns <= t0 + HORIZONS["60m"] * S)
    out["conn_break"] = bool(len(np.unique(conn[w])) > 1)
    return out


def placebo_times(n, dates, seed):
    """n UTC times, uniform over the given dates, avoiding the first and last 60 min of each day."""
    rng = np.random.default_rng(seed)
    days = pd.to_datetime(rng.choice(list(dates), n)).tz_localize("UTC")
    return sorted(days + pd.to_timedelta(rng.uniform(3600, 86400 - 3600, n), unit="s"))


def main():
    rows, secs = [], []
    for t0 in placebo_times(20, ["2026-10-01"], seed=0):
        a = time.perf_counter()
        tob = load_tob("coinbase", "BTC", t0)
        secs.append(time.perf_counter() - a)
        rows.append({"t0": t0.strftime("%H:%M:%S"), **measure(tob, t0)})
    d = pd.DataFrame(rows)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(d.to_string(index=False, float_format=lambda x: f"{x:.3g}"))
        print("\nret means (bps):", (d.filter(like="ret_").mean() * 1e4).round(2).to_dict())
        print("ret n non-NaN:", d.filter(like="ret_").notna().sum().to_dict())
    print(f"load_tob: median {np.median(secs):.3f}s, max {max(secs):.3f}s per call")


if __name__ == "__main__":
    main()
