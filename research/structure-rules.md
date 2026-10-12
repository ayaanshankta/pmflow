# Pre-registered rules — cross-market structure (2026-10-12 02:20 CDT, before either analysis is run)

Motivation: Results 1-5 tested "news -> price" and found liquid markets absorb it in seconds. Result 2 (thin related markets move late or never) and the Result 4 verification (one post moved four sibling markets by very different amounts) suggest a different question: do related markets on the SAME event stay consistent with each other, and if not, for how long and in what size?

Definitions. A FAMILY is a set of Polymarket markets under one event. Two kinds:
- exclusive: outcomes that cannot both happen and of which exactly one must (Polymarket "negRisk" events; e.g. the rate decision at one FOMC meeting). Fair YES prices sum to 1.
- ladder: the same proposition with nested deadlines or thresholds (e.g. "X by April 7" / "X by April 30"; "BTC above 80k" / "above 82k" on the same date). Fair prices are monotone.
Family membership comes from the Gamma API event object (event id, negRisk flag, market list), fetched and saved before any price is examined. Ladders are identified by a committed rule on slugs/end dates within one event; ambiguous cases are dropped and counted.

## C1. Live quotes: are complete sets ever mispriced? (data/tob on the Mac, 2026-10-10 08:06-20:25 UTC; desktop data from branch/backup if obtainable)
- Only families where EVERY outcome is in the recorded universe count as complete; report how many are complete vs partial.
- At each quote change, for a complete exclusive family: A = sum of best YES asks, B = sum of best YES bids, with the available size = min size across the legs. Violation if A < 1 − c or B > 1 + c, where c = total taker fee for the legs at the venue formula rate × p × (1 − p) (rate from the universe file where present, else 0.04) — report also at c = 0.
- For ladders: violation if the ask of the weaker claim (earlier deadline / higher threshold) is below the bid of the stronger claim minus fees, i.e. you can buy the superset cheaper than you can sell the subset.
- Report per family: share of time in violation, number of episodes, duration distribution (median, p90), gap size in points, available size in shares and dollars, and whether a quote on any leg was older than 60 s at the time (stale-quote artefact; reported separately, not counted as a violation). Timestamps are the recorder's receipt times; state the clock caveat.
- Bar for "worth pursuing": at least 20 fee-clearing episodes lasting ≥ 2 s with ≥ $100 available, across ≥ 3 families. Otherwise report "complete sets are priced consistently at the resolution we record".

## C2. Trade archive: do siblings lag the leader? (Polymarket-v1 daily layers; fills only)
- Period: build and inspect on 2025-01-01..2025-06-30 (development); freeze rules; evaluate ONCE on 2025-07-01..2025-12-31 (test). 2026 shards are large and are not used.
- Leader = the family member with the most fills in the prior 24 h. Leader jump = last-trade price changes by ≥ 3 points within 60 s, with no jump in the previous 30 min (the first jump of an episode). t0 = time of the trade completing the jump.
- For each sibling with ≥ 20 fills in the prior 24 h: implied direction is opposite to the leader for exclusive families and the same for ladders. Measure the sibling's last-trade price change from before t0 to 1, 5 and 15 min after, signed by the implied direction; and a paper trade entering at the first sibling trade at or after t0 + Δ (Δ = 5, 30, 120 s), exiting at the last trade in [t0+12m, t0+18m], at 0 fee and at the venue fee.
- Placebo: the same sibling at 20 random times on the same day at least 2 h from any leader jump in its family, same sign convention. Event-cluster bootstrap (cluster = leader jump), 1,000 resamples, seed 0.
- Also report how much of the sibling's eventual 15-min move has already happened by its first trade after t0 (a "catch-up share"), and the dollar volume traded on the sibling within 2c of the entry price in the following 10 s.
- Bar for "siblings lag in a tradeable way" on the TEST period: paper trade at Δ = 30 s, venue fee, mean > 0 with 95 % interval excluding 0 on ≥ 100 jumps, AND median available volume ≥ $200. Report failure plainly; report every Δ and both family kinds whether or not they pass.

Honesty: rules committed before running (cite this file's blob hash in results). Development-period looks are allowed only for fixing bugs and the ladder-identification rule; any change after seeing development results is listed in the result file. No variant is dropped.
