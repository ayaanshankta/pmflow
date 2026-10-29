# Round 2: the rest of *Thinking, Fast and Slow* (test run once, 2026-10-29; rules research/behavioral-rules.md, round 2)

Market-level tests on the weekly snapshot table: DEV 2023–24 (shown first) and TEST 2025-01..2026-03, price-bin-adjusted
premium = price − outcome. Wallet tests B14–B17 are still running (behav_wallets.py), with results to follow.

| # | Book idea | Test | TEST result | Verdict |
|---|---|---|---|---|
| B10 | Planning fallacy (ch. 23) | "Will X launch/pass/sign by…" vs other deadline markets | diff +0.018 [−0.015, +0.046]; S10 buy NO +3.2% [−5.6, +12.0], n = 231 | **No** (right sign, not significant, too few trades) |
| B11 | Wishful thinking, crypto upside (ch. 9, 24) | "BTC above X" vs "below X" | TEST diff +0.083 [+0.052, +0.115], S11 +9.4% — **but TEST was contaminated.** Confirmatory: DEV diff +0.017 [−0.127, +0.145]; Apr-2026 diff **−0.084** [−0.131, −0.020], S11 **−31%** | **No.** It is crypto's direction in the period, not a bias |
| B12 | Hope that doesn't fade (ch. 29) | Longshots 2–10¢ by days to close | premium ≤2 d +2.0, 2–7 d +0.8, 7–30 d 0.0, >30 d +2.1 pts; S12 buy NO ≤7 d +0.35% [+0.02, +0.67] at 1¢, −0.7% at 2¢ | **Technically passes, worthless**: dies at 2¢; the Monday-VWAP row is unreliable for short-dated markets |
| B13 | Round-number anchoring (ch. 11) | Exact prices at 10/20/25/…/90¢ vs 1–2¢ away | round prices are 24% more common than neighbours (ratio 0.31 vs 0.25 expected); premium diff +0.008 [−0.005, +0.021] | **Traders anchor, prices don't suffer** |
| B18 | Recency / law of small numbers, ANY recurring series (Ayaan's generalisation) | 4,252 consecutive pairs in 1,183 series (tweet counts, temperatures, crypto ranges, charts, CPI…) | slope of next premium on last surprise −0.017 [−0.061, +0.026]; after an unexpected Yes −0.001 [−0.052, +0.049]; S18 fails both ways (after an unexpected No, buying YES loses −26%) | **No overreaction** to the last result |

## What this round adds
- **Correlated outcomes are the main trap in this kind of study.** Thousands of crypto or equity price markets are
  really one bet on direction. Clustering by market (even by event) makes that look like a robust bias, and it reverses
  the next month. B11 shows it directly. It also removed most of the binary fade-Yes survivor from round 1 (correction
  appended to behavioral-b2-s1-result.md). Any future claim needs clustering by week (common shocks) as standard.
- **Human signatures are visible in behaviour, not in prices.** People trade at round numbers more often (B13), but
  prices at round numbers are not worse forecasts. The "one bad result" idea (B6, B7, B18) fails everywhere it can be
  tested: Polymarket does not over-update on the last outcome.
- What remains of the book that holds up on Polymarket: a small, broad Yes premium (B2), overpriced multi-outcome fields
  (S1 check), and weak m/m CPI anchoring (B3).
