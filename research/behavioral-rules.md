# Pre-registered rules — behavioral biases (2026-10-29, before any resolved-market statistic has been computed)

Motivation: Results 1-7 tested speed (news → price) and cross-market consistency; liquid markets absorb information in
seconds. A different kind of edge would be a *persistent mispricing* from how people judge probabilities. Hugo Stack
(prediction-market reference-index startup, YC) suggested mapping the biases in Kahneman's *Thinking, Fast and Slow* onto
prediction markets, citing (a) a "Yes" premium in low-volume binary markets and (b) CPI consensus skewing ~9 % toward the
prior print. If biases persist, it suggests little sophisticated capital; if they are small, the opposite.

Known work (not re-derived here): a favorite–longshot bias on Polymarket whose sign depends on weighting
(arXiv 2609.12878) and horizon (arXiv 2610.13593); near-calibration in an independent 2,946-market check (CH4RL3I/honest-odds);
a strong longshot bias on Kalshi, worst for takers (Bürgi, Deng & Whelan 2025). Liquidity-stratified "Yes" premium and CPI
anchoring were not found tested.

## Data and periods
- Polymarket-v1 archive (HF `TimeSeventeen/Polymarket-v1`, fills only), layers `daily_aligned` (binary) and
  `daily_aligned_multi` (neg-risk children), 2022-11-21 .. 2026-04-28. Streamed one day at a time and reduced; raw days are deleted.
- **Development:** snapshots dated 2023-01-02 .. 2024-12-30. **Test:** snapshots 2025-01-06 .. 2026-03-30 (the last month
  is left out so most markets have resolved). The test period is evaluated ONCE, after the strategy below is frozen.

## Unit of observation: weekly snapshots (no outcome-dependent sampling)
- Snapshot times T = every Monday 00:00 UTC.
- A market enters snapshot T if: it had ≥ 1 fill in [T − 7 d, T); its `resolved_at` > T (still open, which is knowable at T);
  and it eventually resolved (`resolution_status == resolved`). Markets that never resolved are counted and excluded.
- Price at T: `p` = VWAP of `p_event` over fills in [T − 24 h, T); if none, the last fill's `p_event` before T (flagged).
  `p_event` is on the outcome_seq = 1 axis ("Yes" for Yes/No markets).
- Volume-to-date `V` = sum of `usdc_amount` before T (never total lifetime volume, which would leak the future).
- Outcome `Y` = 1 if `winning_outcome_label` equals the outcome_seq = 1 label, else 0.
- Also stored per snapshot: days to `close_at`, category, layer (binary / multi), slug, fills and $ in the 24 h before T,
  and `p` 24 h earlier (for B6).
- **Excluded strata, reported separately:** recurring crypto "Up or Down" markets (tag or slug pattern; they are coin flips
  resolving within hours) and markets whose seq-1 label is not "Yes" (sports teams, Over/Under) for the Yes-premium tests.
- Clustering for every interval: by market (`condition_id`); also reported clustered by event (slug prefix / neg-risk id).
  Bootstrap 2,000 resamples, seed 0.

## Tests (all on the same snapshot table)
- **B1 Possibility / certainty effects (ch. 29–30), descriptive.** Calibration: win rate vs `p` in bins
  0–2, 2–5, 5–10, 10–20, …, 80–90, 90–95, 95–98, 98–100; logit slope of Y on logit(p). Equal weight per snapshot,
  then per market (one snapshot drawn per market). By layer, by horizon (≤ 1 d, 1–7 d, 7–30 d, > 30 d to close), by category.
- **B2 "Yes" premium in thin markets (Hugo; affect / framing). PRIMARY.** Yes/No markets only. Premium = `p` − Y.
  Volume terciles of `V` with cut points fixed on development snapshots. Report premium by tercile, and by
  (price bin × tercile) so a thin-market effect is not just "thin markets hold more long shots".
  Claim "Yes is overpriced in thin markets" requires, on TEST: price-bin-adjusted premium in the lowest tercile > 0 with
  95 % CI excluding 0, and larger than in the highest tercile (difference CI excluding 0).
- **B3 Anchoring in CPI (ch. 11; Hugo's ~9 %).** CPI ladder markets (headline CPI m/m and y/y brackets, identified by a
  slug rule committed with the code before prices are read). For each release: implied mean from the ladder at the last
  snapshot ≥ 24 h before release (and at release − 1 h, from fills), actual = the resolved bracket, prior = previous
  release's actual. Fit (implied − actual) = w · (prior − actual) through the origin; report w with CI (cluster = release).
  Anchoring ⇒ w > 0; Hugo's claim ≈ w ≈ 0.09. All releases 2022-11..2026-04 (no dev/test split: too few releases).
  Expect n ≈ 30–40; stated as low power.
- **B4 Base-rate neglect in deadline markets (ch. 14–16), secondary.** Yes/No markets whose slug contains `-by-` or
  `-before-` vs others: premium difference, price-bin-adjusted.
- **B5 Overreaction after vivid moves (availability, ch. 12–13), secondary/exploratory.** Snapshots where |p − p_24h| ≥
  0.10: premium signed by the move's direction (positive = the move overshot).

## The strategy (paper), chosen on DEVELOPMENT only, evaluated ONCE on TEST
S1 "Fade Yes in thin markets": at each snapshot, in a Yes/No market in the lowest `V` tercile with `p` in [lo, hi], buy NO at
(1 − p) + slippage, hold to resolution. One entry per market (first qualifying snapshot). Return per $1 staked
= (1 − Y)/(entry price) − 1 − fee, fee = market's `taker_base_fee` formula where non-zero. Slippage 1¢ (primary) and 2¢.
- Grid, fixed now: [lo, hi] ∈ {[0.05,0.20], [0.10,0.40], [0.20,0.50], [0.05,0.50]}. Pick the cell with the best development
  mean return whose 95 % CI excludes 0; if none does, S1 is reported as "no strategy" and the test period still reports all cells.
- **Pass bar on TEST:** mean return > 0 at 1¢ slippage with 95 % CI excluding 0 (cluster = market), ≥ 300 trades, and
  report capacity: median $ traded on the market in the 24 h before entry (a thin market cannot absorb much size).
  Every grid cell and both slippages are reported on test, pass or fail.
- Comparison rows on test: the same rule on all volume terciles, and a "buy YES" mirror (should lose if B2 holds).

## Honesty
Rules committed before the pipeline is run (cite this file's blob hash in the result file). Development looks are allowed
for bug fixes and the CPI slug rule; any change after development results is listed with its reason. No variant is dropped.
Paper only: the venue is closed to US persons.

## B3 addendum: CPI slug rule and method (2026-10-29, written before any CPI price was computed; dev look was slug names only)
- Releases: the 41 BLS CPI releases 2022-11-10..2026-04-10 (bls.gov archived release links), 08:30 ET. Reference month =
  previous month, except 2025-10-24 → September 2025 and 2025-12-18 → November 2025 (shutdown).
- Ladders (see `behav_cpi.py` `rules()`): y/y brackets `will-annual-inflation-increase-by-X[-or-more|less]-in-<month>`;
  m/m brackets `will-monthly-inflation-increase-by-X…-in-<month>` and `us-inflation-X…-from-<prev>-to-<month>-<year>`;
  m/m thresholds `will-us-inflation-be-greater-than-X-from-<prev>-to-<month>-<year>`. Numeric suffixes allowed; markets must
  trade in the 48 h before t0. Duplicate brackets: keep the one with a price at t0 − 24 h.
- Price at τ = last fill at or before τ within 48 h. Implied mean: normalised bracket probabilities (≥ 3 priced brackets;
  tails valued at their boundary); thresholds converted to bracket mass on a 0.1 grid after enforcing monotonicity.
  Releases with bracket price sums outside [0.8, 1.25] or ambiguous winners are reported but excluded from the fit.
- Actual = the resolved winner; prior = the previous release's actual for the same measure. The fit is unchanged from B3.
- **Slug-rule fix, 2026-10-29 (before any CPI implied value, fit or result was printed):** the first run's log of
  unmatched slug NAMES showed variants the rule missed: "more-than" thresholds, a year on the prior month, 3-letter and
  mixed-case months, integer values without "pt", and 2024 y/y forms (`annual-inflation-above-X`, `will-inflation-increase-by-X`,
  `will-us-annual-inflation-be-X`). The run was stopped and the rule widened; `annual-inflation-under-X` (one-sided, single
  market) stays out. Unit cases for each form are in the commit.
