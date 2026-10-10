"""Prediction-market reaction around a time t0 (adapted from newsflow's reaction.py): delta_p = mid(t0+h) - mid0
in probability points at +1/5/15/60 min, time-to-reprice, spread, update rate and mid vol before vs after.
Window definitions: DECISIONS.md "Reaction windows" / "Time-to-reprice" / "Placebo".

Reads data/tob/{venue}/{market_id}/date=YYYY-MM-DD.parquet (recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).parent / "data/tob"
S = 1_000_000_000  # ns per second
HORIZONS = {"1m": 60, "5m": 300, "15m": 900, "60m": 3600}  # seconds
WIN = 900       # pre/post window length, s
STALE = 60      # a quote older than this is not "the price now", s
TICK = 0.01     # time-to-reprice threshold, probability points
KEYS = ["mid0"] + [f"dp_{h}" for h in HORIZONS] + ["t_reprice_s"] + [
    f"{m}_{w}" for m in ("spread", "rate", "vol") for w in ("pre", "post")] + ["conn_break"]


def _ns(t):
    t = pd.Timestamp(t)
    return (t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")).value


def load_tob(venue, market_id, t0_utc, before_min=16, after_min=60, root=ROOT):  # 16: one extra minute so the first 1 s vol tick at t0-15m has a quote
    """Rows with recv_ns in [t0-before, t0+after], from every UTC date file that window touches."""
    lo, hi = _ns(t0_utc) - before_min * 60 * S, _ns(t0_utc) + after_min * 60 * S
    days = pd.date_range(pd.Timestamp(lo, tz="UTC").normalize(), pd.Timestamp(hi, tz="UTC").normalize())
    fs = [f for d in days if (f := Path(root) / venue / str(market_id) / f"date={d:%Y-%m-%d}.parquet").exists()]
    if not fs:
        return pd.DataFrame(columns=["recv_ns", "conn_id", "bid_px", "ask_px", "mid"])
    t = pd.concat([pq.read_table(f, filters=[("recv_ns", ">=", lo), ("recv_ns", "<=", hi)]).to_pandas() for f in fs],
                  ignore_index=True).sort_values("recv_ns", kind="stable", ignore_index=True)
    t["mid"] = (t.bid_px + t.ask_px) / 2
    return t


def _vol(ns, mid, conn, start):
    """Std of 1 s mid changes (probability points) on the grid start, start+1s, ..., start+WIN (last quote at or before
    each tick). Changes spanning a conn_id change, or ticks with no quote yet, are dropped."""
    i = np.searchsorted(ns, start + np.arange(WIN + 1) * S, side="right") - 1
    ok = i >= 0
    lm, c = mid[i], conn[i]
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
            out[f"dp_{h}"] = mid[j] - mid[i0]
    # time-to-reprice: first quote after t0 with |mid - mid0| >= 1 tick, within 60 min, no conn_id change before it
    end = np.searchsorted(ns, t0 + HORIZONS["60m"] * S, side="right")
    hit = np.flatnonzero(np.abs(mid[i0:end] - mid[i0]) >= TICK - 1e-9)
    if len(hit) and (conn[i0:i0 + hit[0] + 1] == conn[i0]).all():
        out["t_reprice_s"] = (ns[i0 + hit[0]] - t0) / S
    rel = (tob.ask_px - tob.bid_px).to_numpy(float)  # absolute spread, probability points (relative is meaningless near 0)
    for w, a in (("pre", t0 - WIN * S), ("post", t0)):
        m = (ns >= a) & (ns < a + WIN * S)
        out[f"spread_{w}"] = float(np.median(rel[m])) if m.any() else np.nan
        out[f"rate_{w}"] = m.sum() / WIN
        out[f"vol_{w}"] = _vol(ns, mid, conn, a)
    w = (ns >= t0 - WIN * S) & (ns <= t0 + HORIZONS["60m"] * S)
    out["conn_break"] = bool(len(np.unique(conn[w])) > 1)
    return out


def _day_type(x):
    return "weekend" if pd.Timestamp(x).dayofweek >= 5 else "weekday"


def placebo_times(dates, n_per_event, seed, day_type_of):
    """n_per_event UTC times for ONE real event: pick uniformly among `dates` whose day type (weekday/weekend,
    UTC) equals that of `day_type_of` (the event's t0 or date), then a uniform time of day excluding the first and
    last 60 min of the day. Seeded; call once per event (vary seed per event). Raises if no date matches."""
    dt = _day_type(day_type_of)
    ds = sorted({pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates if _day_type(d) == dt})
    if not ds:
        raise ValueError(f"no {dt} date among {list(dates)}")
    rng = np.random.default_rng(seed)
    days = pd.to_datetime(rng.choice(ds, n_per_event)).tz_localize("UTC")
    return sorted(days + pd.to_timedelta(rng.uniform(3600, 86400 - 3600, n_per_event), unit="s"))
