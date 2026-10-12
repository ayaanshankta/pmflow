"""Hand-built families with known violation episodes (C1). Run: python -m pytest -q test_sets.py"""
import numpy as np, pandas as pd
import sets_check as sc

S = 10**9
T0 = 1_000_000 * S


def frame(rows):
    """rows: (t_s, conn, bid, ask, bsz, asz)"""
    return pd.DataFrame([(T0 + int(t * S), c, b, a, bs, az) for t, c, b, a, bs, az in rows],
                        columns=["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"])


def fam(kind, ids, complete=True, ranks=None, rate=0.04):
    return dict(kind=kind, event_id="e", key="k", title="t", complete=complete, n_members=len(ids), n_recorded=len(ids),
                members=[dict(market_id=i, title=i, recorded=True, fee_rate=rate, rank=(ranks or [0] * len(ids))[n]) for n, i in enumerate(ids)])


def bystander():  # keeps the recording 'alive' (no global gap > 60 s) and defines the connection starts
    return frame([(t, 1 if t < 200 else 2, 0.1, 0.2, 10, 10) for t in range(0, 301, 30)])


def test_exclusive_fresh_stale_reconnect():
    X = frame([(0, 1, .38, .40, 100, 100), (100, 1, .28, .30, 100, 100), (130, 1, .38, .40, 100, 100),
               (200, 2, .18, .20, 100, 10), (215, 2, .18, .40, 100, 100)])
    Y = frame([(0, 1, .28, .30, 100, 50), (203, 2, .28, .30, 100, 50)])
    Z = frame([(0, 1, .28, .30, 100, 80), (10, 1, .24, .25, 100, 80), (15, 1, .28, .30, 100, 80), (205, 2, .28, .30, 100, 80)])
    frames = dict(X=X, Y=Y, Z=Z, W=bystander())
    tl = sc.make_timeline(frames)
    assert len(tl["win_start"]) == 1  # bystander keeps one window
    r = sc.analyse_family(fam("exclusive", ["X", "Y", "Z"]), frames, tl)
    ep = {(e["variant"], e["cls"], round((e["start_ns"] - T0) / S)): e for e in r["episodes"]}
    # fee variant: fresh [10,15) and [205,215); stale [100,130). Nothing in [200,205): Y and Z not re-sent, so not known.
    assert sorted(k for k in ep if k[0] == "fee") == [("fee", "fresh", 10), ("fee", "fresh", 205), ("fee", "stale", 100)]
    assert sorted(k for k in ep if k[0] == "c0") == [("c0", "fresh", 10), ("c0", "fresh", 205), ("c0", "stale", 100)]
    a = ep[("fee", "fresh", 10)]
    assert a["dur_s"] == 5 and abs(a["gross_pts"] - 5.0) < 1e-6 and abs(a["net_pts"] - 2.45) < 1e-6
    assert a["shares"] == 50 and abs(a["dollars"] - 47.5) < 1e-6
    b = ep[("fee", "fresh", 205)]
    assert b["dur_s"] == 10 and abs(b["gross_pts"] - 20.0) < 1e-6 and abs(b["net_pts"] - 17.68) < 1e-6
    assert b["shares"] == 10 and abs(b["dollars"] - 8.0) < 1e-6
    c = ep[("fee", "stale", 100)]
    assert c["dur_s"] == 30 and abs(c["gross_pts"] - 10.0) < 1e-6 and c["shares"] == 50
    assert all(l["age_s"] > 60 for l in c["legs"] if l["market"] in "YZ")  # Y, Z stale at the time
    # no B-side violation (bids sum 0.94 / 0.74)
    assert not any("sell" in e["cand"] for e in r["episodes"])
    assert r["episodes"] and all(e["dur_s"] > 0 for e in r["episodes"])


def test_ladder():
    Wk = frame([(0, 1, .48, .50, 100, 100)])                       # weaker claim (superset): ask .50
    St = frame([(0, 1, .40, .42, 40, 40), (10, 1, .55, .57, 40, 40), (20, 1, .45, .47, 40, 40)])  # stronger: bid .55 for [10,20)
    frames = dict(Wk=Wk, St=St, W=frame([(t, 1, .1, .2, 1, 1) for t in range(0, 61, 20)]))
    tl = sc.make_timeline(frames)
    r = sc.analyse_family(fam("ladder", ["Wk", "St"], ranks=[0, 1], complete=False), frames, tl)
    fe = [e for e in r["episodes"] if e["variant"] == "fee" and e["cls"] == "fresh"]
    assert len(fe) == 1 and fe[0]["dur_s"] == 10 and abs(fe[0]["gross_pts"] - 5.0) < 1e-6
    assert abs(fe[0]["net_pts"] - (5.0 - 100 * 0.04 * (0.5 * 0.5 + 0.55 * 0.45))) < 1e-6
    assert fe[0]["shares"] == 40 and abs(fe[0]["dollars"] - 20.0) < 1e-6
    assert fe[0]["cand"] == "L: buy Wk / sell St"
    # reversed ranks (St is the superset): only the other direction is tested; there bid(Wk)=.48 > ask(St)=.42 before t=10
    r2 = sc.analyse_family(fam("ladder", ["Wk", "St"], ranks=[1, 0], complete=False), frames, tl)
    assert r2["episodes"] and all(e["cand"] == "L: buy St / sell Wk" for e in r2["episodes"])


def test_no_violation_and_gap_cut():
    # sum of asks = 1.0 exactly, then a 4-hour recording gap: nothing is carried across it
    X = frame([(0, 1, .4, .5, 10, 10), (10_000, 2, .4, .5, 10, 10)])
    Y = frame([(0, 1, .4, .5, 10, 10), (10_000, 2, .4, .4, 10, 10)])  # after the gap the ask is .4: A = .9
    frames = dict(X=X, Y=Y)
    tl = sc.make_timeline(frames)
    assert len(tl["win_start"]) == 2
    r = sc.analyse_family(fam("exclusive", ["X", "Y"]), frames, tl)
    ep = [e for e in r["episodes"] if e["variant"] == "c0"]
    assert ep == [] or all(e["start_ns"] >= T0 + 10_000 * S for e in ep)  # the violation exists only after the gap, never spanning it
    assert r["evaluable_s"] < 100


def test_bid_side_with_empty_leg():
    # 3 legs, Z has no bid at all: B = .52 + .50 = 1.02 > 1 -> riskless to sell X and Y (c=0 and, at 0 fee rate, fee too)
    X = frame([(0, 1, .52, .60, 30, 100)])
    Y = frame([(0, 1, .50, .55, 20, 100)])
    Z = frame([(0, 1, np.nan, .70, np.nan, 100)])
    frames = dict(X=X, Y=Y, Z=Z, W=frame([(t, 1, .1, .2, 1, 1) for t in range(0, 41, 20)]))
    r = sc.analyse_family(fam("exclusive", ["X", "Y", "Z"], rate=0.0), frames, sc.make_timeline(frames))
    e = [x for x in r["episodes"] if x["variant"] == "fee" and x["cls"] == "fresh"]
    assert len(e) == 1 and e[0]["dur_s"] == 40 and abs(e[0]["gross_pts"] - 2.0) < 1e-6
    assert e[0]["shares"] == 20 and abs(e[0]["dollars"] - 20 * 1.02) < 1e-6
    assert {l["market"] for l in e[0]["legs"]} == {"X", "Y"}
