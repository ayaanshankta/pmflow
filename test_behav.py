"""Hand-made days with known snapshot rows.  Run: python test_behav.py"""
from datetime import date

import pandas as pd

import behav_build as bb

U = lambda s: pd.Timestamp(s, tz="UTC")
def fill(day, hh, cid, p, usd, resolved="2030-01-01", win="No"):
    return dict(block_timestamp=int(U(f"{day} {hh}:00").timestamp()), p_event=p, usdc_amount=usd, condition_id=cid,
                outcome_seq=1, outcome_label="Yes", winning_outcome_label=win, resolution_status="resolved",
                taker_base_fee=0.0, close_at=U("2030-01-01"), resolved_at=U(resolved), market_slug=f"will-{cid}",
                category="Politics", layer="binary")
DAYS = {  # 2025-01-04 Sat, 05 Sun, 06 Mon, 13 Mon
    date(2025, 1, 4): [fill("2025-01-04", "10", "A", 0.30, 100)],
    date(2025, 1, 5): [fill("2025-01-05", "10", "A", 0.20, 100), fill("2025-01-05", "12", "A", 0.40, 300),
                       fill("2025-01-05", "09", "B", 0.50, 10, resolved="2025-01-05 23:00")],   # resolves before T
    date(2025, 1, 6): [fill("2025-01-06", "01", "A", 0.90, 1000)],                                 # after T: not in V
}
bb.load_day = lambda d, tmp: pd.DataFrame(DAYS[d]) if d in DAYS else None
import tempfile, pathlib
bb.OUT = pathlib.Path(tempfile.mkdtemp())
RES = pd.Series({"A": int(U("2030-01-01").timestamp()), "B": int(U("2025-01-05 23:00").timestamp())})
_State = bb.State
bb.State = lambda path, res_ts: _State(path, RES)       # on-chain resolution times, hand-made
bb.main("2025-01-01", "2025-01-20")
s = pd.read_parquet(bb.OUT / "snapshots.parquet")
t6 = s[s["T"] == U("2025-01-06")].set_index("condition_id")
assert list(t6.index) == ["A"], t6                                  # B resolved before T
a = t6.loc["A"]
assert abs(a.p - (0.2 * 100 + 0.4 * 300) / 400) < 1e-12, a.p        # Sunday VWAP = 0.35
assert abs(a.p_24h - 0.30) < 1e-12 and a.V == 500 and not a.p_from_last_fill, a
t13 = s[s["T"] == U("2025-01-13")].set_index("condition_id")
assert abs(t13.loc["A"].p - 0.90) < 1e-12 and t13.loc["A"].p_from_last_fill and t13.loc["A"].V == 1500, t13
t20 = s[s["T"] == U("2025-01-20")]
assert t20.empty, t20                                               # last fill 14 days old: not open
print("ALL BEHAV TESTS PASS")
