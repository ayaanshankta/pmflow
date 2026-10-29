# Behavioral round 2: wallet tests B14-B17, plus B19 and B20 (2026-10-29)

Rules: research/behavioral-rules.md (round 2 wallet tests, B19, B20). Code: behav_wallets.py, behav_wallet_analyze.py,
behav_b19.py, behav_b20.py. Log: data/behav/wallet_analyze.log. Fees ignored; PnL is hold-to-resolution.

## Verdicts
| Test | Book idea | Result | Verdict |
|---|---|---|---|
| B15 | Illusion of skill | Spearman 2024 vs 2025 return +0.058 [+0.044, +0.071], 25,280 wallets. 2024 top decile: 2025 mean −6.3% vs −3.0% for all; 38.8% above the 2025 median | Book holds: no useful persistence; past winners are worse than average |
| B16 | Overtrading | Most active decile −1.3% vs least active −2.3%; top − bottom +1.0 pt [+0.55, +1.51]. Top 1% by $ (69% of $): pooled +0.6% | Prediction fails: activity does not hurt; liquidity providers win |
| B14 | Disposition effect | Pooled PGR 0.395 vs PLR 0.347, +0.051 [+0.009, +0.101]; per-wallet mean −0.066 [−0.071, −0.061] | Present in $-heavy wallets, reversed in the typical small wallet. No price effect tested |
| B17 | Break-even effect | Pre-registered paired diff +0.040 [+0.035, +0.045] (wrong sign) is mechanical (before-window holds the resolving longshot). Post-hoc without that market: −0.004 [−0.009, +0.001] | No effect |
| B19 | Aggregate caution after loss weeks | Favourite premium diff TEST −0.017 [−0.037, +0.003]; S19 −22% at MonVWAP | Fails |
| B20 | Multi-outcome overround, No basket | Passes as written: +3.9% [+2.2, +7.0], n = 3,197 at MonVWAP. Verifier: the tail uses non-simultaneous, partly post-result VWAPs. Cleanest cut +0.38% [+0.27, +0.50], n = 790 | Plausible small edge (~0.4–1% per basket); needs simultaneous quotes (B20-forward) |

## Notes
- Wallet returns are zero-sum before fees: retail wallets lose about 1–2% on average to the top 1% by volume.
- B15 is not a copy-trading test, but the obvious copy rule (follow last year's best) would have done worse than average.
- B20-forward: the desktop recorder was down 2026-10-16 08:26 UTC to its restart (PC crash), so only ~66 h of
  whole-family quotes exist (2026-10-13 14:16 to 10-16 08:26). Results to be appended.

## Verification (Sonnet verifier, own code, 2026-10-29)
- B15 and B16 headline numbers reproduce (to within 0.05 pp; small drift from address case-merging).
- PnL formula and p_event mapping correct; no fills double-counted across the two archive layers (27 local days).
  About 2.3% of rows within a layer are exact duplicates (no tx hash to tell repeats from copies); zero-sum, so noise.
- B15 caveat: the top decile's underperformance is much smaller $-weighted (−1.1% vs +0.4% for all, diff −1.55 pp
  [−3.37, −0.09]) than in equal-weighted means (−6.3% vs −3.0%). Direction holds in every size quintile.
- B14 caveats: a sale at exactly average cost counts as a loss (inflates PLR, conservative for the prediction);
  realized events are per fill but paper events per position-day, so bot wallets dominate the pooled numbers.
  Report B14 as mixed, not as a disposition effect.
