"""Synthetic checks for leadlag.py / leadlag_map.py: known leader jump, known sibling response, known trade result, known placebo."""
import numpy as np, pandas as pd
import leadlag as L, leadlag_map as M

DAY = 1_750_000_000 - 1_750_000_000 % 86400      # a UTC midnight
T0 = DAY + 12 * 3600

def mk(rows):  # rows [(ts, p)] -> (ts, p, usd) with $10 per fill
    r = sorted(rows); return (np.array([a for a, _ in r], "int64"), np.array([b for _, b in r], float), np.full(len(r), 10.0))

def fam_exclusive():
    A = [(T0 - 20000 + 450 * k, 0.50) for k in range(40)] + [(T0 - 100, 0.50), (T0, 0.55), (T0 + 10, 0.56), (T0 + 1500, 0.62)]
    B = [(T0 - 20000 + 600 * k, 0.30) for k in range(25)] + [(T0 - 50, 0.30), (T0 + 40, 0.28), (T0 + 200, 0.27), (T0 + 800, 0.26), (T0 + 1000, 0.25), (T0 + 1200, 0.24)]
    C = [(T0 - 20000 + 600 * k, 0.20) for k in range(25)]            # never trades after t0
    D = [(T0 - 5000 + 100 * k, 0.10) for k in range(5)]              # < 20 fills: not a sibling
    return {"a": mk(A), "b": mk(B), "c": mk(C), "d": mk(D)}

def test_exclusive_known_answers():
    P, Q = L.analyse_family("F1", "exclusive", fam_exclusive(), T0 - 3600, T0 + 3600, np.random.RandomState(0))
    assert {(p["leader"], p["sib"]) for p in P} == {("a", "b"), ("a", "c")}     # one jump: the 2nd one at +1500 s is ignored, d is not a sibling
    assert len({p["t0"] for p in P}) == 1 and P[0]["t0"] == T0
    b = next(p for p in P if p["sib"] == "b"); c = next(p for p in P if p["sib"] == "c")
    assert b["d"] == -1 and abs(b["p_ref"] - 0.50) < 1e-9 and abs(b["p_jump"] - 0.55) < 1e-9
    assert abs(b["m60"] - 2.0) < 1e-6 and abs(b["m300"] - 3.0) < 1e-6 and abs(b["m900"] - 4.0) < 1e-6 and abs(b["first"] - 2.0) < 1e-6
    assert b["ok5"] and b["ok30"] and b["ok120"]
    assert abs(b["pts0_30"] - 3.0) < 1e-6 and abs(b["pts0_5"] - 3.0) < 1e-6 and abs(b["pts0_120"] - 2.0) < 1e-6
    assert abs(b["ptsF_30"] - (3.0 - 4 * (0.28 * 0.72 + 0.25 * 0.75))) < 1e-6
    assert b["avail30"] == 0.0 and b["avail_incl30"] == 10.0 and b["avail120"] == 0.0
    assert not c["ok5"] and not c["ok30"] and c["m900"] == 0.0 and np.isnan(c["first"])
    assert 0 < len(Q) <= 40
    for q in Q:                                                              # placebo: same day, >= 2 h from the jump, same sign, B is flat there
        assert abs(q["t0"] - T0) >= 7200 and q["t0"] // 86400 == T0 // 86400 and q["d"] == -1
        if q["ok30"]: assert q["pts0_30"] == 0.0 and q["m900"] == 0.0

def test_second_jump_alone_is_ignored():
    A = [(T0 - 20000 + 450 * k, 0.50) for k in range(40)] + [(T0, 0.55), (T0 + 1700, 0.62)]   # 2nd candidate 1700 s after the first
    m = {"a": mk(A), "b": fam_exclusive()["b"]}
    ji, _ = L.jumps_of(*m["a"][:2])
    assert list(m["a"][0][ji]) == [T0]
    A2 = A[:-1] + [(T0 + 1900, 0.62)]                                                           # 1900 s later is a new episode
    ji, _ = L.jumps_of(*mk(A2)[:2])
    assert list(mk(A2)[0][ji]) == [T0, T0 + 1900]

def test_ladder_same_sign_and_non_leader_ignored():
    Ld = [(T0 - 20000 + 450 * k, 0.60) for k in range(40)] + [(T0, 0.55)]
    S = [(T0 - 20000 + 600 * k, 0.40) for k in range(25)] + [(T0 + 10, 0.38), (T0 + 900, 0.35)]
    P, _ = L.analyse_family("F2", "ladder", {"l": mk(Ld), "s": mk(S)}, T0 - 3600, T0 + 3600, np.random.RandomState(0))
    assert len(P) == 1 and P[0]["d"] == -1 and abs(P[0]["pts0_5"] - 3.0) < 1e-6
    # the 3-point drop in the thin sibling is a jump candidate but S is not the leader (fewer fills) -> no second pair
    assert all(p["leader"] == "l" for p in P)

def test_burst_flag():
    base = [(T0 - 20000 + 450 * k, 0.50) for k in range(40)]
    for extra, want in (([(T0 - 100, 0.50), (T0, 0.55)], False), ([(T0 - 30, 0.50), (T0, 0.55)], True)):
        P, _ = L.analyse_family("F3", "exclusive", {"a": mk(base + extra), "b": fam_exclusive()["b"]}, T0 - 3600, T0 + 3600, np.random.RandomState(0))
        assert len(P) == 1 and P[0]["burst"] is want

def test_stat_and_bar():
    tr = pd.DataFrame({"jump": ["a", "a", "b", "c"], "v": [1.0, 3.0, 2.0, 2.0]})
    s = L.stat(tr, "v"); assert s["n"] == 4 and s["jumps"] == 3 and abs(s["mean"] - 2.0) < 1e-9 and s["lo"] <= 2.0 <= s["hi"]

def test_template_ladder_rules():
    assert M.normalise("Will Bitcoin reach $100,000 by March 31?") == ("will bitcoin reach <N> by <D>?", ("march 31",), ("100000",))
    assert M.normalise("Price between 80k and 82k") is None
    rows = lambda qs, nr=False: [{"cid": f"c{i}", "found": True, "question": q, "events": [{"id": 1, "negRisk": nr}]} for i, q in enumerate(qs)]
    fm = M.build(rows(["Will X happen by April 7?", "Will X happen by April 30?"])); assert set(fm.kind) == {"ladder"}
    fm = M.build(rows(["Will X happen in April?", "Will X happen in May?"])); assert set(fm.kind) == {"single"}     # 'in' is not nested
    fm = M.build(rows(["Will BTC reach $80k by June 1?", "Will BTC reach $90k by June 30?"])); assert set(fm.kind) == {"dropped:two_dims"}
    fm = M.build(rows(["A?", "B?"], nr=True)); assert set(fm.kind) == {"exclusive"}
    fm = M.build([{"cid": "z", "found": False}]); assert fm.kind[0] == "nogamma"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
