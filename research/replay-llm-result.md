# Latency replay, LLM-direction arm (addendum B2)

> **Verifier findings (2026-10-12, independent fill/exit/PnL/bootstrap code; headline numbers reproduce: n=226 over 122 posts, gross +1.70, venue-fee +1.20, event minus placebo +1.67 [+0.36, +3.61]).**
> 1. **One post supplies about half of it.** The Maduro post of 2026-01-03 is 190 of 385 total points (49 %), across four related markets; three posts together are 74 %. Without that one post: diff **+0.84 [+0.24, +1.52]** (n=222). Without all three: +0.44 [+0.07, +0.84]. Dropping the top 5 trades: +0.74 [+0.21, +1.36].
> 2. **226 trades are 122 independent bets at most.** 77 % of trades share a post with another market. One averaged trade per post: +0.96 [+0.23, +2.04]; median per-post difference +0.11; 59 % positive.
> 3. The "larger edge before February" is that one event: without it the early half is +0.70, so the before/after split says nothing about memorisation either way.
> 4. Placebo is fair on mechanics and price level (mean entry 0.404 vs 0.421; reweighting changes the difference by 0.007). One asymmetry by construction: 19.5 % of event windows contain another matched post, 0 % of placebo; excluding those trades leaves +1.64 [+0.14, +3.98].
> 5. **Size.** Where checked, the Maduro markets had $1k-$11k traded within 2c of entry in ~5 s, so $500 is plausible there. Three of the Iran winners had $553, $23 and $10 within 2c: those gains would not have been available at size. Five of the top ten were not size-checked.
> 6. So: a small positive gross difference (roughly +0.4 to +1.0 points) survives removing the outliers and collapsing to one bet per post, against a venue fee of the same order. Not an after-cost edge; memorisation is tested separately (B3).


Rules: `research/ml-rules.md` section B + addendum B2 + "B2 addition". Prompt: `research/replay-llm-prompt.md` (commit 1f2610f, made before the first model call). Code: `replay_llm.py` (+ `test_replay_llm.py`); engine is `replay_truth.py` unchanged. Same 400 events / 1,993 pairs / placebo generator / bootstrap (1,000 event-cluster draws, RandomState(0)) as Result 3. Full tables: `results/replay_llm_table.md`; raw model answers: `results/replay_llm_dirs.jsonl`; summary `results/replay_llm_summary.json`.

## Verdict
**FAIL on the written bar.** Bar: mean PnL > 0, 95% CI excluding 0, on >= 100 trades, at flat 1% and at the realistic (taker) fee.
- Flat 1%: fails at all 6 (entry x delta) combinations. Best is first-trade entry, delta 2 s: +0.83 pts [-0.62, +2.81], n=214.
- Realistic fee, primary entry (first trade at/after t0+delta): fails at all three deltas: +1.39 [-0.04, +3.39] (2 s), +1.20 [-0.06, +3.07] (10 s), +0.93 [-0.19, +2.31] (30 s). Close at 2 s, but the CI includes 0.
- Realistic fee, "next trade" entry: the CI excludes 0 at 2 s (+1.88 [+0.12, +4.35], n=168) and 10 s (+1.73 [+0.08, +4.01], n=175); not at 30 s. These are 2 of 12 flat/realistic x delta cells in the secondary entry variant, lower bounds are barely above 0, and the 2 s one is not achievable. I do not count this as a pass; it is a lead to check, not a result.

What is real in the data: **gross of fees, the model's direction has an edge over placebo.** Event minus placebo at 0% fee is +1.9 pts [+0.40, +3.77] (2 s), +1.7 [+0.35, +3.49] (10 s), +1.4 [+0.32, +2.82] (30 s), first-trade entry; same sign and similar size for next-trade entry. Placebo trades at the same direction are ~0 gross, so this is specific to the event times. The edge is of the same order as the fee, so after costs it is not reliably positive.

## Counts
| | |
|---|---|
| liquid event pairs sent to the model | 677 |
| up / down / none | 192 / 141 / 344 |
| parse failures, call errors, uncalled | 0 / 0 / 0 |
| spend | $0.171 of the $2 cap |
| mean latency per call | 2.9 s |
| trades (event, first-trade entry, 2/10/30 s) | 214 / 226 / 235 (122-126 events) |
| trades (event, next-trade entry) | 168 / 175 / 188 (101-112 events) |
| placebo trades (first-trade) | 2,940 / 2,952 / 2,896 |

Placebo rows: 12,452 liquid placebo pairs; 7,754 had no direction (their event's pair was not liquid, or the model said none). No-fill / no-exit counts per cell are in `results/replay_llm_summary.json`.

## Table: the two requested fee rows (all 72 event/placebo/diff cells x entry x delta x fee are in `results/replay_llm_table.md`)
Realistic fee = 0.04 x p x (1-p) of traded value on each side. (I checked this convention reproduces the verifier's -0.66 oracle number from Result 3; the per-share-dollar alternative gives -1.15 and was not used.)

| set | entry | delta s | fee | n | events | mean PnL pts (95% CI) |
|---|---|---|---|---|---|---|
| event | first | 2 | taker | 214 | 123 | +1.39 [-0.04, +3.39] |
| event | first | 10 | taker | 226 | 122 | +1.20 [-0.06, +3.07] |
| event | first | 30 | taker | 235 | 126 | +0.93 [-0.19, +2.31] |
| event | next | 2 | taker | 168 | 101 | +1.88 [+0.12, +4.35] |
| event | next | 10 | taker | 175 | 103 | +1.73 [+0.08, +4.01] |
| event | next | 30 | taker | 188 | 112 | +1.19 [-0.09, +2.81] |
| event | first | 2 | 1% | 214 | 123 | +0.83 [-0.62, +2.81] |
| event | first | 10 | 1% | 226 | 122 | +0.64 [-0.62, +2.53] |
| event | first | 30 | 1% | 235 | 126 | +0.35 [-0.79, +1.71] |
| event | next | 2 | 1% | 168 | 101 | +1.28 [-0.49, +3.74] |
| event | next | 10 | 1% | 175 | 103 | +1.14 [-0.52, +3.41] |
| event | next | 30 | 1% | 188 | 112 | +0.59 [-0.72, +2.15] |
| placebo | first | 2 | taker | 2940 | 142 | -0.49 [-0.57, -0.41] |
| placebo | first | 2 | 1% | 2940 | 142 | -0.96 [-1.08, -0.85] |

Event minus placebo (95% CI, event-cluster bootstrap), first-trade entry, 2 s: gross +1.88 [+0.40, +3.77]; flat 1% +1.79 [+0.34, +3.69]; taker +1.88 [+0.43, +3.79]. At 10 s: +1.67 [+0.35, +3.49] / +1.59 [+0.29, +3.41] / +1.67 [+0.37, +3.50]. At 30 s: +1.40 [+0.32, +2.82] / +1.31 [+0.25, +2.71] / +1.41 [+0.34, +2.80]. The difference is positive with CI above 0 in every cell, but note it is a difference against a placebo that loses the fee, not a profit.

## Before / after 2026-02-01 (by the post's date; first-trade entry, 10 s, taker fee)
| period | n trades | events | mean PnL pts (95% CI) | gross (0% fee) | event minus placebo, gross |
|---|---|---|---|---|---|
| before | 57 | 32 | +3.63 [-0.22, +9.81] | +3.99 [+0.13, +10.18] | +3.99 [-0.10, +10.54] |
| after | 169 | 90 | +0.38 [-0.34, +1.16] | +0.93 [+0.20, +1.71] | +0.89 [+0.20, +1.71] |

The gross edge is positive in both halves, larger and much noisier before February (n=57). After February it is +0.9 gross and below the fee. Neither half passes the bar at the taker fee. Full split tables for every cell are in `results/replay_llm_table.md`.

## Robustness notes (first-trade entry, 10 s, 0% fee, n=226)
- **The mean is carried by a few trades.** The median trade is ~0.0 pts; the top 5 trades are 55% of the total PnL; the mean excluding them is +0.78; the 5%-trimmed mean is +0.63. Hit rate at 0% fee is 53.5%, close to a coin flip.
- Long trades average +2.0, short +1.2 (58% long).
- 38% of entries are at p < 0.10 or p > 0.90, where a point is a large proportion of the price; the mean for entries in 0.10-0.90 is +2.6 (n=139).

## Limitations
1. **Memorisation cannot be excluded.** The posts run from October 2025 to April 2026 and the model may have seen these events (or the resolutions of these markets) in training; a positive gross edge could be recall of what happened and not reading of the post. The before/after-2026-02-01 split does not settle it: the edge is positive in both halves and shrinks after February, which is what leakage would predict if the model's knowledge fades near its cutoff, but is also what a small noisy sample would give, and I do not know the model's training cutoff. Because the answer is about the YES price over the next ~15 minutes, leakage would need the model to remember a price path, which is less likely than remembering an outcome, but I cannot rule it out.
2. **Trades only, no quotes.** Spread and price impact are not measured, and a $500 order is assumed filled at one trade price. Both would reduce the edge, and the edge here is already about the size of the fee.
3. **Timing.** Timestamps are on-chain settlement times, so a 2 s delay is inside settlement jitter and is not really achievable. The model took ~2.9 s per call, so 2 s is not achievable even with an instant fill; the 10 s and 30 s rows are the ones that could be traded. The "first trade at/after t0+delta" entry is partly selected on (the first print can be the move itself); the "next trade" entry is the verifier's control for that, and it gave the larger numbers here, not smaller.
4. **Small, clustered sample.** About 120 events and 214-235 trades; the CIs are wide, the mean is outlier-driven (see above), and four fee models x three deltas x two entries x two splits is many cells. Only the written bar (flat 1% and realistic fee, n >= 100) was used for the verdict.
5. **Model answers are one sample each.** One call per pair, no repeat to measure run-to-run consistency; 3 of 677 calls were served by `claude-haiku-4-5-20251001` and the rest by `claude-haiku-5-5` (per the CLI's modelUsage), so the "model" is a mix.
6. **Placebo times** hold the event's own direction fixed, so event minus placebo isolates timing (is this a good moment to trade this direction), not "does the model's direction beat random".
7. Taker-fee convention: rate x p x (1-p) x traded value per side, p taken at the actual entry and exit trade. The other reading (fee per share in dollars) is about 2x larger at mid prices and gives -1.15 on the oracle check versus the verifier's -0.66; I used the one that reproduces the verifier. The "next trade" entry gave 320 oracle trades at delta 2 s against the verifier's 323 (mean -0.007 vs +0.001 pts).

## What I would check next before believing a positive
(a) Out-of-sample: run the same fixed prompt on posts after the model's cutoff (the collector is still recording), so memorisation is excluded by construction. (b) Re-run with the model asked about a market it cannot have seen resolved (open markets at the time of the call). (c) Check spread/impact on the tob data (`data/tob`) for the trades that make up the mean: a handful of large winners pay for everything. (d) Repeat the model call 3x per pair to see how stable the direction is.
