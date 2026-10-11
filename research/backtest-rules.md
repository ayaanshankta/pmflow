# Backtest rules — unscheduled news (Trump Truth Social posts) vs Polymarket-v1 fills
Written 2026-10-11, committed BEFORE any market measure was computed. Changing anything below = a new dated amendment at the bottom.

**Question.** Does Polymarket reprice UNSCHEDULED news within seconds (as it did scheduled releases, DECISIONS Result 1), or is there a lag?

## Data
- Events: CNN-hosted Truth Social archive (`https://ix.cnn.io/data/truth-social/truth_archive.json`, full history from 2022-02, `created_at` ms-precision UTC). t0 = created_at floored to the second.
- Fills: HF `TimeSeventeen/Polymarket-v1`, layers `daily_aligned` + `daily_aligned_multi`, columns block_timestamp (s), condition_id, market_slug, p_event, resolved_at, close_at. A market = condition_id; its price = `p_event` (reference-outcome axis). A "fill" = one row.

## Events
1. Window: t0 in [2025-01-20 00:00 UTC, 2026-04-27 23:00 UTC] (archive ends 2026-04-28; last hour margin).
2. Text = content with URLs removed and a leading `RT:` removed, whitespace collapsed. Excluded: text with < 20 letters (pure media, bare retweets, URL-only).
3. Lexicon (case-insensitive; terms match on token boundaries, i.e. not preceded/followed by a letter). A post is a *matched post* if its text matches ≥ 1 topic:

| topic | post regex terms | market-slug terms (hyphen-delimited tokens) |
|---|---|---|
| tariff | tariff, tariffs | tariff, trade-deal, trade-war |
| fed | fed, powell, interest rate(s), rate cut(s), federal reserve | fed, powell, interest-rates, rate-cut, bps |
| china | china, chinese, xi jinping, xi | china, xi, taiwan |
| iran | iran, iranian | iran |
| russia_ukraine | russia, russian, ukraine, putin, zelensky, zelenskyy, ceasefire, cease-fire | russia, ukraine, putin, zelensky, ceasefire |
| greenland | greenland | greenland |
| canada_mexico | canada, canadian, mexico, mexican | canada, mexico |
| tiktok | tiktok | tiktok |
| shutdown | shutdown | shutdown |
| supreme_court | supreme court, scotus | supreme-court, scotus |
| people | musk, elon, netanyahu, maduro, mamdani, newsom, vance, rubio, bessent, lutnick, harris | the same name as a slug token |

   (`trump` is deliberately not a slug term: it is in most slugs.)
4. Burst rule: a matched post is dropped if another matched post exists in the prior 10 minutes (kept or not). Remaining matched posts are the candidate events.
5. Cap: the 400 most recent candidate events.

## Markets (candidates for an event)
- Slug matches ≥ 1 slug term of any topic the post matched.
- Active: ≥ 1 fill in [t0-7d, t0). Not resolved: resolved_at is null or > t0.
- Keep the top 5 by fill count in [t0-7d, t0). A (event, market) **pair** needs ≥ 1 fill before t0 (for p0).
- Relevance rate = share of events with ≥ 1 pair. Also reported: share of lexicon-matched posts (before burst rule/cap) in the covered date span.

## Measures (per pair; all from fills)
- `pre60` fills in [t0-60m, t0); `post5` fills in [t0, t0+5m); `post_5_60` fills in [t0+5m, t0+60m).
- p0 = mean of p_event over the last 5 fills before t0; p_first = first fill at/after t0 (within 60 m).
- `t_first_fill`: seconds to the first fill ≥ t0 (NaN if none within 60 m).
- `t_move`: seconds to the first fill in [t0, t0+60m] with |p_event − p0| ≥ 0.02 (NaN if none).
- `dp15` = |p_last − p0| with p_last = last fill in [t0+12m, t0+18m] (NaN if none).

## Placebo
For each pair, 20 uniform random integer-second times on the same market in [t0-3d, t0+3d], excluding ±2 h around ANY matched post (incl. burst-dropped and beyond the cap, in the downloaded span), restricted to times ≥ 7 d + after data start and ≤ 2026-04-27 23:00 UTC. Same measures with the same activity rule (needs ≥ 1 fill before). Seeded: numpy RandomState(20261011 + event_index*1000 + market_rank). Fewer than 20 valid draws after 5000 attempts → use what exists.
Secondary placebo (reported, not the verdict): same, but time-of-day matched — candidate times must lie within ±60 min of t0's UTC clock time, on other days.

## Estimation
- Unit of resampling = event (cluster bootstrap, 10,000 resamples, RandomState(7)); all CIs 95 % percentile.
- Event excess = per pair: post5_event − mean(post5_placebo of that pair); mean over pairs; bootstrap CI of the pair-mean.
- Median `t_move` over moved pairs (event side) with bootstrap CI; placebo median `t_move` reported alongside.
- Secondary (reported, not the verdict): same table restricted to pairs with 0.02 ≤ p0 ≤ 0.98 ("unpinned").

## Pre-registered pass bar — "unscheduled news reprices fast"
BOTH: (1) median `t_move` over moved event pairs < 120 s; AND (2) mean excess `post5` over placebo has a bootstrap 95 % CI excluding 0 (positive).
If not both: report that, honestly, with the numbers (including "no detectable reaction" if excess ≈ 0).

## Known limitations (stated up front)
- Fills only, no quotes; block time = on-chain settlement a few seconds after the match, so sub-5 s claims are not supported.
- Keyword relevance is crude; most posts will match no active market. "Moved" is conditional on a fill happening — thin markets bias medians; the placebo median is the comparison.
- t0 is the post time, not the time the news is "known"; reposts of known stories are not filtered beyond the burst rule.
