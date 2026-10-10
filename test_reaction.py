"""Known-answer checks for reaction.py on synthetic top-of-book. Run: python -W ignore test_reaction.py"""
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from reaction import load_tob, measure, placebo_times

S = 1_000_000_000
T0 = pd.Timestamp("2026-01-01 12:00", tz="UTC")
t0 = T0.value
X = math.log(1.01)


def frame(ts_s, conn_switch_s=None):
    """Quotes at t0+ts_s seconds; mid 100 before t0+30 s, 101 from then; spread 0.02."""
    ts = np.asarray(ts_s, float)
    mid = np.where(ts >= 30, 101.0, 100.0)
    conn = np.where(ts >= conn_switch_s, 2, 1) if conn_switch_s is not None else np.ones(len(ts), int)
    return pd.DataFrame({"recv_ns": (t0 + ts * S).astype("int64"), "conn_id": conn,
                         "bid_px": mid - 0.01, "ask_px": mid + 0.01, "bid_sz": 1.0, "ask_sz": 1.0,
                         "bid_sz5": 5.0, "ask_sz5": 5.0, "mid": mid})


# 1 quote/s before t0, 2 quotes/s after, out to t0+70 min; reconnect at t0+10 min.
ts = np.r_[np.arange(-1200, 0, 1.0), np.arange(0, 4200, 0.5)]
m = measure(frame(ts, conn_switch_s=600), T0)
print("main case:", {k: (round(v, 8) if isinstance(v, float) else v) for k, v in m.items()})
assert m["mid0"] == 100.0
assert math.isclose(m["ret_1m"], X) and math.isclose(m["ret_5m"], X)
assert math.isnan(m["ret_15m"]) and math.isnan(m["ret_60m"])          # cross the reconnect
assert math.isclose(m["spread_pre"], 0.02 / 100) and math.isclose(m["spread_post"], 0.02 / 101)
assert m["rate_pre"] == 1.0 and m["rate_post"] == 2.0
assert m["vol_pre"] == 0.0
# post grid t0..t0+900 s: 900 one-second returns, one of them X; the one spanning the reconnect
# (t0+599 -> t0+600) is dropped -> 899 returns, std(ddof=1) = X / sqrt(899)
assert math.isclose(m["vol_post"], X / math.sqrt(899))
assert m["conn_break"] is True

# No reconnect: 15 and 60 min returns exist, vol_post = X / sqrt(900) = X / 30.
m = measure(frame(ts), T0)
assert math.isclose(m["ret_15m"], X) and math.isclose(m["ret_60m"], X)
assert math.isclose(m["vol_post"], X / 30) and m["conn_break"] is False

# Quotes stop at t0+2 min: 1 m return fine, 5/15/60 m stale -> NaN.
m = measure(frame(ts[ts <= 120]), T0)
assert math.isclose(m["ret_1m"], X) and all(math.isnan(m[f"ret_{h}"]) for h in ("5m", "15m", "60m"))

# Last quote at or before t0 is 62 s old -> everything NaN. 60 s old -> fine.
gap = ts[(ts < -61) | (ts > 0)]
assert all(math.isnan(v) for v in measure(frame(gap), T0).values())
assert measure(frame(ts[(ts < -59) | (ts > 0)]), T0)["mid0"] == 100.0
# Empty frame -> everything NaN.
assert all(math.isnan(v) for v in measure(frame([]), T0).values())

# Midnight crossing: t0 = 00:05 needs the previous day's file too; only [t0-15m, t0+60m] is read.
with tempfile.TemporaryDirectory() as root:
    d = Path(root) / "coinbase" / "BTC-USD" / "tob"
    d.mkdir(parents=True)
    tm = pd.Timestamp("2026-01-02 00:05", tz="UTC")
    for day in ("2026-01-01", "2026-01-02"):
        f = frame(np.arange(0, 86400, 10.0))
        f["recv_ns"] = pd.Timestamp(day, tz="UTC").value + np.arange(len(f)) * 10 * S
        f.drop(columns="mid").to_parquet(d / f"date={day}.parquet")
    t = load_tob("coinbase", "BTC", tm, root=root)
    lo, hi = tm.value - 960 * S, tm.value + 3600 * S  # default before_min=16
    assert t.recv_ns.min() == lo and t.recv_ns.max() == hi and len(t) == 4560 // 10 + 1
    assert t.recv_ns.is_monotonic_increasing and "mid" in t
    assert len(load_tob("coinbase", "BTC", "2030-01-01 12:00", root=root)) == 0  # missing file -> empty

# Placebo times: inside the given dates, never in the first/last hour, reproducible.
p = placebo_times(2000, ["2026-10-01", "2026-10-02"], seed=1)
h = np.array([x.hour + x.minute / 60 for x in p])
assert len(p) == 2000 and h.min() >= 1 and h.max() < 23
assert {x.strftime("%Y-%m-%d") for x in p} == {"2026-10-01", "2026-10-02"}
assert p == placebo_times(2000, ["2026-10-01", "2026-10-02"], seed=1)
print("all reaction tests passed")
