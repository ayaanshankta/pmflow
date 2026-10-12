"""Run: /opt/anaconda3/bin/python3 -m pytest -q test_replay_llm.py"""
import numpy as np, pandas as pd, pytest
import replay_llm as L, replay_truth as R

T0 = 10_000
TS = np.array([T0 - 50, T0 - 40, T0 - 30, T0 - 20, T0 - 10, T0 + 1, T0 + 3, T0 + 50, T0 + 400, T0 + 800, T0 + 1000, T0 + 1100])
PS = np.array([.4] * 5 + [.42, .45, .50, .60, .55, .70, .90])

@pytest.mark.parametrize("s,d", [("up", 1), ("Up.", 1), (" DOWN\n", -1), ("none", 0), ("**none**", 0)])
def test_parse_ok(s, d): assert L.parse_dir(s) == d

@pytest.mark.parametrize("s", ["", None, "up or down", "upward", "I think up", "none, because", "yes", "up\ndown"])
def test_parse_fail_is_none_not_zero(s): assert L.parse_dir(s) is None   # failure must never be read as 'none'

def test_prompt_is_read_from_file_and_has_no_price_or_date_slots():
    msg = L.user_message("Tariffs on China!", "will-china-tariff-hit-60")
    assert msg.startswith("Post: Tariffs on China!\nMarket: will china tariff hit 60\n")
    assert "{" not in msg and "{" not in L.SYSTEM and "none" in L.SYSTEM

def test_entry_first_vs_next():
    assert L.entry(TS, PS, T0, 2, 0) == R.fill_exit(TS, PS, T0, 2) == ("ok", .45, .70)
    assert L.entry(TS, PS, T0, 2, 1) == ("ok", .50, .70)      # trade after the +3 one is +50 (<= 2+60)
    ts = np.array([T0 - 1, T0 + 3, T0 + 100, T0 + 800]); ps = np.array([.4, .5, .6, .7])
    assert L.entry(ts, ps, T0, 2, 1)[0] == "nofill"            # next trade is at +100 > 2+60

def test_taker_fee_by_hand():
    p, u = L.pnl_taker(1, .45, .70)
    sh = 500 / .45
    assert u == pytest.approx(sh * .25 - .04 * .45 * .55 * 500 - .04 * .70 * .30 * sh * .70)
    assert p == pytest.approx(100 * u / sh)
    assert L.pnl_taker(1, .5, .5)[1] == pytest.approx(-(.04 * .25 * 500) * 2)   # flat price: only fees, 1% each side at p=.5
    # long and its mirror short pay the same fee at the same prices
    assert L.pnl_taker(-1, .45, .45)[1] == pytest.approx(L.pnl_taker(1, .45, .45)[1])

def test_placebo_uses_event_direction_not_local_move():
    # liquid history, price FALLS after the placebo time; event's LLM direction is +1 (up), so the placebo trade is a long that loses
    base = np.arange(T0 - 3600, T0 + 3600, 60)
    ts = np.concatenate([base, [T0 + 3, T0 + 1000, T0 + 600 + 3, T0 + 600 + 1000]]); o = np.argsort(ts, kind="stable"); ts = ts[o]
    ps = np.where(ts < T0 + 600, .50, .30)[:len(ts)]
    ps[np.searchsorted(ts, T0 + 3)] = .45; ps[np.searchsorted(ts, T0 + 1000)] = .70   # event: long wins
    P = pd.DataFrame([dict(event=7, rank=0, cid="a", kind="event", t0=T0, slug="s", post_id="p"),
                      dict(event=7, rank=0, cid="a", kind="placebo", t0=T0 + 600, slug="s", post_id="p")])
    for d in (1, -1):
        Tr, c = L.run(P, {"a": (ts, ps)}, {"7|a": d}, deltas=(2,))
        assert set(Tr[Tr.kind == "placebo"].sign) == {d} and set(Tr[Tr.kind == "event"].sign) == {d}
    Tr, _ = L.run(P, {"a": (ts, ps)}, {"7|a": 0})
    assert Tr.empty                                           # 'none' = no trade at event or placebo
    Tr, c = L.run(P, {"a": (ts, ps)}, {})
    assert Tr.empty and c[("event", "no_direction")] == 1 and c[("placebo", "no_direction")] == 1

def _T(ev_pts, pl_pts):
    rows = [dict(kind=k, entry=0, delta=2, event=e, rank=0, **{f"pts_{f}": x for f in L.FEE_COLS}, **{f"usd_{f}": 2 * x for f in L.FEE_COLS})
            for k, pts in (("event", ev_pts), ("placebo", pl_pts)) for e, xs in enumerate(pts) for x in xs]
    return pd.DataFrame(rows)

def test_table_diff_and_verdict():
    T = _T([[5.0]] * 120, [[1.0, 1.0]] * 120)
    Rt = L.table(T)
    d = Rt[(Rt.kind == "diff") & (Rt.fee == "tk")].iloc[0]
    assert d.pts == pytest.approx(4.0) and d.lo == pytest.approx(4.0) and d.hi == pytest.approx(4.0)
    assert Rt[(Rt.kind == "event") & (Rt.fee == "0.01")].n.iloc[0] == 120
    assert L.verdict(Rt)["entry0|d2|fee0.01"] is True and L.verdict(Rt)["entry0|d10|fee0.01"] is False
    assert L.verdict(L.table(_T([[5.0]] * 30, [[1.0]] * 30)))["entry0|d2|fee0.01"] is False   # n < 100
    assert L.verdict(L.table(_T([[-1.0]] * 120, [[1.0]] * 120)))["entry0|d2|fee0.01"] is False
