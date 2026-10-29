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

## B6 Regression to the mean after a loss (ch. 17; "law of small numbers", ch. 10) — added 2026-10-29 before any sports price was computed
Suggested by Ayaan from the Hugo call: one bad game makes the market mark a team down for the next game, but a single
game is mostly noise, so the next game should be underpriced for the team that just lost.
- Markets: moneyline game markets with slug `{league}-{a}-{b}-{YYYY-MM-DD}` (no suffix) in leagues nba, wnba, nhl, mlb
  (two-way outcomes, teams that meet in consecutive games). Outcome labels are the two team names; winner from
  `winning_outcome_label`. Dev look so far: slug names only.
- Pre-game price: VWAP of each team's win probability over fills from 00:00 ET the day before the slug date to 11:00 ET on
  the slug date (before day-game starts); ≥ 1 fill required.
- Pairs: game n and n+1 between the same two teams in the same league, n+1 dated 1–4 days after n (a series).
  L = loser of game n. Premium_L = p_L(n+1) − Y_L(n+1). Upset = L was the pre-game favourite (p_L(n) > 0.5) in game n.
- Prediction: premium_L < 0 (L underpriced), more negative after upsets.
- Periods as before: development games dated ≤ 2024-12-31; TEST 2025-01-01 .. 2026-04-28, evaluated once.
- Strategy S6: buy L before game n+1 at p_L + 1¢ (and 2¢), hold to the result. Variants fixed now: all L; upset-only L.
  Pass bar on TEST: mean return > 0 at 1¢ with 95 % CI excluding 0 (cluster = series), ≥ 300 games. Both variants reported.

## B7 Player props: does the market overreact to one game? (ch. 17 regression to the mean, ch. 10 law of small numbers / hot hand) — added 2026-10-29, before any prop price was computed
Ayaan's request: follow players (≥ the top 20 by volume, plus a pooled test on all) and ask whether, after a bad or a great
game, the market prices the next game as if the last one were the new normal.
- Markets: NBA player props `nba-{a}-{b}-{YYYY-MM-DD}-{points|rebounds|assists}-{player}-{X}pt{Y}`, binary layer;
  seq-1 = "Yes" = over the line. Season window 2025-10-15 .. 2026-04-28 (props appear in the archive by 2025-12).
  `close_at` = tip-off (checked on 2025-12-09 slugs); props trade in-play after it, so prices stop strictly at tip-off.
- Pre-game price: VWAP of P(over) over fills in [tip − 6 h, tip − 5 min); ≥ 1 fill. Outcome Y_over from the winner.
- Performance of game n (market-only; NBA's stats API refused requests, and per-game scraping is off-limits): for a
  player-stat in game n, sign_n = +1 if every line that game resolved over ("great"), −1 if every line resolved under ("bad"),
  0 otherwise. Main line of game n+1 = the line with the most pre-game $ (ties: closer to 0.5).
- Pairs: same player and stat, game n+1 dated 1–5 days after game n.
- Measures: (a) line change L(n+1) − L(n) by sign_n (how far the market re-sets after one game; descriptive);
  (b) premium = p_over(n+1) − Y_over(n+1), by sign_n. Overreaction ⇒ premium > 0 after great games (over too dear) and
  < 0 after bad games; primary statistic = premium(great) − premium(bad) > 0.
- Strategy S7 "fade the last game": after a bad game buy the over; after a great game buy the under; at entry price
  + 1¢ (and 2¢); hold to the result; one bet per player-stat-game. Variants fixed now: all stats; points only.
- Periods: development games dated ≤ 2026-02-15; TEST 2026-02-16 .. 2026-04-28, evaluated once.
- Pass bar on TEST: S7 mean return > 0 at 1¢ with 95 % CI excluding 0 (cluster = player), ≥ 300 bets; and the primary
  premium difference with CI excluding 0. Player panel: the 20 players with the most pre-game $ in development, per-player
  premiums reported descriptively (too few games each for per-player claims).
- **B7 amendment, 2026-10-29 (before any prop price or statistic was looked at; the props table was still building):**
  real box scores replace the market-only performance measure, at Ayaan's request. Source: Kaggle
  `szymonjwiak/nba-traditional` (CC BY-NC-SA, non-commercial research; downloaded via the Kaggle API, 2025-26 has
  28,698 player rows 2025-10-21..2026-06-13). NBA's stats API refused requests and is not used.
  - Join: game date + player name normalised (lower-case, punctuation removed, spaces → hyphens) against the slug's
    player; the match rate is reported and unmatched props are dropped and counted.
  - Performance of game n: z_n = (stat_n − line_n) / sd, where sd = the player's SD of that stat over his earlier games
    this season (≥ 5 games, else the pair is dropped). bad: z_n ≤ −1; great: z_n ≥ +1. Games with minutes < 60 % of his
    season-to-date average are a separate stratum (foul trouble, injury, blowout), reported but not traded.
  - Added measure (c), the honest baseline: does z_n predict the next game's actual stat vs its line (real form)? The
    market only overreacts if the price moves more than this.
  - S7 entry rule: bad → buy over, great → buy under. The threshold k ∈ {0.5, 1.0, 1.5} (|z_n| ≥ k) is picked on
    development by mean return; all three are reported on TEST. Pass bar unchanged.

## Planned next (2026-10-29, Ayaan's idea; recorded before any in-play or post-game prop trade was examined; full rules come before running)
- **B8 In-game overreaction:** during game n+1, does the over price fall further after a cold start than the player's
  rest-of-game distribution justifies? Needs in-game stats by wall-clock time (candidate: Kaggle `deocheng/nba-data-1946-2026`
  play-by-play; usable only if it carries wall-clock or the game clock can be mapped to real time reliably).
- **B9 Settlement lag:** after the final whistle, how far below 1 (or above 0) do decided props trade before resolution,
  for how long, and with how much size? A mechanical gap, not a bias; measured from fills after the game's end.
- **B7 development decisions, 2026-10-29 (test period not yet run):**
  - Fixes during development (bugs, not tuning): slug-name aliases and jr/ii suffixes; and **next-game no-shows (DNP) are
    now counted** (an over bet loses, an under bet wins), since dropping them selects on the outcome and flatters overs.
  - S7 on development: every cell negative (best: points k = 1.0, −2.8 % at 1¢; all stats k = 1.5, −2.9 %). Rule applied:
    k = 1.0 (points) is the chosen cell; ALL cells are reported on TEST regardless.
  - **New hypothesis from development, S7b "the over is overpriced" (Hugo's Yes premium, in props):** buy the UNDER on every
    priced main line, at 1¢ and 2¢; and an S7c variant: buy the under only after a great game (|z| ≥ 1, the hot-hand
    case). Pass bar as S7. Development showed premium +0.04..+0.10 in every bucket; TEST decides.
