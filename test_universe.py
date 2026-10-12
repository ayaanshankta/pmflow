from universe import is_sports
S = [  # (tags, question, expected)
    ([], "Will the Lakers win the NBA Finals?", True),
    (["Sports", "nba"], "Will LeBron score 30?", True),
    ([], "Will Tottenham win the Premier League?", True),
    ([], "Will Max Verstappen win the F1 championship?", True),
    ([], "Will Man City win the Champions League?", True),
    (["Soccer"], "Who wins?", True),
    ([], "Will Navi win the CS2 major?", True),
    ([], "Will Donald Trump win the 2028 election?", False),
    ([], "Will the Fed cut rates in December?", False),
    (["Politics", "Elections"], "Will Emma Smith be governor of Tennessee?", False),
    (["Crypto"], "Will Bitcoin hit $150k in October?", False),
    ([], "Will OpenAI release GPT-6 before 2027?", False),
]
for tags, q, exp in S:
    assert is_sports(tags, q) == exp, (tags, q, exp)
assert is_sports([], "x", "", "nfl-super-bowl-winner")  # slug hyphens split
print("ok", len(S) + 1)
import pandas as pd, universe as u
now = pd.Timestamp("2026-10-11T00:00:00Z")
rows = [dict(market_id=f"t{i}", end_date="2027-01-01T00:00:00Z", volume24hr=1000 - i) for i in range(u.TOP_N)]            # top200, long-dated
rows += [dict(market_id="t0s", end_date="2026-10-12T00:00:00Z", volume24hr=1)]                                              # ranked below 200, ends in 1 d
rows += [dict(market_id=f"s{i}", end_date="2026-10-13T00:00:00Z", volume24hr=0.5) for i in range(60)]                       # 60 short candidates
rows += [dict(market_id="past", end_date="2026-10-10T00:00:00Z", volume24hr=0.4), dict(market_id="far", end_date="2026-10-19T00:00:00Z", volume24hr=0.4)]
df = pd.DataFrame(rows).sort_values("volume24hr", ascending=False)
out = u.with_short(df, now)
assert out.slice.value_counts().to_dict() == {"top200": 200, "short": 50} and out.market_id.is_unique
assert "past" not in set(out.market_id) and "far" not in set(out.market_id) and "t0s" in set(out[out.slice == "short"].market_id)
print("slice ok")
from universe import econ
e = econ({"orderPriceMinTickSize": 0.001, "rewardsMinSize": 200, "rewardsMaxSpread": 5.5, "feesEnabled": True, "feeType": "politics_fees",
          "feeSchedule": {"exponent": 1, "rate": 0.04, "takerOnly": True, "rebateRate": 0.25}, "makerBaseFee": 1000,
          "clobRewards": [{"rewardsDailyRate": 55}, {"rewardsDailyRate": 5}]})
assert (e["tick_size"], e["rewards_min_size"], e["rewards_max_spread"], e["reward_daily_rate"], e["fee_rate"], e["fee_rebate_rate"]) == (0.001, 200, 5.5, 60, 0.04, 0.25)
assert econ({})["tick_size"] is None and econ({})["reward_daily_rate"] == 0 and econ({"feeSchedule": None})["fee_rate"] is None
print("econ ok")
