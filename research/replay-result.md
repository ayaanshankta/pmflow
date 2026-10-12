# Latency replay on fills only (Truth Social, Result-2 pairs)

> **Verifier corrections (2026-10-12, independent re-derivation; numbers reproduce, interpretation changed).**
> 1. The finding is: **no detectable gross edge** from entering 2-30 s after matched posts; event ≈ placebo. The 1 %-fee losses mostly restate the fee.
> 2. The "oracle" arm is **not an upper bound**. Its direction is the sign of the first post-t0 trade against the prior mean, and 92 % of Δ=2 s entries are that same trade, so it buys the print it was selected on. Entering on the next trade instead gives +0.001 pts [−0.73, +0.83] at 0 % fee (n=323). Read it as a momentum-with-bounce control.
> 3. The **lexicon arm is underpowered** (n=32 trades over 20 events; 91 % of liquid pairs had no direction) and supports no conclusion about news direction.
> 4. The flat 1 %/2 % fees overcharge. With the venue's documented taker fee, rate × p × (1−p) at rate 0.04: oracle Δ=2 s −0.66 pts [−1.21, −0.00]; next-trade variant −0.47 [−1.19, +0.36]; lexicon +0.02.
> 5. Limits: fills only (no spread or impact), $500 assumed filled at one price, on-chain timestamps (Δ=2 s is inside settlement jitter).

Rules: `research/ml-rules.md` section B (blob a6140e5, committed before running). Code: `replay_truth.py` (+ `test_replay_truth.py`, 8 tests). Raw trades: `results/replay_trades.csv` (regenerated, not committed); summary `results/replay_summary.json`. Same 400 events / 1,993 pairs / placebo generator and seeds as `backtest_truth.py` (Result 2). Bootstrap: 1,000 event-cluster resamples, RandomState(0), trade-weighted mean.

## Verdict (pre-registered bar: mean PnL at 1 % fee > 0, CI excluding 0, ≥ 100 trades)
**FAIL at every Δ (2, 10, 30 s).** Lexicon arm at 1 % fee: Δ=2: -0.68 pts, CI [-1.17, -0.12], n=32, Δ=10: -0.67 pts, CI [-1.15, -0.09], n=31, Δ=30: -0.66 pts, CI [-1.07, -0.19], n=37. Fails two ways: n = 31-37 (< 100) and the mean is negative with a CI entirely below 0. The oracle upper bound (direction of the first post-t0 trade, n≈420-440) is also negative at 1 % (-1.1 to -1.2 pts, CI below 0) and only ≈ 0 at 0 % fee (CI includes 0). Placebo times give the same picture, so there is no event-specific gross edge, and fees of 1 % per side alone exceed any gross move.

## Table (all variants run, none dropped)
| set | direction | Δ s | fee/side | n trades | events | hit rate | mean PnL pts (95% CI) | mean PnL $ (95% CI) |
|---|---|---|---|---|---|---|---|---|
| event | lexicon | 2 | 0% | 32 | 20 | 43.8% | +0.29 [-0.06, +0.76] | +8.22 [-2.97, +20.77] |
| event | lexicon | 2 | 1% | 32 | 20 | 25.0% | -0.68 [-1.17, -0.12] | -1.87 [-12.94, +10.56] |
| event | lexicon | 2 | 2% | 32 | 20 | 21.9% | -1.66 [-2.34, -0.97] | -11.95 [-22.91, +0.35] |
| event | lexicon | 10 | 0% | 31 | 20 | 41.9% | +0.27 [-0.08, +0.78] | +7.81 [-3.57, +20.37] |
| event | lexicon | 10 | 1% | 31 | 20 | 22.6% | -0.67 [-1.15, -0.09] | -2.27 [-13.53, +10.17] |
| event | lexicon | 10 | 2% | 31 | 20 | 19.4% | -1.61 [-2.34, -0.92] | -12.34 [-23.50, -0.03] |
| event | lexicon | 30 | 0% | 37 | 21 | 43.2% | +0.18 [-0.13, +0.65] | +3.34 [-13.92, +18.20] |
| event | lexicon | 30 | 1% | 37 | 21 | 24.3% | -0.66 [-1.07, -0.19] | -6.69 [-23.78, +8.01] |
| event | lexicon | 30 | 2% | 37 | 21 | 16.2% | -1.50 [-2.13, -0.90] | -16.73 [-33.64, -2.17] |
| event | oracle | 2 | 0% | 421 | 215 | 36.3% | -0.19 [-0.77, +0.50] | -12.02 [-22.85, +0.11] |
| event | oracle | 2 | 1% | 421 | 215 | 15.4% | -1.21 [-1.78, -0.55] | -21.90 [-32.62, -9.89] |
| event | oracle | 2 | 2% | 421 | 215 | 10.0% | -2.23 [-2.78, -1.60] | -31.78 [-42.39, -19.89] |
| event | oracle | 10 | 0% | 424 | 218 | 37.5% | -0.12 [-0.61, +0.43] | -9.10 [-19.60, +0.98] |
| event | oracle | 10 | 1% | 424 | 218 | 16.3% | -1.13 [-1.59, -0.58] | -19.00 [-29.41, -9.03] |
| event | oracle | 10 | 2% | 424 | 218 | 12.3% | -2.13 [-2.60, -1.58] | -28.91 [-39.21, -19.04] |
| event | oracle | 30 | 0% | 441 | 217 | 37.6% | -0.10 [-0.48, +0.29] | -9.04 [-17.88, -0.69] |
| event | oracle | 30 | 1% | 441 | 217 | 18.6% | -1.12 [-1.49, -0.73] | -18.95 [-27.70, -10.68] |
| event | oracle | 30 | 2% | 441 | 217 | 12.5% | -2.15 [-2.52, -1.76] | -28.86 [-37.52, -20.67] |
| placebo | lexicon | 2 | 0% | 670 | 41 | 43.7% | +0.09 [+0.02, +0.17] | +2.25 [-0.95, +5.79] |
| placebo | lexicon | 2 | 1% | 670 | 41 | 22.5% | -0.69 [-0.84, -0.55] | -7.77 [-10.94, -4.27] |
| placebo | lexicon | 2 | 2% | 670 | 41 | 15.8% | -1.47 [-1.74, -1.20] | -17.79 [-20.93, -14.33] |
| placebo | lexicon | 10 | 0% | 670 | 41 | 41.6% | +0.09 [+0.02, +0.17] | +2.18 [-1.22, +6.01] |
| placebo | lexicon | 10 | 1% | 670 | 41 | 21.8% | -0.68 [-0.83, -0.54] | -7.84 [-11.21, -4.05] |
| placebo | lexicon | 10 | 2% | 670 | 41 | 15.8% | -1.46 [-1.74, -1.19] | -17.86 [-21.20, -14.11] |
| placebo | lexicon | 30 | 0% | 639 | 40 | 38.8% | +0.07 [-0.00, +0.15] | +1.90 [-1.64, +5.77] |
| placebo | lexicon | 30 | 1% | 639 | 40 | 22.2% | -0.70 [-0.86, -0.57] | -8.11 [-11.62, -4.29] |
| placebo | lexicon | 30 | 2% | 639 | 40 | 15.8% | -1.48 [-1.76, -1.21] | -18.13 [-21.61, -14.35] |
| placebo | oracle | 2 | 0% | 7274 | 298 | 31.5% | -0.23 [-0.28, -0.18] | -7.01 [-8.33, -5.65] |
| placebo | oracle | 2 | 1% | 7274 | 298 | 11.7% | -1.24 [-1.29, -1.19] | -16.94 [-18.24, -15.60] |
| placebo | oracle | 2 | 2% | 7274 | 298 | 8.0% | -2.25 [-2.31, -2.19] | -26.87 [-28.16, -25.54] |
| placebo | oracle | 10 | 0% | 7238 | 298 | 34.2% | -0.18 [-0.24, -0.14] | -5.05 [-6.32, -3.78] |
| placebo | oracle | 10 | 1% | 7238 | 298 | 12.8% | -1.20 [-1.25, -1.14] | -15.00 [-16.26, -13.74] |
| placebo | oracle | 10 | 2% | 7238 | 298 | 8.6% | -2.21 [-2.27, -2.15] | -24.95 [-26.20, -23.70] |
| placebo | oracle | 30 | 0% | 7189 | 298 | 37.3% | -0.12 [-0.17, -0.07] | -2.15 [-3.58, -0.62] |
| placebo | oracle | 30 | 1% | 7189 | 298 | 15.2% | -1.13 [-1.18, -1.08] | -12.13 [-13.54, -10.62] |
| placebo | oracle | 30 | 2% | 7189 | 298 | 10.3% | -2.15 [-2.21, -2.09] | -22.11 [-23.51, -20.61] |

## Counts
| set | pairs | illiquid (<50 fills prior hour) | liquid | lexicon: no direction | oracle: no direction |
|---|---|---|---|---|---|
| event | 1993 | 1316 | 677 | 619 | 29 |
| placebo | 39639 | 27187 | 12452 | 11356 | 498 |

| set | direction | Δ s | no fill (no trade ≤60 s) | no exit in [12m,18m] (dropped) | traded |
|---|---|---|---|---|---|
| event | lexicon | 2 | 25 | 1 | 32 |
| event | lexicon | 10 | 26 | 1 | 31 |
| event | lexicon | 30 | 20 | 1 | 37 |
| event | oracle | 2 | 218 | 9 | 421 |
| event | oracle | 10 | 216 | 8 | 424 |
| event | oracle | 30 | 198 | 9 | 441 |
| placebo | lexicon | 2 | 410 | 16 | 670 |
| placebo | lexicon | 10 | 411 | 15 | 670 |
| placebo | lexicon | 30 | 445 | 12 | 639 |
| placebo | oracle | 2 | 4510 | 170 | 7274 |
| placebo | oracle | 10 | 4550 | 166 | 7238 |
| placebo | oracle | 30 | 4588 | 177 | 7189 |

## Notes / unverified
- **Lexicon direction.** `backtest_truth.py`'s lexicon is topic-only (no up/down). The only committed text→direction rule is the LABELS.md keyword baseline (`map.keyword_dir`); I applied it to the post text with the market slug (hyphens → spaces) as the question. It returns `none` for people/Ukraine/midterms themes and for unmatched sentiment words, so 619 of 677 liquid event pairs (91 %) had no direction and are skipped; the lexicon arm has only 20-21 events. Lexicon is therefore a weak test; the oracle arm carries the statistical power. Lexicon direction at placebo times = the event's own direction, held fixed.
- Oracle = sign(first trade ≥ t0 − mean of last 5 trades before t0): deliberate look-ahead (may be earlier than the Δ entry), an upper bound, equal prices → no direction.
- Fills only: no quotes, so no spread/impact; short = buying the complement at 1 − p (assumed available at the mirror price). $500 is assumed fully filled at one trade price. Timestamps are on-chain settlement, so Δ = 2 s is within settlement jitter (sub-5 s unsupported, as in Result 2).
- Liquidity filter (≥ 50 trades in [t0-1h, t0)) is applied at the placebo time for placebo rows (12,452 of 39,639 liquid).
- Fee = rate × traded value per side (entry $500; exit shares × exit value). Hit = net $ PnL > 0 at that fee.
- Pass bar read as: lexicon arm, event set, per Δ; no overall pooled test was pre-registered.
