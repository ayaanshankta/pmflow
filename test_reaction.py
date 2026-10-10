"""Known-answer checks for reaction.py / run_reactions.py on synthetic top-of-book. Run: python3 -m pytest -q"""
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from reaction import STALE, load_tob, measure, placebo_times
from run_reactions import boot, run, summary

S = 1_000_000_000
T0 = pd.Timestamp("2026-01-01 12:00", tz="UTC")
t0 = T0.value
STEP = 0.05


def frame(ts_s, conn_switch_s=None, step_s=30, step=STEP, base=0.50):
    """Quotes at t0+ts_s seconds; mid `base` before t0+step_s, base+step from then; spread 0.02."""
    ts = np.asarray(ts_s, float)
    mid = np.where(ts >= step_s, base + step, base)
    conn = np.where(ts >= conn_switch_s, 2, 1) if conn_switch_s is not None else np.ones(len(ts), int)
    return pd.DataFrame({"recv_ns": (t0 + ts * S).astype("int64"), "conn_id": conn,
                         "bid_px": mid - 0.01, "ask_px": mid + 0.01, "bid_sz": 1.0, "ask_sz": 1.0, "mid": mid})


# 1 quote/s before t0, 2 quotes/s after, out to t0+70 min; reconnect at t0+10 min.
ts = np.r_[np.arange(-1200, 0, 1.0), np.arange(0, 4200, 0.5)]


def test_dp_and_windows():
    m = measure(frame(ts, conn_switch_s=600), T0)
    assert math.isclose(m["mid0"], 0.5)
    assert math.isclose(m["dp_1m"], STEP) and math.isclose(m["dp_5m"], STEP)
    assert math.isnan(m["dp_15m"]) and math.isnan(m["dp_60m"])          # cross the reconnect
    assert math.isclose(m["spread_pre"], 0.02) and math.isclose(m["spread_post"], 0.02)
    assert m["rate_pre"] == 1.0 and m["rate_post"] == 2.0 and m["vol_pre"] == 0.0
    # 900 one-second changes in post grid, one is STEP; the one spanning the reconnect is dropped -> 899
    assert math.isclose(m["vol_post"], STEP / math.sqrt(899))
    assert m["conn_break"] is True
    m = measure(frame(ts), T0)                                          # no reconnect
    assert math.isclose(m["dp_15m"], STEP) and math.isclose(m["dp_60m"], STEP)
    assert math.isclose(m["vol_post"], STEP / 30) and m["conn_break"] is False


def test_t_reprice():
    x = np.unique(np.r_[ts, 37.0])
    m = measure(frame(x, step_s=37), T0)
    assert m["t_reprice_s"] == 37.0 and math.isclose(m["dp_1m"], STEP)
    assert measure(frame(x, step_s=37, step=-STEP), T0)["t_reprice_s"] == 37.0    # down move too
    assert measure(frame(x, step_s=37, step=0.009), T0)["t_reprice_s"] != m["t_reprice_s"]  # < 1 tick: no reprice
    assert math.isnan(measure(frame(x, step_s=37, step=0.009), T0)["t_reprice_s"])
    assert math.isnan(measure(frame(ts, step_s=1e9), T0)["t_reprice_s"])           # no change at all
    assert math.isnan(measure(frame(x, step_s=3700), T0)["t_reprice_s"])           # change only after 60 min
    assert measure(frame(x, step_s=3500), T0)["t_reprice_s"] == 3500.0
    # conn_id break before the step -> NaN (dp_1m is NaN too: same rule as the return windows)
    m = measure(frame(x, conn_switch_s=20, step_s=37), T0)
    assert math.isnan(m["t_reprice_s"]) and math.isnan(m["dp_1m"])
    # break after the step -> still 37
    assert measure(frame(x, conn_switch_s=50, step_s=37), T0)["t_reprice_s"] == 37.0


def test_stale_and_empty():
    m = measure(frame(ts[ts <= 120]), T0)                               # quotes stop at t0+2 min
    assert all(math.isclose(m[f"dp_{h}"], STEP) for h in ("1m", "5m", "15m", "60m"))  # standing quote (STALE=3600)
    gap = ts[(ts < -(STALE + 1)) | (ts > 0)]                           # last quote at/before t0 is STALE+2 s old
    assert all(math.isnan(v) for v in measure(frame(gap), T0).values())
    assert measure(frame(np.r_[[-(STALE - 1.0)], ts[ts > 0]]), T0)["mid0"] == 0.5   # one quote STALE-1 s old is still the price
    assert all(math.isnan(v) for v in measure(frame([]), T0).values())
    # standing quote after the step: the 37 s quote is still the price at t0+5m (STALE=3600, DECISIONS 2026-10-10)
    m = measure(frame(np.r_[np.arange(-60, 0, 1.0), [10.0, 37.0]], step_s=37), T0)
    assert m["t_reprice_s"] == 37.0 and math.isclose(m["dp_5m"], STEP)


def test_load_tob_path_and_midnight():
    with tempfile.TemporaryDirectory() as root:
        d = Path(root) / "kalshi" / "KXFOO-1"
        d.mkdir(parents=True)
        tm = pd.Timestamp("2026-01-02 00:05", tz="UTC")
        for day in ("2026-01-01", "2026-01-02"):
            f = frame(np.arange(0, 86400, 10.0))
            f["recv_ns"] = pd.Timestamp(day, tz="UTC").value + np.arange(len(f)) * 10 * S
            f.drop(columns="mid").to_parquet(d / f"date={day}.parquet")
        t = load_tob("kalshi", "KXFOO-1", tm, root=root)
        lo, hi = tm.value - 960 * S, tm.value + 3600 * S
        assert t.recv_ns.min() == lo and t.recv_ns.max() == hi and len(t) == 4560 // 10 + 1
        assert t.recv_ns.is_monotonic_increasing and "mid" in t
        assert len(load_tob("kalshi", "KXFOO-1", "2030-01-01 12:00", root=root)) == 0
        assert len(load_tob("polymarket", "KXFOO-1", tm, root=root)) == 0   # venue is part of the path


def test_placebo_day_type_and_bounds():
    dates = ["2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05"]       # Fri Sat Sun Mon
    wk = placebo_times(dates, 500, 1, "2026-10-07 15:00")                  # Wed -> weekday
    we = placebo_times(dates, 500, 1, pd.Timestamp("2026-10-10 03:00", tz="UTC"))  # Sat -> weekend
    assert {x.strftime("%Y-%m-%d") for x in wk} == {"2026-10-02", "2026-10-05"}
    assert {x.strftime("%Y-%m-%d") for x in we} == {"2026-10-03", "2026-10-04"}
    for p in (wk, we):
        h = np.array([x.hour + x.minute / 60 for x in p])
        assert len(p) == 500 and h.min() >= 1 and h.max() < 23
    assert wk == placebo_times(dates, 500, 1, "2026-10-07")
    assert wk != placebo_times(dates, 500, 2, "2026-10-07")
    try:
        placebo_times(["2026-10-03"], 20, 0, "2026-10-07")
        assert False
    except ValueError:
        pass


def test_bootstrap_ci_covers_planted_effect():
    rng = np.random.default_rng(5)
    ev = {i: np.abs(0.04 + 0.02 * rng.standard_normal(1)) for i in range(60)}      # planted mean |dp| ~ 0.04
    pl = {i: np.abs(0.01 * rng.standard_normal(20)) for i in range(60)}            # placebo mean ~ 0.008
    p, lo, hi, n = boot(ev, np.mean)
    assert lo < 0.04 < hi and lo > 0.03 and n == 60
    pp, plo, phi, pn = boot(pl, np.mean)
    assert phi < lo and pn == 1200 and abs(pp - 0.008) < 0.002
    assert boot(ev, np.mean) == boot(ev, np.mean)                                  # seed 0 deterministic
    assert boot({}, np.mean)[3] == 0


def _synthetic(root, n_events=8, step=STEP):
    """Markets m0..: flat 0.50 quotes every 10 s Sat 2026-10-03 .. Wed 2026-10-07; each event steps +/-step at
    t0+37 s for 2 h. Returns the events frame."""
    days = pd.date_range("2026-10-03", "2026-10-07", tz="UTC")
    evs = []
    for i in range(n_events):
        t0e = pd.Timestamp("2026-10-03 14:00", tz="UTC") + pd.Timedelta(days=i % 2 * 2) + pd.Timedelta(minutes=7 * i)
        sgn = 1 if i % 2 == 0 else -1
        evs.append(dict(event_id=f"e{i}", t0_utc=t0e, venue="polymarket", market_id=f"m{i}",
                        direction="up" if sgn > 0 else "down", source="synthetic"))
        lo = days[0].value
        t = np.arange(lo, lo + 5 * 86400 * S, 10 * S)
        t = np.unique(np.r_[t, t0e.value + 37 * S, t0e.value + 37 * S + 7200 * S])
        on = (t >= t0e.value + 37 * S) & (t < t0e.value + 37 * S + 7200 * S)
        mid = 0.5 + sgn * step * on
        f = pd.DataFrame({"recv_ns": t, "conn_id": 1, "bid_px": mid - .01, "ask_px": mid + .01, "bid_sz": 1., "ask_sz": 1.})
        d = Path(root) / "polymarket" / f"m{i}"
        d.mkdir(parents=True)
        for day in days:
            m = (f.recv_ns >= day.value) & (f.recv_ns < day.value + 86400 * S)
            f[m].to_parquet(d / f"date={day:%Y-%m-%d}.parquet")
    return pd.DataFrame(evs)


def test_end_to_end_synthetic():
    with tempfile.TemporaryDirectory() as root:
        ev = _synthetic(root)
        df = run(ev, root=root, n_placebo=20, seed=0)
        e, p = df[df.kind == "event"], df[df.kind == "placebo"]
        assert len(e) == 8 and len(p) == 160
        assert (e.t_reprice_s == 37.0).all() and np.allclose(e.dp_1m.abs(), STEP)
        # placebo day type matches the event's, and never in the first/last hour
        wk = lambda t: t.dayofweek >= 5
        for eid, g in p.groupby("event_id"):
            t0e = e[e.event_id == eid].t0_utc.iloc[0]
            assert len(g) == 20 and all(wk(t) == wk(t0e) for t in g.t0_utc)
            assert all(1 <= t.hour + t.minute / 60 < 23 for t in g.t0_utc)
        s = summary(df).set_index("metric")
        a = s.loc["|dp_5m|"]
        assert math.isclose(a.event_est, STEP) and a.event_n == 8 and a.event_lo <= STEP <= a.event_hi
        assert a.placebo_est < 0.02 and a.placebo_n == 160 and a.placebo_est < a.event_lo
        assert s.loc["t_reprice_s"].event_est == 37.0
        assert math.isclose(s.loc["signed dp_15m"].event_est, STEP)       # called direction matches the planted move
        none = ev.assign(direction="none")
        assert summary(run(none, root=root, n_placebo=20)).event_n.eq(0).all()      # direction none -> excluded
        print(s.to_string(float_format=lambda x: f"{x:.4g}"))
