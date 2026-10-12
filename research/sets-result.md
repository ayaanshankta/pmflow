# C1 result: are related Polymarket markets priced consistently? (2026-10-12)

Rules: `research/structure-rules.md`, blob hash `1582327e1f20` (Definitions + C1). Family map committed first: `families.py` + `research/sets-ladder-rule.md` at 203480a, before any price was read. Code: `sets_check.py`, tests `test_sets.py` (4 hand-built cases) and the whole suite (60 passed).
Data: `data/tob/polymarket`, 200 markets, 2026-10-10 08:06:06-20:23:59 UTC, recorded 08:06-14:58 and 19:17-20:24 (7.98 h observed, 4.3 h hole). Gamma events fetched 2026-10-12 (`data/sets_gamma_events_raw.json`).

## Verdict (against the bar in C1)

**No evidence of tradeable mispricing; the bar is not met, and on this data it could not have been met.** The bar needs at least 20 fee-clearing episodes lasting >= 2 s with >= $100 available, across >= 3 complete families. This recording holds exactly **one** complete exclusive family (Elon Musk tweet count, Oct 6-13, 14 brackets) and **zero** complete ladders. On that family: **0** fee-clearing episodes at any duration (after the venue fee). At zero cost it shows 22 fresh-quote episodes (13 of them >= 2 s), at most 2.0 points gross, at most 13 shares / $13. So "complete sets are priced consistently at the resolution we record" holds for what was testable, but the testable set is one family over 8 hours. This is a small-sample null, not a finding about Polymarket in general. The 250-market recording on the other machine and a rerun (command below) are what could say more.

Supplementary (not in the bar, flagged as such): partial exclusive families (sell-the-recorded-legs test, valid without completeness) and ladder pairs (exact relations, valid for any recorded pair). Across all of them: 41 fee-clearing fresh episodes, 29 lasting >= 2 s, 1 with >= $100 (a 0.09 s flicker, see below), in 4 of 37 testable families. Largest net gap after fee: 2.29 points, and it lasted 0.09 s.

## Counts and tables

| kind | completeness | recorded legs | families |
|---|---|---|---|
| exclusive | complete | testable | 1 |
| exclusive | partial | single recorded leg | 10 |
| exclusive | partial | testable | 20 |
| ladder | partial | single recorded leg | 13 |
| ladder | partial | testable | 16 |

Recording windows (UTC, cut where no market updated for > 60 s): 10-10 08:06:06-14:58:03, 10-10 19:17:02-20:23:59.

### Per family, after fee (fresh quotes; episodes / of which >= 2 s; duration median / p90 s; net gap points median / max; shares median / max; $ at peak median / max; time share; stale-quote episodes)

| scope | kind | event | title | legs | hours | episodes | >=2 s | dur med | dur p90 | gap med | gap max | shares med | shares max | $ med | $ max | share of time | stale eps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bar | exclusive | 1122453 | Elon Musk # tweets October 6 - October 13, 2 | 14/14 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1134913 | What price will Ethereum hit October 5-11? | 7/13 | 8.0 | 19 | 16 | 31.8 | 95.2 | 0.07 | 0.42 | 5 | 1701 | 0.01 | 5.10 | 2.85% | 17 |
| supplementary | exclusive | 1137875 | Elon Musk # tweets October 8 - October 10, 2 | 6/8 | 6.9 | 13 | 4 | 0.1 | 21.6 | 0.06 | 2.29 | 28 | 73 | 27.58 | 75.26 | 0.63% | 4 |
| supplementary | ladder | 1134901 | What price will Bitcoin hit October 5-11? | 4/9 | 8.0 | 7 | 7 | 33.2 | 53.4 | 0.14 | 0.14 | 5 | 72 | 0.01 | 0.29 | 0.82% | 7 |
| supplementary | ladder | 1124995 | Bitcoin above ___ on October 10? | 9/11 | 6.9 | 2 | 2 | 29.6 | 30.6 | 0.17 | 0.17 | 5 | 5 | 0.01 | 0.01 | 0.24% | 2 |
| supplementary | ladder | 1038648 | US-Iran ceasefire continues through...? | 6/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1061332 | Serbia Parliamentary Election Winner | 2/37 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1078055 | What will WTI Crude Oil (WTI) hit in October | 4/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1078055 | What will WTI Crude Oil (WTI) hit in October | 2/14 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1112205 | What price will Bitcoin hit in October? | 4/15 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1124989 | Bitcoin price on October 10? | 3/11 | 6.9 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1134901 | What price will Bitcoin hit October 5-11? | 4/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1140914 | Elon Musk # tweets October 9 - October 16, 2 | 9/25 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1152059 | Highest temperature in Wellington on October | 6/11 | 0.0 | 0 | 0 | - | - | - | - | - | - | - | - | nan% | 0 |
| supplementary | ladder | 255195 | Iran leadership change by...? | 2/14 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 267102 | Kharg Island no longer under Iranian control | 2/11 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 276527 | Bab el-Mandeb Strait effectively closed by.. | 2/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 30829 | Democratic Presidential Nominee 2028 | 3/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 31552 | Presidential Election Winner 2028 | 5/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 31875 | Republican Presidential Nominee 2028 | 4/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32224 | Which party will win the Senate in 2026? | 2/9 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32225 | Which party will win the House in 2026? | 2/9 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32228 | Balance of Power: 2026 Midterms | 4/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 45915 | Brazil Presidential Election | 2/15 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 48930 | NATO x Russia military clash by...? | 2/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 57111 | Los Angeles Mayoral Election | 2/6 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 57672 | Texas Senate Election Winner | 2/13 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 606422 | Fed Decision in October? | 4/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 637442 | Next Prime Minister of Spain? | 4/58 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 699735 | US announces end of Iranian blockade by...? | 3/23 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 711714 | Israel x Iran ceasefire continues through... | 3/27 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 79041 | Largest Company end of December 2026? | 3/28 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 79987 | Next French Presidential Election | 19/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 81557 | Prime Minister of Israel after the next elec | 6/28 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 848341 | Taipei Mayor Election Winner | 2/30 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 89502 | What price will Bitcoin hit in 2026? | 3/21 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 89519 | What price will Ethereum hit in 2026? | 2/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |

### Per family, zero cost (fresh quotes; episodes / of which >= 2 s; duration median / p90 s; net gap points median / max; shares median / max; $ at peak median / max; time share; stale-quote episodes)

| scope | kind | event | title | legs | hours | episodes | >=2 s | dur med | dur p90 | gap med | gap max | shares med | shares max | $ med | $ max | share of time | stale eps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bar | exclusive | 1122453 | Elon Musk # tweets October 6 - October 13, 2 | 14/14 | 8.0 | 22 | 13 | 11.0 | 60.0 | 0.55 | 2.00 | 5 | 13 | 5.19 | 13.05 | 1.86% | 236 |
| supplementary | exclusive | 848341 | Taipei Mayor Election Winner | 2/30 | 8.0 | 39 | 36 | 60.0 | 111.5 | 0.40 | 0.70 | 60 | 496 | 60.25 | 499.89 | 8.50% | 34 |
| supplementary | exclusive | 1137875 | Elon Musk # tweets October 8 - October 10, 2 | 6/8 | 6.9 | 32 | 18 | 8.1 | 84.8 | 0.20 | 3.10 | 13 | 118 | 13.08 | 117.78 | 3.21% | 16 |
| supplementary | ladder | 1134913 | What price will Ethereum hit October 5-11? | 7/13 | 8.0 | 19 | 16 | 31.8 | 95.2 | 0.10 | 0.50 | 5 | 1701 | 0.01 | 5.10 | 2.85% | 17 |
| supplementary | ladder | 1134901 | What price will Bitcoin hit October 5-11? | 4/9 | 8.0 | 7 | 7 | 33.2 | 53.4 | 0.20 | 0.20 | 5 | 72 | 0.01 | 0.29 | 0.82% | 7 |
| supplementary | ladder | 1124995 | Bitcoin above ___ on October 10? | 9/11 | 6.9 | 2 | 2 | 29.6 | 30.6 | 0.20 | 0.20 | 5 | 5 | 0.01 | 0.01 | 0.24% | 2 |
| supplementary | ladder | 1038648 | US-Iran ceasefire continues through...? | 6/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1061332 | Serbia Parliamentary Election Winner | 2/37 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1078055 | What will WTI Crude Oil (WTI) hit in October | 4/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1078055 | What will WTI Crude Oil (WTI) hit in October | 2/14 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1112205 | What price will Bitcoin hit in October? | 4/15 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1124989 | Bitcoin price on October 10? | 3/11 | 6.9 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 1134901 | What price will Bitcoin hit October 5-11? | 4/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1140914 | Elon Musk # tweets October 9 - October 16, 2 | 9/25 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 1152059 | Highest temperature in Wellington on October | 6/11 | 0.0 | 0 | 0 | - | - | - | - | - | - | - | - | nan% | 0 |
| supplementary | ladder | 255195 | Iran leadership change by...? | 2/14 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 267102 | Kharg Island no longer under Iranian control | 2/11 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 276527 | Bab el-Mandeb Strait effectively closed by.. | 2/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 30829 | Democratic Presidential Nominee 2028 | 3/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 31552 | Presidential Election Winner 2028 | 5/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 31875 | Republican Presidential Nominee 2028 | 4/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32224 | Which party will win the Senate in 2026? | 2/9 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32225 | Which party will win the House in 2026? | 2/9 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 32228 | Balance of Power: 2026 Midterms | 4/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 45915 | Brazil Presidential Election | 2/15 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 48930 | NATO x Russia military clash by...? | 2/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 57111 | Los Angeles Mayoral Election | 2/6 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 57672 | Texas Senate Election Winner | 2/13 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 606422 | Fed Decision in October? | 4/5 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 637442 | Next Prime Minister of Spain? | 4/58 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 699735 | US announces end of Iranian blockade by...? | 3/23 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 711714 | Israel x Iran ceasefire continues through... | 3/27 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 79041 | Largest Company end of December 2026? | 3/28 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 79987 | Next French Presidential Election | 19/128 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | exclusive | 81557 | Prime Minister of Israel after the next elec | 6/28 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 89502 | What price will Bitcoin hit in 2026? | 3/21 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |
| supplementary | ladder | 89519 | What price will Ethereum hit in 2026? | 2/12 | 8.0 | 0 | 0 | - | - | - | - | - | - | - | - | 0.00% | 0 |

- Bar (complete families only): 0 fee-clearing fresh episodes >= 2 s with >= $100 in 0 families (need 20 in 3).
- Bar (every testable family incl. partial and ladders): 1 fee-clearing fresh episodes >= 2 s with >= $100 in 1 families (need 20 in 3).

| variant | class | episodes | >= 2 s | >= 2 s and >= $100 |
|---|---|---|---|---|
| c0 | fresh | 121 | 92 | 22 |
| c0 | stale | 312 | 128 | 16 |
| fee | fresh | 41 | 29 | 1 |
| fee | stale | 30 | 26 | 0 |

### Three largest fresh episodes, fee (by profit at peak = shares x net gap)

- family 1137875 start 14:53:22.401644Z dur 0.090 s, B: sell YES on legs with a bid, gross 3.10 / net 2.29 pts, 73 shares, $75.26, profit $1.67; legs: 90-114 bid 0.926x970 (age 0.18s); 115-139 bid 0.105x73 (age 0.00s)
- family 1134913:Will Ethereum reach <NUM><DATE>? start 09:00:38.881535Z dur 20.119 s, L: buy ↑ 3,100 / sell ↑ 3,200, gross 0.10 / net 0.05 pts, 1701 shares, $5.10, profit $0.87; legs: ↑ 3,100 ask 0.003x3720 (age 0.04s); ↑ 3,200 bid 0.004x1701 (age 0.00s)
- family 1134913:Will Ethereum reach <NUM><DATE>? start 11:53:12.842578Z dur 60.000 s, L: buy ↑ 2,900 / sell ↑ 3,000, gross 0.10 / net 0.07 pts, 200 shares, $0.40, profit $0.13; legs: ↑ 2,900 ask 0.002x200 (age 0.00s); ↑ 3,000 bid 0.003x1695 (age 0.00s)

### Three largest fresh episodes, c0 (by profit at peak = shares x net gap)

- family 848341 start 08:44:20.848107Z dur 88.962 s, B: sell YES on legs with a bid, gross 0.70 / net 0.70 pts, 496 shares, $499.89, profit $3.47; legs: Chiang Wan-an bid 0.670x1032 (age 0.00s); Puma Shen bid 0.337x496 (age 0.00s)
- family 848341 start 08:46:35.524185Z dur 61.261 s, B: sell YES on legs with a bid, gross 0.70 / net 0.70 pts, 496 shares, $499.89, profit $3.47; legs: Chiang Wan-an bid 0.670x912 (age 28.17s); Puma Shen bid 0.337x496 (age 0.00s)
- family 848341 start 08:24:06.042232Z dur 159.493 s, B: sell YES on legs with a bid, gross 0.70 / net 0.70 pts, 436 shares, $439.47, profit $3.05; legs: Chiang Wan-an bid 0.670x950 (age 12.47s); Puma Shen bid 0.337x436 (age 0.00s)
## The largest episodes, and what to check before believing them

The largest after-fee episode: Musk Oct 8-10 count family (6 of 8 brackets recorded), 14:53:22.401Z, 0.09 s. Bid 0.926 x 970 on 90-114 (age 0.18 s) plus bid 0.105 x 73 on 115-139 sums to 1.031. The raw rows show the 115-139 book going bid 0.105 / ask 0.102 (crossed) at 22.4016 then ask 0.106 at 22.4016, and 90-114 bid stepping 0.926 -> 0.923 at 22.4677. This is one leg updating a fraction of a second before the other in a fast-moving count market, not a standing mispricing: at our timestamp resolution it is the same moment seen twice. The other 40 fee-clearing fresh episodes are 12 more on the same Musk Oct 8-10 family (mostly sub-second, up to 2.17 points on 5 shares) and 28 on "reach $X" / "above $X" ladders (19 Ethereum, 7 Bitcoin, 2 Bitcoin-above; 0.05-0.4 points, on prices of 0.2-0.4 cents, i.e. 1-4 ticks of 0.001). The largest peak profit among all 41 is $1.67 (the flicker), then $0.87; the rest are $0.13 or less.

What I would want verified before believing any of them: (1) exchange timestamps from the trades/depth stream (recorder2 data on the other machine), because our `recv_ns` can reorder two legs by a few hundred ms; (2) that the displayed size on each leg was available at that price and not already being taken (the recorded top of book carries one level only); (3) that sub-second flickers are not the same leg being counted before and after its own update; (4) fees and the real fee rate per market on the day (rate 0.05 on the Musk tweets family from Gamma `feeSchedule`, 0.04 where absent); (5) for the c=0 episodes in the Musk Oct 6-13 family, whether the binding leg (5-6 shares on the tail brackets) is a real resting order or a dust quote.

## Limitations

- Only the YES token is recorded. Buying NO, or NO-side conversion arbitrage on negRisk events, cannot be checked; selling YES on a set is evaluated at the YES best bid, which is what a seller of YES would hit.
- Timestamps are when our machine received the message, not when the exchange changed the book. Mac clock was +0.06 to +0.08 s at last check (DECISIONS); legs can be reordered by network jitter, so sub-second episodes (and many of the ones under 2 s) may be artefacts of arrival order.
- 12 hours of calendar time, 8 hours observed, with a 4.3 hour hole (laptop sleep 14:58-19:17 UTC) on a Saturday. Weekend, thin US hours; nothing about a macro release.
- One complete exclusive family and no complete ladder; 30 of 31 exclusive families and all 29 ladders are partial because the other outcomes are outside the recorded top-200 by volume. The family list comes from the Gamma event as fetched two days later; a market added to an event after 2026-10-10 would appear as an unrecorded member.
- Top of book only: size is one level. Depth beyond the best quote, queue position, and the NegRisk conversion mechanism are not modelled. Dollars = shares x set price (A or B), not capital after collateral rules.
- Stale quotes (>60 s since the last update) are reported separately and never counted. Polymarket quotes stand until changed, so a "stale" violation may be a real standing one; that is why it is reported, not dropped. After a reconnect a market not yet re-sent is treated as unknown, so no violation is ever joined across a connection change; a 60 s gap in recording cuts a window.
- Being first to a mispriced set against other bots is not something a recording can establish. A violation that lasts 60 s in our data may have been taken a second later by someone faster; a missing violation may have been taken before our message arrived.

## Rerun on another data folder

    python sets_check.py --tob <folder with {market_id}/date=*.parquet> --raw <events json> --out <outdir> [--fetch]

`--fetch` downloads the Gamma event of every market under `--tob` into `--raw` first (3 requests/s); without it `--raw` must already exist. Output: `<outdir>/episodes.json` and `<outdir>/tables.md`.
