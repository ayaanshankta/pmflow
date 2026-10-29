# B3 result: anchoring in CPI markets (2026-10-29; rules research/behavioral-rules.md B3 + addendum; code behav_cpi.py)

**Verdict.**
- **Month-on-month CPI: weak evidence for anchoring.** When the market's expectation is near the previous print, the
  actual print tends to land further from the previous print than the market expected.
- **Year-on-year: inconclusive.**
- n is 13–15 usable releases (m/m) and 8 (y/y), so this is a hint, not a finding.
- The market still forecasts far better than "no change" (mean absolute error 0.05 vs 0.13 pp, m/m).

Data:
- 49 release-ladders (m/m 30, y/y 19), releases 2022-12-13 .. 2026-04-10.
- Usable: complete ladders (probabilities sum to 0.8–1.25) with a single resolved bracket.

## 1. Pre-registered fit — and why it cannot be read as stated
(implied − actual) = w · (prior − actual), through the origin. Bootstrap by release.

| | n | w |
|---|---|---|
| m/m, 24 h before | 13 | 0.27 [0.12, 0.47] |
| m/m, 1 h before | 15 | 0.34 [0.17, 0.50] |
| y/y, 24 h before | 8 | 0.27 [−0.22, 0.79] |
| y/y, 1 h before | 8 | 0.24 [−0.24, 0.68] |

**Flaw (found after running it, before interpreting it):**
- `actual` is on both sides of this regression.
- Any noisy forecast that doesn't simply equal the outcome gives w > 0 mechanically. A perfectly rational forecast
  plus surprise noise does.
- So w > 0 here is NOT evidence of anchoring, and it can't be compared with Hugo's ~9%.
- The pre-registered test was mis-specified. It is reported unchanged, as the rules require.

## 2. Corrected efficiency test (POST-HOC, labelled as such)
(actual − implied) = a + b · (prior − implied).
- Under an efficient forecast, the error is unpredictable from information known beforehand, so b = 0.
- Anchoring (implied pulled toward prior) ⇒ b < 0.

| | n | b |
|---|---|---|
| m/m, 24 h before | 13 | **−0.24 [−0.64, −0.08]** |
| m/m, 1 h before | 15 | **−0.33 [−0.75, −0.12]** |
| y/y, 24 h before | 8 | −0.45 [−1.24, +0.15] |
| y/y, 1 h before | 8 | −0.38 [−1.05, +0.24] |

- **m/m:** b < 0 with the CI excluding 0 at both horizons, an anchoring signature. Read loosely: the market sits ~25–30% too close
  to the prior print.
- **y/y:** the same sign, but the CI includes 0.
- **Correction:** earlier today I reported y/y as +0.20 [+0.02, +0.54], "the opposite". I could not reproduce that
  figure from cpi_releases.parquet with this specification. The table above is the reproducible one, and the earlier
  y/y claim is withdrawn.

## Caveats
- **Tiny n.** One or two releases can move b a lot, and the bootstrap CI at n = 13 is itself unreliable.
- **Post-hoc specification.** It was chosen after the pre-registered one proved flawed. The test is standard
  (forecast-efficiency regression) and was not picked from several variants, but it was not pre-registered.
- **Implied mean depends on ladder construction:** bracket mid-points, tail brackets at their boundary.
- **Not a strategy.** About one release a month, and the ladders are a few thousand dollars deep.

## For Hugo
- His anchoring intuition shows up in m/m CPI, in the direction he expected.
- It looks larger than his ~9%. The data can't pin the size down, and the naive way to estimate it (our pre-registered fit) is
  biased upward by construction.
- The clean way to settle it is more releases. Kalshi CPI ladders would roughly triple n.
