# C2 family map (2025 archive markets, Gamma event membership)

Counts over all 2025 markets with >= 1 fill in daily_aligned(+multi) (2024-12-31..2025-12-31 shards).

| kind                     |    markets |         fills |             usd |   usd_share |   mkt_share |
|:-------------------------|-----------:|--------------:|----------------:|------------:|------------:|
| dropped:between          |    12.0000 |     3976.0000 |     559858.7321 |      0.0001 |      0.0001 |
| dropped:duplicate_values |    81.0000 |   617384.0000 |   95851564.4499 |      0.0099 |      0.0004 |
| dropped:two_dims         |     7.0000 |     4846.0000 |    1168415.4393 |      0.0001 |      0.0000 |
| exclusive                | 47046.0000 | 42742210.0000 | 2787882043.4117 |      0.2869 |      0.2238 |
| ladder                   | 10251.0000 |  9042204.0000 | 1078292343.9884 |      0.1110 |      0.0488 |
| nogamma                  |   923.0000 |  1808372.0000 |   60102552.8271 |      0.0062 |      0.0044 |
| not_looked_up:<20_fills  | 52874.0000 |   358222.0000 |   19676126.2518 |      0.0020 |      0.2515 |
| not_looked_up:up_or_down | 55955.0000 | 60757820.0000 | 1104562360.8123 |      0.1137 |      0.2661 |
| single                   | 43112.0000 | 27523035.0000 | 4569026749.5927 |      0.4702 |      0.2050 |

Families:

| kind      |   families |   median_members |   max_members |
|:----------|-----------:|-----------------:|--------------:|
| exclusive |       8107 |                3 |           123 |
| ladder    |       1558 |                6 |            25 |

Gamma lookup: 101,432 markets looked up; found 99.1%; markets placed in exclusive or ladder family = 27.3% of all markets, 39.8% of USDC volume; of looked-up markets 56.5%.
Cross-check: archive neg_risk_market_id == Gamma negRiskMarketID for 100.0% of 47,593 markets with both.

Raw Gamma responses (trimmed to id/slug/question/endDate/negRisk/events): `data/leadlag/gamma_markets.jsonl` (not committed, ~100k lines; fetched by `leadlag_gamma.py` on 2026-10-12 before any price measure was computed).
Lookup list = 2025 archive markets with >= 20 fills in 2025 and a slug not matching `up-or-down|updown` (short-horizon crypto markets; 0 of 902 sampled such markets shared an event with another market, so they are single-market events by construction). Everything else is counted above as not looked up.
"single" = in an event with no ladder partner among archive markets (or a non-negRisk event whose questions do not share a template).
Only archive markets can be members; an event member that never traded in 2025 is absent.
Ladder rule: see `leadlag_map.py` docstring (committed with this file). Amendment before commit: threshold cues extended to `> >= < <=` after a first look at the largest unplaced events (no price examined).
