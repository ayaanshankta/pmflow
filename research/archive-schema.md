# Polymarket-v1 archive schema (HF `TimeSeventeen/Polymarket-v1`, CC-BY-4.0, checked 2026-10-11)
Paper: arXiv 2606.04217. 1,201,580,990 raw fills, 2022-11-21..2026-04-28, ~49 GB parquet total. **No order book / quotes** — fills only.

| Layer | Path | Size | Notes |
|---|---|---|---|
| raw | `OrderFilled/YYYY_MM.parquet` (monthly) | 185 MB (2025-04) .. 1.5 GB (2025-12) | 13 cols; `id` = `chainId_blockNumber_logIndex` (only layer with block no.); includes relayer/router rows |
| clean, binary | `daily_aligned/YYYY_MM_DD.parquet` | ~2 MB/day (30k-90k rows) | neg_risk=false; 24 cols; **used here** |
| clean, neg-risk | `daily_aligned_multi/YYYY_MM_DD.parquet` | ~2 MB/day | + `neg_risk_market_id`; **all Fed-decision markets live here**, binary layer has CPI-style markets too |
| CTF | `CTF/{preparations,splits,merges,resolutions,redemptions}.parquet` | 0.1-5 GB | `preparations` links `condition_id`<->`question_id` |

## Columns (daily_aligned)
`asset_id` (token id), `block_timestamp` (int64 unix **seconds**), `price`, `maker`, `taker`, `taker_direction`, `usdc_amount`, `fee_usdc`,
`condition_id`, `outcome_seq` (1=reference/Yes), `neg_risk`, `category`, `category_refined`, `outcome_label`, `winning_outcome_label`, `resolution_status`,
`taker_base_fee`, `maker_base_fee`, `opens_at`, `close_at`, `resolved_at`, `market_slug`, `p_event` (price on outcome_seq=1 axis: price, or 1-price for the other leg), `D` (+1 taker buys reference event).

## Market identification
`condition_id` (market) + `asset_id` (token) + `market_slug`. **There is no question text column**; the slug is the human label
(e.g. `fed-decreases-interest-rates-by-25-bps-after-january-2025-meeting`, `will-annual-inflation-increase-by-2pt7-or-more-in-april`).
A question/metadata table was not needed; slug regex was enough for macro events. (SII-WANGZJ/Polymarket_data not inspected: unnecessary.)
Gotcha: `block_timestamp` is chain-block time (~2 s), not CLOB match time; `p_event` should be used instead of `price` for event probability.
Gotcha: slug month = the *reference* month for CPI (release in month M is "in-<M-1>").
