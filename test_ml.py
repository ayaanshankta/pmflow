"""Checks for ml_dataset label construction, split rule, placebo draw. Run: /opt/anaconda3/bin/python3 -m pytest -q test_ml.py"""
import numpy as np
import ml_dataset as M
from ml_train import wilson

def fills(rows): a = np.array(rows, dtype=float); return a[:, 0].astype(np.int64), a[:, 1]

def test_label_known_dp15():
    # last 5 fills before t0=1000 are .50,.50,.50,.50,.60 (an older .90 must be ignored) -> p0 = .52
    ts, ps = fills([(10, .9), (900, .5), (910, .5), (920, .5), (930, .5), (999, .6),
                    (1000 + 719, .1),            # before window start t0+12m=1720 -> ignored
                    (1000 + 720, .55), (1000 + 1000, .60),   # in window; last = .60
                    (1000 + 1081, .99)])         # after t0+18m=2080 -> ignored
    r = M.label_times(ts, ps, [1000])
    assert abs(r["p0"][0] - 0.52) < 1e-9 and abs(r["dp15"][0] - 0.08) < 1e-9
    assert r["pre60"][0] == 6 and r["n7d"][0] == 6      # t0=1000 is < 1h/7d from the start, so the .9 fill at t=10 counts too
    assert abs(r["dp15"][0]) >= M.THR                   # -> y_move = 1, y_dir = +1

def test_label_nan_cases():
    ts, ps = fills([(900, .5), (910, .5)])
    assert np.isnan(M.label_times(ts, ps, [1000])["dp15"][0])       # no fill in [t0+12m, t0+18m] -> NaN -> row dropped
    assert np.isnan(M.label_times(ts, ps, [500])["p0"][0])           # no fill before t0 -> NaN
    ts, ps = fills([(900, .5), (1000 + 800, .505)])
    r = M.label_times(ts, ps, [1000]); assert abs(r["dp15"][0] - 0.005) < 1e-9 and abs(r["dp15"][0]) < M.THR   # y_move = 0

def test_window_edges_inclusive_and_ties():
    ts, ps = fills([(900, .5), (1720, .6), (2080, .7)])
    assert abs(M.label_times(ts, ps, [1000])["dp15"][0] - 0.2) < 1e-9   # both edges in window, last = .7
    ts, ps = fills([(1000, .9), (900, .5)][::-1]); assert M.label_times(ts, ps, [1000])["p0"][0] == 0.5   # a fill AT t0 is not "before"

def test_split_by_date():
    T = lambda y, m, d, H=0: M.TS(y, m, d, H)
    assert M.split_of(T(2022, 11, 1)) == "train" and M.split_of(T(2025, 9, 30, 23)) == "train"
    assert M.split_of(T(2025, 10, 1)) == "val" and M.split_of(T(2025, 12, 31, 23)) == "val"
    assert M.split_of(T(2026, 1, 1)) == "test" and M.split_of(T(2026, 4, 27, 22)) == "test"
    assert M.split_of(T(2022, 10, 31)) is None and M.split_of(T(2026, 4, 28)) is None

def test_placebo_same_label_rule_and_exclusion():
    rng = np.random.RandomState(1); t0 = M.TS(2025, 3, 1)
    ts = np.arange(t0 - 8 * M.DAY, t0 + 4 * M.DAY, 60, dtype=np.int64); ps = np.linspace(.2, .8, len(ts))
    excl = np.array([t0], dtype=np.int64)
    got = [M.draw_placebo(rng, t0, ts, excl, M.T_END) for _ in range(200)]
    got = [g for g in got if g is not None]; assert len(got) > 150
    assert all(abs(g - t0) >= 3600 and abs(g - t0) <= 3 * M.DAY for g in got)          # away from the headline, within +-3d
    r = M.label_times(ts, ps, got); assert not np.isnan(r["dp15"]).any() and (r["n7d"] >= M.MIN_FILLS).all()   # same rule, liquid
    assert M.draw_placebo(rng, t0, ts[:5], excl, M.T_END) is None                      # illiquid market -> no placebo

def test_recent_move_rate():
    ts = np.arange(0, 40 * M.DAY, 60, dtype=np.int64); ps = np.where((ts // 3600) % 2 == 0, .4, .6)   # alternates every hour: moves 0.2
    r = M.recent_move_rate(ts, ps, [30 * M.DAY]); assert r[0] == 1.0
    assert np.isnan(M.recent_move_rate(ts, ps, [100])[0])

def test_wilson():
    lo, hi = wilson(60, 100); assert 0.50 < lo < 0.51 and 0.69 < hi < 0.70
