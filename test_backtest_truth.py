import numpy as np, pandas as pd
import backtest_truth as b
def test_lexicon():
    assert b.topics_of("New TARIFFS on China!") == ["tariff", "china"]
    assert b.topics_of("Federal Reserve should cut") == ["fed"]
    assert b.topics_of("Mexican food, Xiaomi, defend") == ["canada_mexico"]   # no 'xi' inside Xiaomi, no 'fed' inside defend
    assert len(b.clean("RT: https://x.co/a")) == 0
def test_burst_and_cap():
    m = pd.DataFrame(dict(t0=[0, 100, 800, 5000], id=list("abcd"), text="", topics=[["x"]]*4))
    assert list(b.select_events(m).id) == ["a", "c", "d"]   # b within 10 min of a
def test_measures():
    ts = np.array([0, 10, 20, 30, 40, 50, 1000, 1010, 1020, 1030]); ps = np.array([.5]*6 + [.5, .55, .5, .6])
    r = b.measures(ts, ps, 1005)
    assert r["post5"] == 3 and r["t_first"] == 5 and r["t_move"] == 5
    assert abs(r["p0"] - .5) < 1e-9 and r["pre60"] == 7
    assert b.measures(ts, ps, -5) is None
if __name__ == "__main__":
    test_lexicon(); test_burst_and_cap(); test_measures(); print("ok")
