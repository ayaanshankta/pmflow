"""Family slice on hand-built Gamma events (universe.with_family, families.from_universe). Run: python -m pytest -q test_family_slice.py"""
import pandas as pd
import universe as u
import families


def mk(cid, q, vol, end="2026-12-31T00:00:00Z", book=True, closed=False):
    return dict(conditionId=cid, question=q, active=True, closed=closed, enableOrderBook=book, clobTokenIds=f'["y{cid}","n{cid}"]',
                outcomes='["Yes","No"]', volume24hr=vol, liquidityNum=1, endDate=end, groupItemTitle=q[-12:])


def ev(eid, title, markets, neg=False, tags=()):
    return dict(id=eid, title=title, slug=title.lower().replace(" ", "-"), negRisk=neg, markets=markets, tags=[dict(id=t, label=t, slug=t) for t in tags])


E1 = ev("E1", "Fed decision", [mk("a1", "Fed cut 25?", 900), mk("a2", "Fed hold?", 5), mk("a3", "Fed hike 25?", 5)], neg=True)       # a1 in top; 2 to add
E2 = ev("E2", "Mayor", [mk("b1", "Alice wins?", 800), mk("b2", "Bob wins?", 1, book=False)], neg=True)                       # b2 has no book: not added, never recorded
E3 = ev("E3", "Big race", [mk("c1", "Cand 1 wins?", 100)] + [mk(f"c{i}", f"Cand {i} wins?", 1) for i in range(2, 7)], neg=True)  # 5 to add: over the cap
E4 = ev("E4", "Hormuz", [mk("d1", "Hormuz normal by September 30?", 700, "2026-10-01T00:00:00Z"), mk("d2", "Hormuz normal by October 31?", 2, "2026-11-01T00:00:00Z"),
                         mk("d3", "Hormuz normal by December 31?", 2, "2027-01-01T00:00:00Z")])                                 # ladder, 2 to add
E5 = ev("E5", "NBA Finals winner", [mk("e1", "Lakers win?", 50), mk("e2", "Celtics win?", 50)], neg=True, tags=("nba",))       # sports: excluded as today
E6 = ev("E6", "Single", [mk("f1", "Will it rain?", 10)])                                                                       # no family


def test_family_slice():
    df, n_sports = u.build([E1, E2, E3, E4, E5, E6], sport_ids={"nba"})
    assert n_sports == 2 and not {"e1", "e2"} & set(df.market_id)
    assert df.set_index("market_id").family_kind.to_dict() == dict(a1="exclusive", a2="exclusive", a3="exclusive", b1="exclusive", c1="exclusive",
        **{f"c{i}": "exclusive" for i in range(2, 7)}, d1="ladder", d2="ladder", d3="ladder", f1="none")
    d = df.set_index("market_id")
    assert d.loc["a1", "event_id"] == "E1" and d.loc["f1", "event_id"] == "E6"
    assert d.loc["d1", "family_rank"] == 2 and d.loc["d3", "family_rank"] == 0   # onset ladder: later deadline = weaker = rank 0
    assert d.loc["b1", "family_size"] == 2 and d.loc["f1", "family_size"] is pd.NA  # b2 (no book) still counts toward the family's size

    top = df[df.market_id.isin(["a1", "b1", "c1", "d1", "f1"])].assign(slice="top200")
    out, left = u.with_family(df, top, cap=8)
    added = set(out[out.slice == "family"].market_id)
    # 5 in top. Priority = share of family volume already in: E4 .994, E1 .989, E3 .952. E4 (+2) -> 7; E1 (+2) would be 9 > 8: left out
    # whole (a2/a3 absent, not just one of them); E3 (+5) left out whole too.
    assert out.market_id.is_unique and len(out) == 7
    assert added == {"d2", "d3"} and left == 2
    assert not {"c2", "c3", "c4", "c5", "c6"} & set(out.market_id)  # never part of a family
    assert "b2" not in set(out.market_id)                           # no order book
    assert (out.set_index("market_id").loc[["a1", "b1", "c1", "d1", "f1"], "slice"] == "top200").all()  # original label kept

    out2, left2 = u.with_family(df, top, cap=450)  # roomy cap: E3 now fits, whole
    assert {"c2", "c3", "c4", "c5", "c6", "a2", "a3", "d2", "d3"} == set(out2[out2.slice == "family"].market_id) and left2 == 0
    # every added family is whole
    for key, g in out2[out2.family_kind != "none"].groupby("family_key"):
        assert g.market_id.isin(df[df.family_key == key].market_id).all() and len(g) == len(df[df.family_key == key])


def test_from_universe_matches_api_map():
    df, _ = u.build([E1, E2, E3, E4, E6])
    top = df.assign(slice="top200")
    fm = families.from_universe(top, set(top.market_id))
    api = families.build(dict(recorded=list(top.market_id), events={e["id"]: e for e in [E1, E2, E3, E4, E6]}))
    key = lambda m: sorted((f["kind"], f["event_id"], f["n_members"], f["n_recorded"], f["complete"]) for f in m["families"])
    assert key(fm) == key(api)
    byev = {f["event_id"]: f for f in fm["families"]}
    assert byev["E1"]["complete"] and not byev["E2"]["complete"]   # E2 has a member without a book: never complete
    assert [m["market_id"] for m in byev["E4"]["members"]] == ["d3", "d2", "d1"]  # weakest first


def test_pinned_added_whole_and_labelled():
    import pandas as pd, universe as U
    df = pd.DataFrame(dict(market_id=["a", "b", "c", "d"], event_id=["1", "9", "9", "9"], volume24hr=[5.0, 1.0, 0.5, 0.0]))
    top = df.head(2).assign(slice="top200")                      # "b" (event 9) is already in the universe
    out = U.with_pinned(df, top, ids=("9",))
    assert out.market_id.tolist() == ["a", "b", "c", "d"]        # the rest of event 9 is added, nothing duplicated
    assert out.set_index("market_id").slice.to_dict() == {"a": "top200", "b": "top200", "c": "pinned", "d": "pinned"}
    assert U.with_pinned(df, top, ids=("404",)).equals(top)      # unknown event: unchanged


def test_cap_arg_and_pinned_over_cap():
    import pandas as pd, universe as U
    assert U.cap_arg(["universe.py"]) == U.FAMILY_CAP and U.cap_arg(["universe.py", "--cap", "300"]) == 300
    df, _ = U.build([E1, E3, E4, E6])
    pinned = df[df.market_id.isin(["c1", "c2", "c3", "c4"])].assign(slice="pinned")   # 4 pinned markets, a family split across cap
    top = pd.concat([df[df.market_id.isin(["a1", "d1", "f1"])].assign(slice="top200"), pinned], ignore_index=True)  # 7 already in
    out, left = U.with_family(df, top, cap=5)                                       # pinned + top already exceed the cap
    assert out.market_id.tolist() == top.market_id.tolist() and left == 3           # nothing added, nothing trimmed (c5/c6 of E3 are not added)
    assert (out[out.slice == "pinned"].market_id.tolist() == ["c1", "c2", "c3", "c4"])
    out, left = U.with_family(df, top, cap=7); assert len(out) == 7 and left == 3   # exactly at the cap: still no family fits
    out, left = U.with_family(df, top, cap=9); assert set(out[out.slice == "family"].market_id) == {"d2", "d3"} and left == 2   # fits whole or not at all
