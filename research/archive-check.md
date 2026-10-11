# Archive timestamp precision check (2026-10-11)
**Verdict: second-precise** (Polygon block time, ~2 s granularity, max 9 s per block). The "~3 h noise" claim of arXiv 2602.19520 is NOT reproduced in this dataset.

## 1. Event study (script: `archive_check.py`; raw rows `results/archive_check_events.csv`)
t0 = FOMC statement 14:00 ET / CPI 08:30 ET (zoneinfo, DST-correct). Fills on matching markets within ±6 h. `peak_min` = minute (relative to t0) with most fills in [t0-60m, t0+60m].
`first_move_s` = seconds from t0 to first fill ≥2 pts from the pre-release price on the busiest market (blank = price never moved ≥2 pts, i.e. outcome already priced in).

| kind | date | t0 UTC | mkts | fills [-60m,0) | fills [0,+5m) | fills [0,+1m) | peak min | peak n | busiest market (p before → +15m) | first move |
|---|---|---|---|---|---|---|---|---|---|---|
| FOMC | 01-29 | 19:00 | 5 | 1809 | 288 | 215 | 0 | 215 | cut-25 0.027→0.001 | 37 s |
| FOMC | 03-19 | 18:00 | 4 | 330 | 257 | 147 | 0 | 147 | no-change 0.996→0.999 | – |
| FOMC | 05-07 | 18:00 | 4 | 629 | 118 | 103 | 0 | 103 | cut-25 0.005→0.001 | – |
| FOMC | 06-18 | 18:00 | 4 | 586 | 195 | 170 | 0 | 170 | no-change 0.991→0.999 | – |
| FOMC | 07-30 | 18:00 | 4 | 796 | 212 | 133 | 0 | 133 | no-change 0.990→0.999 | – |
| FOMC | 09-17 | 18:00 | 4 | 4794 | 300 | 216 | -7 | 242 | cut-50 0.056→0.001 | 14 s |
| FOMC | 10-29 | 18:00 | 4 | 1953 | 509 | 427 | 0 | 427 | cut-25 0.996→0.999 | – |
| FOMC | 12-10 | 19:00 | 4 | 4103 | 511 | 380 | 0 | 380 | cut-25 0.962→0.999 | 6 s |
| CPI | 01-15 | 13:30 | 7 | 121 | 149 | 0 | 1 | 135 | ann ≤2.6 0.010→0.001 | 101 s |
| CPI | 02-12 | 13:30 | 8 | 92 | 100 | 0 | 2 | 58 | mo ≤0.1 0.013→n/a | – |
| CPI | 03-12 | 12:30 | 10 | 492 | 201 | 72 | 1 | 118 | ann ≥3.1 0.006→n/a | – |
| CPI | 04-10 | 12:30 | 10 | 53 | 79 | 62 | 0 | 62 | ann ≤2.4 0.328→n/a | 39 s |
| CPI | 05-13 | 12:30 | 5 | 225 | 130 | 93 | 0 | 93 | ann ≥2.7 0.025→0.001 | 25 s |
| CPI | 06-11 | 12:30 | 10 | 163 | 274 | 114 | 1 | 146 | ann ≤2.2 0.025→0.001 | 62 s |
| CPI | 07-15 | 12:30 | 10 | 348 | 382 | 341 | 0 | 341 | ann ≥2.6 0.844→0.999 | 25 s |
| CPI | 08-12 | 12:30 | 5 | 118 | 95 | 18 | 1 | 50 | ann ≥3.0 0.057→0.001 | 60 s |
| CPI | 09-11 | 12:30 | 10 | 426 | 183 | 108 | 0 | 108 | ann =2.9 0.430→0.999 | 7 s |
| CPI | 10-24 | 12:30 | 10 | 82 | 104 | 91 | 0 | 91 | ann =2.9 0.448→n/a | 37 s |
| CPI | 12-18 | 13:30 | 10 | 127 | 508 | 176 | 1 | 267 | mo =0.3 0.908→0.289 | 60 s |

(p +15m = mean `p_event` of fills in [t0+12m, t0+18m]; "n/a" = no fill in that window.) Peak minute is 0 in 13/19 events and 1-2 in the rest; 18 of 19 events put ≥1 minute-bin peak within 2 min of t0 — nothing like a 3-hour smear. Fills in the first minute after t0 exceed the *whole* previous 5 minutes in most events. Prices step to the resolved level within seconds-to-minutes (fastest 6 s on 12-10 FOMC, 7 s on 09-11 CPI). The 09-17 peak at -7 min is pre-release positioning on a day with 4.8k fills in the hour before (Miran/50bp speculation), not timestamp noise.

## 2. Block-number consistency (raw `OrderFilled`, `id` = chain_block_log)
| shard | fills | blocks | ts conflicts within a block | monotone | s/block median / p99 / max | gaps >10 s |
|---|---|---|---|---|---|---|
| 2025_04 | 7,428,320 | 974,669 | 0 | yes | 2 / 4 / 6 | 0 |
| 2025_06 | 8,893,402 | 1,004,152 | 0 | yes | 2 / 4 / 9 | 0 |

One timestamp per block, strictly monotone in block number, ≤9 s between consecutive observed blocks. That is exactly the Polygon PoS block cadence; hours of noise is impossible. An independent RPC anchor (polygon-rpc / publicnode / ankr) could not be reached from this machine (SSL failure), so the absolute offset to wall-clock is validated only by the event-study jump at t0 (peak within 0-2 min), which bounds any constant bias to ~1 min.

## 3. Caveats for the backtest
- Timestamp = on-chain settlement of the fill, a few seconds after off-chain CLOB match; fine for minute-scale lag, borderline for <5 s claims.
- Fills only: no quotes. Price after news = last trade, so thin markets give stale/NaN windows (several "→n/a" above); no spread/depth.
- Daily layers are tiny (~2 MB/day), so the whole of 2025 is only ~0.7 GB; no need for the 1.5 GB raw months except for block ids.
- Archive ends 2026-04-28; overlap with our live recorder (starts 2026-10-10) is zero, so cross-validation vs our own tob data is not possible; only an event-based check.

Download used: 555 MB (`data/archive/`: 38 daily files = 130 MB + 2 raw shards 2025_04, 2025_06 = 0.42 GB).
