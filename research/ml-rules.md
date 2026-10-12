# Pre-registered rules — headline→move model and latency replay (2026-10-11 23:30 CDT, before any model is trained)

## A. Headline → (market, direction, move) model
- Inputs: Benzinga headlines (data/archive/alpaca_news_*.parquet, 2022-11..2026-04) and Truth Social posts; Polymarket daily_aligned(+multi) fills.
- Pairing: headline matched to markets by the committed slug-keyword lexicon (research/backtest-rules.md lexicon, extended once and committed before labelling); market must have ≥ 20 fills in the prior 7 days at t0.
- Labels per (headline, market): dp15 = last-trade price in [t0+12m, t0+18m] minus mean of last 5 fills before t0 (NaN → drop); y_move = |dp15| ≥ 0.02; y_dir = sign(dp15) on movers.
- Splits by TIME, fixed now: train 2022-11-01..2025-09-30; validation 2025-10-01..2025-12-31 (model selection only); test 2026-01-01..2026-04-27 (touched once, at the end). No tuning on test. Placebo rows (random times, same markets) included in train with y_move from their own dp15, so the model must beat "markets move anyway".
- Models: (1) baseline = keyword lexicon direction + market's recent |move| rate; (2) text embeddings (sentence-transformers, local) + gradient boosting (sklearn HistGradientBoosting) predicting y_move and y_dir; (3) optional small fine-tune only if (2) beats baseline on validation.
- Metrics on test: AUC for y_move vs baseline and vs a "price-only" model (features: p0, recent fill rate, time of day); directional accuracy on movers with 95 % CI; calibration. Pass bar: AUC(y_move) ≥ baseline + 0.05 AND directional accuracy on movers > 55 % with CI excluding 50 %. Report failure plainly.
## B. Latency replay (fills-only, paper)
- Universe: the 1,993 Truth Social pairs from Result 2 restricted to liquid markets (≥ 50 fills in the prior hour).
- Rule: at t0 + Δ (Δ ∈ {2, 10, 30} s) submit a $500 taker order in the direction the keyword lexicon gives (and separately: the direction of the first post-t0 trade, as an oracle upper bound); fill at the first trade price at or after t0+Δ; exit at the last trade price in [t0+12m, t0+18m]; fee sensitivity 0 / 1 % / 2 % of notional per side (Polymarket taker fees vary; report all three); no fill if no trade within 60 s.
- Metrics: mean PnL per trade in points and $, bootstrap 95 % CI over events, hit rate, n; placebo = same rule at the placebo times. Pass bar: mean PnL at 1 % fee > 0 with CI excluding 0 on ≥ 100 trades.
## Honesty
Rules committed before running (this file's blob hash is cited in results). No variant is dropped; every variant run is reported.

## B2. Addendum, committed 2026-10-12 00:00 CDT, before it is run — LLM-direction arm
Reason: the lexicon direction rule returned no direction for 619 of 677 liquid event pairs (91 %), so arm B's "lexicon" test had 31-37 trades and little power; the "oracle" arm is momentum-following, not news-reading. The real question (does READING the post give a tradeable direction?) is untested.
- Direction: Claude Haiku via `claude -p --model haiku`, given only the post text and the market's slug-as-question, answers up / down / none for the YES price (fixed prompt committed in research/replay-llm-prompt.md before any call; no post-t0 information in the prompt). Applied to the same 677 liquid event pairs; at placebo times the event's own LLM direction is held fixed (same convention as the lexicon arm).
- Everything else identical to section B (Δ ∈ {2,10,30} s, $500, same fill/exit rules, fees 0/1/2 %, event-cluster bootstrap, same seeds). Note the LLM's own latency (~3 s) makes Δ = 2 s unachievable in practice; report all three anyway.
- Leakage check: the model's training data may include these events (posts are Oct 2025-Apr 2026). Report results separately for posts before and after 2026-02-01 and say plainly that memorisation cannot be excluded.
- Pass bar unchanged: mean PnL at 1 % fee > 0 with 95 % CI excluding 0 on ≥ 100 trades. Also report event minus placebo.
