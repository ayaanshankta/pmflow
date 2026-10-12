# mm-scope (2026-10-11, Opus researcher) — assembled
Bottom line: a paper maker backtest is worth building only as a reward+rebate accounting study with bounded fill assumptions. BLOCKER is legal: pmflow records the INTERNATIONAL CLOB, which a US person cannot open positions on.
## 1. Liquidity rewards (international; high confidence on mechanics)
Book sampled once a minute at a random offset; epoch = UTC day. Order score S = ((v-s)/v)^2 * b (v = market max spread, s = distance from adjusted mid). Two-sided: mid in [0.10,0.90] -> Q_min = max(min(Q1,Q2), max(Q1,Q2)/3); outside -> min(Q1,Q2). Paid daily midnight UTC, $1 min. Gamma fields rewardsMinSize, rewardsMaxSpread, clobRewards[].rewardsDailyRate. CLOB V2 + pUSD collateral since Apr 28 2026.
pmflow universe (Gamma 2026-10-12 04:41 UTC): 152 of 200 returned; 82 carry rewards totalling $23.3k/day; median pool $100/day, min size 50 shares, max spread 4.5c.
$5k book estimate (researcher inference, one Sunday-night snapshot): 5,000 shares/side 1c from mid -> median $9-23/day on mid 0.1-0.9 markets (0.2-0.5 %/day BEFORE adverse selection). No public maker-earnings data found.
## 2. Fees/ticks/limits (high confidence)
Intl: taker pays C*rate*p(1-p); makers pay 0. Rates crypto 0.07, politics/finance/tech 0.04, sports/econ/culture 0.05, geopolitics free. Maker rebate 25 % of pool (crypto 20 %, sports 15 %). Dynamic crypto fee on 15-min markets, peak 1.56 % at 50 %; crypto taker delay 150 ms.
pmflow universe: 111/152 fee-enabled; MEDIAN TICK 0.001 and median spread 0.002 (pmflow assumed 0.01 tick -> re-check t_reprice rule). Min order 5. Rate limits 40 orders/s, 80 cancels/s; batch 15 orders, 1000 cancel ids.
Polymarket US: taker theta 0.0695, maker rebate theta 0.0125 (~0.31c/share at 50c), effective Oct 7 2026.
## 3. Order API
Intl: POST /order, /orders; DELETE /order, /orders, /cancel-all, /cancel-market-orders; GTC/GTD/FOK/FAK + post-only; user ws .../ws/user; auth L1 EIP-712 + L2 HMAC; py-clob-client-v2. US person on intl CLOB: NO (US listed close-only on frontend and API)...
(pending rest)
