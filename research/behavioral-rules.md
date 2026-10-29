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

## B9 Settlement lag in NBA props — rules (2026-10-29, before any post-game fill has been read)
Mechanical, not a bias: after the game, a prop's outcome is known from the box score, but the market resolves later.
Do decided props trade below 1 for the winning side, for how long, and with how much size?
- Markets: the props in data/behav/props.parquet. Winner from the on-chain payout (1,0 = over), so DNP props pay the
  under as they really did.
- "Decided" time: tip-off (`close_at`) + 3 h (NBA regulation is ~2 h 15 m; double overtime ends by ~2 h 50 m).
  Sensitivity: + 2.5 h and + 4 h.
- Fills kept: every fill from tip + 2 h until on-chain resolution. Winning-side price q = p_event if the over won,
  else 1 − p_event.
- Reported (all props, by stat; per-prop and per-fill):
  - Share of props with ≥ 1 fill after decided.
  - $ after decided.
  - Distribution of the discount 1 − q (cents).
  - Time from decided to resolution.
  - $ traded at q ≤ 0.98 and q ≤ 0.95 (the size a buyer of the known winner could have taken).
  - Mean return 1/q − 1 per fill, by discount bucket.
- Also counted: fills where q < 0.5 after decided, i.e. someone paid up for the LOSING side. These measure the risk
  that "decided" is wrong: stat corrections, late resolution disputes, or my tip + 3 h rule.
- No pass bar, no strategy claim: the question is how big the gap is and how much size it takes. Fees: report gross and
  the documented 0.04·q·(1−q).

## Round 2 (2026-10-29, Ayaan: "look everywhere in the book"). Rules written before any of these statistics was computed.
Same snapshot table, Yes/No markets without up-or-down, same periods (DEV snapshots 2023-01-02..2024-12-30, TEST
2025-01-06..2026-03-30), same price-bin adjustment and clustering (market; event also reported), and the same one-entry-per-market
strategy mechanics as S1 (1¢ and 2¢ slippage, entry at the snapshot price; ALSO reported at the Monday VWAP entry
from behav_entry.py, since the S1 check showed the pre-T entry flatters results). Pass bar for every strategy: TEST mean return
> 0 at 1¢ with CI excluding 0, ≥ 300 trades, AND > 0 at the Monday-VWAP entry.

- **B10 Planning fallacy (ch. 23).** "Planned-completion" markets: slug has `-by-` or `-before-` AND a project verb
  (release|launch|pass|passes|sign|signs|approve|approved|ipo|announce|complete|ship|open|reopen|deliver|implement|start|
  confirm|confirmed). Compare with other deadline markets. Prediction: price-bin-adjusted premium higher. S10: buy NO
  when Yes ∈ [0.10, 0.60].
- **B11 Wishful thinking on crypto upside (ch. 9, 24).** Crypto slugs (bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|
  dogecoin) with an upside word (above|reach|hit|exceed|higher|over|ath|all-time) vs a downside word (below|dip|fall|drop|
  under|lower|crash). Prediction: the upside Yes premium is larger. S11: buy NO on upside markets with Yes ∈ [0.10, 0.60].
  **Contamination:** the S1 verifier reported crypto "above" ladders strongly positive to fade on TEST. So for B11 the
  confirmatory period is DEV (2023–24) plus snapshots 2026-04-06..2026-04-27. The TEST number is reported but carries
  no weight.
- **B12 Hope that does not decay (ch. 29, possibility effect over time).** Longshots, Yes ∈ [0.02, 0.10]: premium by days
  to close (≤ 2, 2–7, 7–30, > 30). Prediction: premium larger close to the deadline. S12: buy NO when Yes ∈ [0.02, 0.10]
  and ≤ 7 days to close. Mild contamination: B1's horizon slopes on TEST were seen (all-price, not longshot premium).
- **B13 Round-number anchoring (ch. 11).** Snapshots priced from an exact last fill (p_from_last_fill). Round = within
  0.001 of {0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90}; neighbours = 0.01–0.02 away from a round
  price. Report the share of fills at round prices and the premium at round vs neighbour prices. No strategy.

Wallet tests (new pass `behav_wallets.py` over both layers; maker and taker addresses).
- Per fill: buyer and seller of token `asset_id` at `price`; v = the token's on-chain payout (0, 0.5 or 1);
  hold-to-resolution PnL of the buyer = usdc·(v/price − 1), the seller the negative. Fees ignored.
- Aggregated per (wallet, month traded, month resolved). Wallet return = PnL / $ traded.
- **B15 Illusion of skill (ch. 20).** Periods P1 = trades in 2024, P2 = trades in 2025. Wallets with ≥ $1,000 traded and
  ≥ 20 fills in both. Report the Spearman correlation of P1 vs P2 return, and the P2 return of the P1 top decile, with a
  bootstrap CI over wallets. Kahneman's fund managers ≈ 0 persistence; Polymarket may differ (sharps, insiders). No
  strategy claim from this test. A copy-trading test needs its own rules and a later pass.
- **B16 Overconfidence / overtrading (ch. 24).** In P2, wallet return by deciles of fill count (wallets ≥ $1,000).
  Prediction: the most active retail-size wallets do worst. Reported separately for the top 1% by $ volume (likely market makers).
- **B14 Disposition effect (ch. 26, 32; Odean 1998).** Sample: wallets with int(address, 16) % 50 == 0, all their fills
  in both roles. Positions per (wallet, token) at average cost.
  - On each day a wallet sells any token, every other open position with a price that day is an opportunity, marked as
    a gain or a loss against the day's last price.
  - PGR = realized gains / (realized + paper gains); PLR likewise. Prediction: PGR > PLR. Bootstrap over wallets.
- **B17 Break-even effect (prospect theory).** Same sample. After a position of ≥ $20 resolves as a loss vs as a win,
  compare the wallet's mean buy price over the next 7 days with its own mean buy price before. Prediction: lower
  (longer shots) after losses. Paired within wallet, bootstrap over wallets.
- **B18 Recency overreaction in ANY recurring series (ch. 10 law of small numbers, ch. 17; Ayaan's generalisation of
  B6/B7).** Series = Yes/No markets sharing a slug template after removing dates, month names, years and numbers
  (e.g. weekly tweet counts, daily temperatures, monthly CPI, recurring polls, box office, app ranks, price ranges).
  - Consecutive instances: the next market of the same template whose close follows the previous one's within 1–45 days.
  - Surprise of instance k = Y_k − p_k, where p_k is its last snapshot price before resolution.
  - Prediction under overreaction: the premium of instance k+1 at its first snapshot after instance k resolved
    (p − Y) is positively related to the surprise of k. After an unexpected Yes, the next Yes is overpriced.
  - Report: the slope of premium_{k+1} on surprise_k, and premium_{k+1} after |surprise| ≥ 0.5 split by sign.
    Bootstrap over templates. Also by category.
  - S18: after a surprise ≥ +0.5, buy NO on k+1; after ≤ −0.5, buy YES on k+1. Pass bar as above.
  - Excludes up-or-down and sports moneylines (B6 covered those).
  - Contamination: none seen (no series-level statistic has been computed).

## B19 (2026-10-29, written before any computation; from Ayaan's break-even idea)
- **Aggregate caution after losses.** Weekly loss L_w = sum of realized hold-to-resolution losses (PnL < 0) of the
  sample wallets (int(addr,16) % 50 == 0) on positions resolving in the 7 days before snapshot Monday w, excluding the
  top 1% of sample wallets by $ (likely market makers). Weeks split at the DEV median of L_w (scaled by that week's
  total sample $ resolved, to remove the growth trend) into high-loss and normal weeks.
- Prediction: after high-loss weeks, traders seek safety, so favourites (Yes in [0.70, 0.95], Yes/No binaries,
  not up-or-down) are overpriced: premium p − Y higher in high-loss weeks. Price-bin-adjusted, clustered by WEEK.
- S19: in high-loss weeks buy NO on favourites (Yes in [0.70, 0.95]); first qualifying snapshot per market.
  Pass bar as round 2 (TEST mean > 0 at 1¢ with week-clustered CI excluding 0, >= 300 trades, > 0 at MonVWAP + 1¢).
- Known weakness: about 65 TEST weeks, so low power; a null is weak evidence.
- Contamination: B12 showed favourites/longshot premia by horizon on TEST, never split by loss week.

## B20 (2026-10-29, written before any computation): multi-outcome overround at an achievable price
- **Basket.** A neg-risk event (nr_id) at snapshot T. Legs = its markets present at T. Complete = the legs at T are
  every condition_id of that nr_id seen anywhere in the snapshot table with res_ts > T (a live trader sees the full
  leg list from the API; outcomes are not used). Incomplete event-snapshots are excluded; the count is reported.
- Overround O = sum of leg Yes prices − 1.
- **S20 No basket** (O >= threshold): buy one No share of every leg. Cost = Σ(1 − p_i + slip_i), payout = Σ(1 − Y_i).
  Return = payout / cost − 1 (per $ of capital), plus the median days held to the last leg's resolution.
- **S20b Yes basket** (O <= −threshold): buy one Yes share of every leg. Cost = Σ(p_i + slip_i), payout = ΣY_i.
- Thresholds 0.02, 0.05, 0.10. First qualifying snapshot per event.
- Slippage per leg: 1¢ when the leg's price is in [0.05, 0.95], 0.1¢ outside it (tick size there is 0.001). Also
  reported with zero slippage.
- Entries: snapshot price (last fill) and Monday VWAP per leg (event excluded if any leg lacks a Monday VWAP;
  coverage reported). Monday VWAP is the executable check.
- ΣY ≠ 1 at resolution (no winner among the legs, or ties) is kept, and how often it happens is reported.
- Pass bar as round 2: TEST mean > 0 at slippage, week-clustered CI excluding 0, >= 300 events, and > 0 at Monday
  VWAP + slippage. DEV is 2023-12-22..2024-12-30 (the multi layer starts 2023-12-22).
- Priors and contamination: B2 showed multi-outcome legs overpriced, and the S1 verifier showed the neg-risk half
  of fade-Yes losing at Monday VWAP (single legs, not baskets). Result 6 of pmflow (live quotes, one family) saw no
  complete-set mispricing. Expected result: overround is mostly stale tail prices and is not achievable.

## B20-forward (2026-10-29, before any new quote is read): overround on simultaneous live quotes
- Data: desktop top-of-book recordings of complete exclusive families from 2026-10-13 14:16:03 UTC (conn_id 46) on,
  excluding recorded gaps. Method and bar: C1 in sets_check.py unchanged (rules blob 1582327e1f20), side B
  (sum of live Yes bids > 1 + fee; selling every Yes = the No basket of B20).
- Added report for B20: per family, the share of fresh time with sum of bids > 1 and > 1.01, episode duration, and
  min displayed size in $. B20 counts as confirmed only if fee-clearing fresh episodes appear in >= 3 families with
  >= $50 of size; otherwise the B20 archive result is read as a non-simultaneous-price artefact.
