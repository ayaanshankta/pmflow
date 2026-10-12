"""Hand-made fill stream with known fills / exits / fees. Run: /opt/anaconda3/bin/python3 -m pytest -q test_replay_truth.py"""
import numpy as np, pandas as pd, pytest
import replay_truth as R

T0 = 10_000
# before t0: 5 fills at 0.40; after: trades at +1 (0.42), +3 (0.45), +50 (0.50), +400 (0.60), +800 (0.55), +1000 (0.70), +1100 (0.90)
TS = np.array([T0 - 50, T0 - 40, T0 - 30, T0 - 20, T0 - 10, T0 + 1, T0 + 3, T0 + 50, T0 + 400, T0 + 800, T0 + 1000, T0 + 1100])
PS = np.array([.4] * 5 + [.42, .45, .50, .60, .55, .70, .90])

def test_fill_and_exit():
    assert R.fill_exit(TS, PS, T0, 2) == ("ok", .45, .70)      # first trade >= t0+2 is +3; last in [+720,+1080] is +1000
    assert R.fill_exit(TS, PS, T0, 10) == ("ok", .50, .70)     # +50
    assert R.fill_exit(TS, PS, T0, 30) == ("ok", .50, .70)

def test_nofill_when_gap_over_60s():
    ts = np.array([T0 - 1, T0 + 100, T0 + 800]); ps = np.array([.4, .5, .6])
    assert R.fill_exit(ts, ps, T0, 2)[0] == "nofill"           # next trade at +100 > 2+60
    assert R.fill_exit(ts, ps, T0, 40)[0] == "ok"              # +100 <= 40+60

def test_noexit():
    ts = np.array([T0 - 1, T0 + 5, T0 + 300, T0 + 1200]); ps = np.array([.4, .5, .6, .7])
    assert R.fill_exit(ts, ps, T0, 2)[0] == "noexit"           # nothing in [+720,+1080]

def test_pnl_long_short_fees():
    # long at .45, exit .70, $500: 1111.11 sh, gross $277.78 = 25 pts
    p, u = R.pnl(1, .45, .70, 0)
    assert p == pytest.approx(25.0) and u == pytest.approx(500 / .45 * .25)
    # 1% fee: entry 5.00 + exit 0.01*1111.11*.70 = 7.78 -> usd 277.78-12.78 ; pts = usd/sh*100
    p, u = R.pnl(1, .45, .70, .01)
    assert u == pytest.approx(500 / .45 * .25 - 5 - .01 * (500 / .45) * .70)
    assert p == pytest.approx(100 * u / (500 / .45))
    # short = buy NO at .55, NO exit value .30 -> loses 25 pts gross
    p, u = R.pnl(-1, .45, .70, 0)
    assert p == pytest.approx(-25.0) and u < 0
    # 2% fee costs more than 1%
    assert R.pnl(1, .45, .70, .02)[1] < R.pnl(1, .45, .70, .01)[1]

def test_oracle_dir():
    assert R.oracle_dir(TS, PS, T0) == 1                       # first post trade .42 > mean .40
    assert R.oracle_dir(TS, np.where(np.arange(len(PS)) == 5, .30, PS), T0) == -1
    assert R.oracle_dir(TS[:5], PS[:5], T0) == 0               # no post trade

def test_lexicon_dir_known():
    assert R.lexicon_dir("Bitcoin surges to a record", "will-bitcoin-hit-100k") == 1
    assert R.lexicon_dir("Bitcoin crashes after hack", "will-bitcoin-hit-100k") == -1
    assert R.lexicon_dir("Congratulations to the great state of Ohio", "will-bitcoin-hit-100k") == 0

def test_run_counts_end_to_end():
    ts = np.concatenate([np.arange(T0 - 3600, T0, 60), [T0 + 3, T0 + 1000]]); ps = np.concatenate([np.full(60, .4), [.45, .70]])
    P = pd.DataFrame([dict(event=0, rank=0, cid="a", kind="event", t0=T0, slug="will-bitcoin-hit-100k", post_id="p"),
                      dict(event=0, rank=0, cid="a", kind="placebo", t0=T0 + 500, slug="will-bitcoin-hit-100k", post_id="p"),
                      dict(event=0, rank=1, cid="b", kind="event", t0=T0, slug="x", post_id="p")])
    g = {"a": (ts, ps), "b": (TS, PS)}                        # b has only 5 prior fills -> illiquid
    Tr, c = R.run(P, g, {"p": "Bitcoin surges to a record"})
    assert c[("event", "illiquid")] == 1 and c[("event", "liquid")] == 1
    e = Tr[(Tr.kind == "event") & (Tr.arm == "lexicon") & (Tr.delta == 2)].iloc[0]
    assert (e.p_in, e.p_out, e.sign) == (.45, .70, 1) and e["pts_0"] == pytest.approx(25.0)
    # placebo at T0+500: liquid, next trade is +500 s away -> no fill; counted, not traded
    assert c[(("placebo", "lexicon", 2)), "nofill"] == 1
    assert not ((Tr.kind == "placebo")).any()

def _T(n, pts):
    return pd.DataFrame([dict(kind="event", arm="lexicon", delta=2, event=e, rank=0, t0=0, sign=1, p_in=.5, p_out=.5,
                              **{f"pts_{f:g}": pts for f in R.FEES}, **{f"usd_{f:g}": 2 * pts for f in R.FEES}) for e in range(n)])

def test_bootstrap_table_and_verdict():
    a = R.table(_T(30, 10.0))
    assert a.equals(R.table(_T(30, 10.0))) and (a.pts == 10).all() and (a.pts_lo == 10).all() and (a.hit == 1).all() and (a.n == 30).all()
    assert R.verdict(a)[2] is False                      # n < 100 -> cannot pass
    assert R.verdict(R.table(_T(120, 10.0))) == {2: True, 10: False, 30: False}   # only delta 2 present
    assert R.verdict(R.table(_T(120, -1.0)))[2] is False
