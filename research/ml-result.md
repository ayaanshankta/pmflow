# Result — headline → (market, direction, move) model (rules: research/ml-rules.md §A, blob a6140e5)
Code: lexicon.py (a37a879, committed before labelling), ml_fetch.py, ml_dataset.py, ml_train.py, test_ml.py (80120ec). Run 2026-10-12.

## Verdict: **FAIL** (pre-registered bar needs BOTH)
| criterion | value | bar | result |
|---|---|---|---|
| AUC(y_move): text model − baseline | 0.892 − 0.772 = **+0.120** | ≥ +0.05 | pass |
| directional accuracy on movers, text model | **51.7 %**, Wilson 95 % [49.6, 53.8], n = 2,195 | > 55 % and CI excludes 50 % | **FAIL** |

Plain reading: the model predicts *which markets move* (AUC 0.89), but almost all of that comes from market features (p0, fill rate, hour: price-only AUC 0.876). Text adds +0.016 AUC over price-only. Headline text does **not** predict *direction*: 51.7 % vs 52.1 % for always guessing "up" (the up-share among test movers). The baseline "recent |move| rate" is a weak baseline for a move model, so +0.12 over it overstates what the headline contributes.

## Data (real pairs; placebo = same headline text at a random time on the same market, ±3 d, ≥ 1 h from any matched headline, same 20-fill/label rules)
Headlines: 122,427 Benzinga + 4,870 Truth Social lexicon-matched (127,297) → 421,996 candidate (headline, market) pairs, top-5 markets by prior-7d fills, ≥ 20 fills prior 7 d, not resolved. 73 % (307,835 of 421,996) have no fill in [t0+12m, t0+18m] or no p0 and are dropped per rule, leaving 114,161 real pairs.

| split | kind | n | headlines | markets | y_move rate | movers | up-share of movers |
|---|---|---|---|---|---|---|---|
| train (..2025-09-30) | real | 65,212 | 32,387 | 2,251 | 16.4 % | 10,712 | 50.3 % |
| train | placebo | 45,154 | 23,282 | 1,808 | 10.6 % | 4,771 | 50.0 % |
| val (2025-10-01..12-31) | real | 18,997 | 7,324 | 504 | 8.5 % | 1,620 | 49.6 % |
| val | placebo | 15,499 | 6,723 | 458 | 5.4 % | 836 | 50.4 % |
| test (2026-01-01..04-27) | real | 29,952 | 10,126 | 769 | 7.3 % | 2,195 | 52.1 % |
| test | placebo | 26,358 | 9,697 | 705 | 5.1 % | 1,348 | 51.6 % |

Real pairs move more than placebo in every split (16.4 vs 10.6, 8.5 vs 5.4, 7.3 vs 5.1 %): news timing carries some signal, consistent with Result 2. Placebo rows are train-only for fitting; val/test scoring is on real rows. Sources (real, y_move): Benzinga 16.9 / 8.6 / 7.3 %, Truth Social 8.3 / 6.8 / 7.2 % (train/val/test).

## Test metrics (test split scored once, n = 29,952 real pairs, 2,195 movers)
| model | AUC(y_move) | val AUC | dir. accuracy on movers (n) | Wilson 95 % | cluster-bootstrap 95 % (by market-day) |
|---|---|---|---|---|---|
| baseline: market recent-|move| rate (y_move) / lexicon polarity (direction) | 0.772 | 0.770 | 52.6 % (645 calls, 29 % coverage) | [48.7, 56.4] | – |
| price-only HGB (p0, fills/h, fills/7d, hour) | 0.876 | 0.867 | 51.1 % (2,195) | [49.0, 53.2] | [48.6, 53.5] |
| **text + price HGB** (headline emb PCA32 + slug emb PCA16 + price) | **0.892** | 0.882 | **51.7 %** (2,195) | [49.6, 53.8] | [49.5, 53.9] |

Selection (validation only, 4-point grid lr ∈ {.05,.1} × leaves ∈ {15,31}, 150 iters, l2 = 1): text move 0.1/31; text dir 0.1/15 (val acc 49.8 %); price move 0.05/15; price dir 0.1/31. Optional fine-tune (3) not run: it was gated on beating baseline on validation for *direction*, which the embedding model did not.

Calibration of the text model on test (10 fixed bins of predicted P(move)): the model is over-confident, because train's move base rate (16 % real, 10.6 % placebo) is far above test's 7.3 %.
| bin | 0–.1 | .1–.2 | .2–.3 | .3–.4 | .4–.5 | .5–.6 | .6–.7 | .7–.8 | .8–.9 | .9–1 |
|---|---|---|---|---|---|---|---|---|---|---|
| n | 18,886 | 3,297 | 2,763 | 2,153 | 1,376 | 819 | 428 | 177 | 52 | 1 |
| mean predicted | .019 | .149 | .248 | .348 | .446 | .546 | .642 | .742 | .841 | .920 |
| observed | .005 | .080 | .132 | .202 | .292 | .366 | .442 | .599 | .712 | 1.0 |
Ranking is useful (observed rate rises monotonically), probabilities are ~1.5–2× too high; price-only has the same shape. A recalibration on validation would fix levels, not ranking.

## Caveats
- **Keyword relevance is crude** (Result 2: ~3 of 10 sampled pairs clearly related). Many headlines (e.g. a company-news item matching "apple", "meta", "gold") are only loosely tied to the market; direction labels on such pairs are noise. A cleaner relevance filter (LLM) could raise direction accuracy and is the obvious follow-up; this result is for the pre-registered keyword pairing only.
- **Settlement stamps:** block_timestamp is on-chain settlement (a few seconds after the match); irrelevant at 12–18 min horizons.
- **Label noise / selection:** dp15 uses the last fill in a 6-min window vs a 5-fill mean; thin markets bounce between bid and ask, producing |dp15| ≥ 0.02 from spread alone. 73 % of candidate rows have no fill in the window and are dropped (the sample is conditional on a fill happening, i.e. on active markets). y_dir is on fill-price moves, not mid.
- **Non-stationarity:** move rate falls 16 → 8.5 → 7.3 % across splits (2024 election markets dominate train). Models were not retrained on train+val.
- **Dependence:** one headline maps to ≤ 5 markets and markets re-appear daily; Wilson CIs assume independence. The market-day cluster bootstrap is about as wide as Wilson and leads to the same conclusion.
- **Excluded by lexicon decision:** slugs matching `up-or-down|updown` (5/15-min/hourly coin-flip markets, the bulk of crypto fills in 2026; one probed day was ~75 % of all fills) are excluded — they resolve within minutes and would dominate the data. 2022-11..2023 has almost no matching liquid markets (first months have ≤ a few k fills), so the train set is effectively 2024–2025-09.
- Direction baseline = sign of (positive − negative word count) in lexicon.py, applied to the Yes-axis price regardless of the market's wording: crude by design, only makes a call on 29 % of movers.
- A first `ml_train.py test` run crashed on a string-concatenation bug AFTER computing AUCs and BEFORE writing results/ml_test.json (models and thresholds were fixed; nothing was refit or tuned); the fixed re-run produced the table above.

## Commands
```
cd pmflow-M   # branch pm/ml; data/archive symlinked to ~/Downloads/pmflow/data/archive
P=/opt/anaconda3/bin/python3
$P ml_fetch.py          # 41 monthly steps, ~40 min, <= 0.2 GB raw on disk at a time -> data/ml_fills (421 MB)
$P ml_dataset.py        # -> data/ml_pairs.parquet (18 MB), counts above
$P ml_train.py select   # validation grid -> results/ml_selected.json, data/ml_models.joblib
$P ml_train.py test     # one-shot test scoring -> results/ml_test.json (refuses to run twice)
$P -m pytest -q test_ml.py   # 7 passed
```
