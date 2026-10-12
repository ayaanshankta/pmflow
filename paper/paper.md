# How fast do prediction markets price the news? Second-resolution evidence from 1.2 billion Polymarket fills

**Ayaan Shankta** — Carnegie Mellon University — ayaanshankta08@gmail.com
Draft, 2026-10-11. Not peer reviewed.

## Abstract

Do prediction markets lag the news? We measure reaction times in the public Polymarket-v1 archive of 1.2 billion on-chain fills (2022–2026), whose timestamps we show are second-precise. On 19 scheduled 2025 macro releases (8 FOMC, 11 CPI), fill activity peaks within two minutes of release in 18 cases and the first price move of two points or more arrives 6–101 s after release. For 400 unscheduled Truth Social posts matched by keyword to 1,993 markets, liquid flagship markets moved in 13–33 s, while the median pair that moved at all took 682 s (about 11 minutes; 95 % CI 531–900) and most pairs did not move. Against placebo times, the apparent excess in how often prices move is a dead-market artifact. Slowness is illiquidity, not latency: we find no sellable news-to-price lag where liquidity exists. Rules were fixed before measurement; fills are settlement-stamped, so second-level figures are upper bounds.

## 1 Introduction

**Question.** When news arrives, how long does a prediction-market price take to reflect it? Two answers circulate. One is that these markets are fast: informed traders and bots move prices within seconds. The other is that retail-heavy venues are slow, with repricing delays measured in tens of minutes or hours. We ask the question at the resolution that separates them: seconds, around dated news events, with a placebo to say what "normal" movement looks like.

**Why it matters.** For market efficiency, a repricing delay on the order of seconds is evidence that information is incorporated about as fast as the venue's matching and settlement allow; a delay on the order of an hour would be a measurable inefficiency in a venue now used as a source of probability forecasts. For practice, the question is whether a "news-reaction feed" has anything to sell: a service that tells a subscriber which markets a headline touches and how far they have moved is only valuable if there is a window between the headline and the price.

**What we find.** We test this on two classes of news using only data that is public. Scheduled macro releases are priced within seconds to roughly a minute and a half. Unscheduled posts by a high-profile political account produce a burst of trading, but the typical keyword-matched market takes about 11 minutes to move two points, and a placebo comparison shows that most of the apparent difference from random moments is a measurement artifact. The markets that are liquid and clearly on-topic move within 13–33 s. The negative result is the main one: we find no sellable lag where there is liquidity, and the slow cases are thin markets that simply have no one trading in them.

**Contributions.** (i) A timestamp-precision check of the Polymarket-v1 archive (Section 3). (ii) A scheduled-release event study at second resolution (5.1). (iii) A pre-registered, placebo-controlled test on unscheduled news with independently re-derived numbers (5.2–5.4). (iv) A frank account of what fills-only data cannot show (Section 6).

## 2 Related work

We know of no study that measures second-level news-to-price latency from Polymarket or Kalshi data across both scheduled and unscheduled, non-crypto events. Closest work, as summarized from our literature notes (the papers themselves were read only as far as needed to place this study):

- **Diercks, Katz and Wright (FEDS 2026-010)** study Kalshi forecast accuracy and the response of Kalshi-implied distributions to CPI, PCE, payrolls, ISM and FOMC releases. Their distributions are built from last trades and updated daily, and we found no time-to-reprice figure. Our scheduled-release section is complementary: same kind of event, second rather than daily resolution, a different venue.
- **arXiv 2609.06005 (Ibrahim and Zaki)** use 173.7 M on-chain Polymarket fills from 2024–25, hourly prices and daily GDELT news. They identify 44,976 moves of five points or more across 9,590 markets and find that 74 % of 630 timed first news citations come after the move. Their direction of inference is the reverse of ours (move first, then look for news), and by construction they cannot resolve who moved first at finer scales.
- **OpenMarket (arXiv 2607.26245)** has millisecond resolution but, per our notes, covers BTC markets against Binance (median lag 347 ms), so it measures cross-venue price discovery in a market with an external reference price rather than reaction to news.
- **PolyBench (arXiv 2604.14199)** is a one-week benchmark for LLM forecasters on Polymarket, not a latency study.
- **Popular claims.** A "1-hour" repricing window is reported under the name "Attention Gap", and a trade-press article asserts an "80-minute repricing delay" without a source we could find. Our scheduled-release numbers (6–101 s) and flagship-market numbers (13–33 s) contradict these as statements about markets where traders are present; our thin-market result (about 11 minutes, or no move) is the part of the picture they may be describing.
- **Timestamp noise.** arXiv 2602.19520 is cited in our notes as claiming roughly three hours of timestamp noise in on-chain Polymarket data. We do not reproduce this in the archive we use (Section 3.2).

## 3 Data

### 3.1 Polymarket-v1 fills archive

We use the Hugging Face dataset `TimeSeventeen/Polymarket-v1` (CC-BY-4.0; described in arXiv 2606.04217): 1,201,580,990 raw fills from 2022-11-21 to 2026-04-28, about 49 GB of parquet. It has four layers:

| Layer | Content | Size | Used here |
|---|---|---|---|
| raw `OrderFilled` | monthly shards, 13 columns, `id` = chain_block_log; includes relayer rows | 185 MB (2025-04) to 1.5 GB (2025-12) | block-timestamp check only |
| `daily_aligned` | cleaned, binary (non-neg-risk) markets, 24 columns, ~2 MB/day | — | yes |
| `daily_aligned_multi` | cleaned neg-risk markets (all Fed-decision markets); adds `neg_risk_market_id` | — | yes |
| CTF | preparations, splits, merges, resolutions, redemptions | 0.1–5 GB | no |

The archive contains **fills only: no order book and no quotes**. Markets are identified by `condition_id`, `asset_id` and `market_slug`; there is no question-text column, so we match on slugs. The price series we use is `p_event`, the price on the reference-outcome axis (the price, or one minus the price for the other leg), not the raw `price`. The timestamp, `block_timestamp`, is an integer number of Unix seconds.

### 3.2 Timestamp precision

Because event-study conclusions at second resolution rest on the timestamp, we checked it two ways.

*Block consistency.* In the raw layer, each `id` carries a block number. In two monthly shards (2025-04 with 7,428,320 fills in 974,669 blocks; 2025-06 with 8,893,402 fills in 1,004,152 blocks) there were **0** conflicting timestamps within a block, timestamps were **monotone** in block number, the median spacing was **2 s** per block (p99 4 s; maximum 6 s in April and 9 s in June), and there were no gaps over 10 s. That is the Polygon PoS block cadence, and it is incompatible with hours of timestamp noise.

*Event response.* Fill counts jump at the scheduled release time in the events of Section 5.1 (peak minute 0 in 12 of 19 events, within two minutes in 18 of 19), which bounds any constant offset in the archive's clock to about a minute. We could not reach a public Polygon RPC node from our machine to anchor absolute time independently, so the absolute offset is validated by this event response only.

### 3.3 Truth Social archive

Unscheduled events are posts by one account taken from the CNN-hosted Truth Social archive (`ix.cnn.io/data/truth-social/truth_archive.json`; full history from 2022-02; `created_at` with millisecond precision, which we floor to the second). This is a third-party archive that we did not create or audit beyond using its timestamps; posts it omits or mis-times would not be in our event set.

### 3.4 What fills-only data can and cannot show

A fill is a trade that happened. From fills we can say when trading in a market intensified and when the last traded price first differed from the earlier price. We cannot say what the best bid and ask were, whether a quote was stale or the book was empty, or how deep the market was. A price "not moving" in this data is indistinguishable from "no one traded". Timestamps are on-chain settlement, a few seconds after the off-chain match, so the figures below are upper bounds on how long a reaction took and cannot support claims below about five seconds.

## 4 Method

**Pre-registration.** The unscheduled-news rules (`research/backtest-rules.md`) were committed at git commit `dc5a9c8` (blob `bdab62a0db474f5202ab05036104aa71604a6b0e`) on 2026-10-11 at 15:19 CDT, before any market measure had been computed; results followed at 21:56. Any change would be a dated amendment at the bottom of that file; it contains none. The independent verifier re-derived the headline numbers with separately written code.

**Events.** Posts dated 2025-01-20 to 2026-04-27 with at least 20 letters after removing URLs and a leading "RT:" are matched against a fixed lexicon of 11 topics (tariffs, the Fed, China, Iran, Russia/Ukraine, Greenland, Canada/Mexico, TikTok, shutdown, the Supreme Court, named people). A matched post is dropped if another matched post occurred in the preceding 10 minutes, and the 400 most recent remaining posts are the events. 1,016 posts matched the lexicon over the whole window; the 400-event cap means events span 2025-10-22 to 2026-04-24.

**Markets and pairs.** For each event the candidate markets are those whose slug matches a slug term for any topic the post matched, with at least one fill in the previous 7 days, and not resolved at t0. The top five by prior-week fill count are kept. A (post, market) *pair* additionally needs at least one fill before t0 to define the pre-news price p0 (mean of `p_event` over the last 5 fills).

**Measures (per pair).** Fills in [t0−60 min, t0); fills in [t0, t0+5 min); time to the first fill at or after t0; time to the first fill at least two probability points from p0 within 60 minutes (`t_move`; undefined if none); and |p − p0| at 15 minutes, using the last fill in [t0+12 min, t0+18 min].

**Placebo.** For each pair, 20 uniform random integer-second times on the same market within ±3 days of t0, excluding ±2 hours around any matched post, with the same activity rule and seeded generators. A secondary placebo matches time of day (within ±60 min of t0's clock time on other days). This gives 39,639 placebo draws for 1,993 pairs.

**Estimation.** Resampling unit is the event (cluster bootstrap, 10,000 resamples). The "excess" is the event's fill count in the first 5 minutes minus the mean of that pair's placebo counts, averaged over pairs. CIs are 95 % percentile intervals.

**Pass bar ("unscheduled news reprices fast").** Both: (1) median `t_move` over moved event pairs below 120 s, and (2) the mean excess in first-5-minute fills has a bootstrap CI excluding zero. If not both, the rules require reporting that, with numbers.

**Scheduled releases (5.1)** are a descriptive event study not covered by the pre-registered rules file: t0 is the official release time (FOMC statement 14:00 ET, CPI 08:30 ET, DST-corrected), and for each event we used the markets matching the release by slug regex and report the busiest one.

## 5 Results

### 5.1 Scheduled releases: 19 events

Table 1 is the full list. "Fills" are counts on all matching markets; "peak min" is the minute relative to t0 with the most fills within ±60 min; "first move" is seconds from t0 to the first fill at least 2 points from the pre-release price on the busiest market (a dash means no such move: the outcome was already priced in).

**Table 1.** Scheduled 2025 releases.

| kind | date | t0 UTC | mkts | fills [−60m,0) | fills [0,+5m) | fills [0,+1m) | peak min | busiest market (p before → +15m) | first move |
|---|---|---|---|---|---|---|---|---|---|
| FOMC | 01-29 | 19:00 | 5 | 1809 | 288 | 215 | 0 | cut-25 0.027→0.001 | 37 s |
| FOMC | 03-19 | 18:00 | 4 | 330 | 257 | 147 | 0 | no-change 0.996→0.999 | – |
| FOMC | 05-07 | 18:00 | 4 | 629 | 118 | 103 | 0 | cut-25 0.005→0.001 | – |
| FOMC | 06-18 | 18:00 | 4 | 586 | 195 | 170 | 0 | no-change 0.991→0.999 | – |
| FOMC | 07-30 | 18:00 | 4 | 796 | 212 | 133 | 0 | no-change 0.990→0.999 | – |
| FOMC | 09-17 | 18:00 | 4 | 4794 | 300 | 216 | −7 | cut-50 0.056→0.001 | 14 s |
| FOMC | 10-29 | 18:00 | 4 | 1953 | 509 | 427 | 0 | cut-25 0.996→0.999 | – |
| FOMC | 12-10 | 19:00 | 4 | 4103 | 511 | 380 | 0 | cut-25 0.962→0.999 | 6 s |
| CPI | 01-15 | 13:30 | 7 | 121 | 149 | 0 | 1 | ann ≤2.6 0.010→0.001 | 101 s |
| CPI | 02-12 | 13:30 | 8 | 92 | 100 | 0 | 2 | mo ≤0.1 0.013→n/a | – |
| CPI | 03-12 | 12:30 | 10 | 492 | 201 | 72 | 1 | ann ≥3.1 0.006→n/a | – |
| CPI | 04-10 | 12:30 | 10 | 53 | 79 | 62 | 0 | ann ≤2.4 0.328→n/a | 39 s |
| CPI | 05-13 | 12:30 | 5 | 225 | 130 | 93 | 0 | ann ≥2.7 0.025→0.001 | 25 s |
| CPI | 06-11 | 12:30 | 10 | 163 | 274 | 114 | 1 | ann ≤2.2 0.025→0.001 | 62 s |
| CPI | 07-15 | 12:30 | 10 | 348 | 382 | 341 | 0 | ann ≥2.6 0.844→0.999 | 25 s |
| CPI | 08-12 | 12:30 | 5 | 118 | 95 | 18 | 1 | ann ≥3.0 0.057→0.001 | 60 s |
| CPI | 09-11 | 12:30 | 10 | 426 | 183 | 108 | 0 | ann =2.9 0.430→0.999 | 7 s |
| CPI | 10-24 | 12:30 | 10 | 82 | 104 | 91 | 0 | ann =2.9 0.448→n/a | 37 s |
| CPI | 12-18 | 13:30 | 10 | 127 | 508 | 176 | 1 | mo =0.3 0.908→0.289 | 60 s |

"p +15m" is the mean `p_event` of fills in [t0+12 min, t0+18 min]; "n/a": no fill in that window.

Summary: the peak minute is 0 in 12 of 19 events and 1–2 in six more (18 of 19 within two minutes of t0); the exception is 2025-09-17, where a −7 minute peak reflects pre-release positioning in a day with 4,794 fills in the preceding hour, not timestamp noise. In 12 of 19 events a first ≥2-point move was observed on the busiest market, 6–101 s after release (fastest 6 s on 2025-12-10 FOMC and 7 s on 2025-09-11 CPI). In the seven others the market was already pinned (≥ 0.99, or the move was never ≥ 2 points), so there was nothing left to reprice. Fills in the first minute after release exceed the whole preceding five minutes in most events.

**Interpretation.** On scheduled macro news the price reaches its new level within seconds to under two minutes. This is the best case for efficiency: everyone knows when the number will print, so liquidity is concentrated at the moment. A fast response here says nothing yet about news nobody scheduled.

### 5.2 Unscheduled posts: event versus placebo

**Table 2.** Truth Social posts against Polymarket, 400 events, 1,993 pairs (events 2025-10-22 to 2026-04-24). "ev" = event, "pl" = placebo. Excess is first-5-minute fills, event minus pair-matched placebo mean, 95 % event-cluster bootstrap CI.

| set | events | pairs | fills [0,+5m) ev / pl | excess [0,+5m) | moved within 60 min ev / pl | median `t_move` s ev (95 % CI) / pl | median first fill s ev / pl | mean \|dp\| at 15 min ev / pl |
|---|---|---|---|---|---|---|---|---|
| primary (random ±3 d) | 400 | 1,993 | 14.8 / 6.3 | **+8.5 [4.3, 13.9]** | 17.3 % / 13.4 % | **682 [531, 900]** / 1,210 | 89 / 108 | 0.0122 / 0.0066 |
| secondary (clock-time matched) | 400 | 1,993 | 14.8 / 6.5 | +8.3 [4.0, 13.8] | 17.3 % / 14.5 % | 682 [531, 900] / 1,096 | 89 / 106 | 0.0122 / 0.0073 |
| secondary (0.02 ≤ p0 ≤ 0.98) | 370 | 1,116 | 22.5 / 9.0 | +14.5 [7.4, 23.9] | 30.6 % / 23.3 % | 682 [528, 900] / 1,202 | 82 / 100 | 0.0161 / 0.0086 |

Fills in the hour before the post averaged 116.6 for event pairs against 73.5 for placebo (primary). 344 of 1,993 event pairs had a ≥2-point move within 60 minutes. The verifier's independent code gave an excess of +8.7 [4.5, 14.4].[^v1]

**Against the pre-registered bar.** Criterion (2) passes: posts coincide with about 2.3 times the fills of a random moment in the first five minutes (+8.5, CI excluding zero), robust to clock-time matching and to dropping pinned markets. Criterion (1) fails clearly: the median time to a ≥2-point move among pairs that moved is 682 s (CI 531–900), not under 120 s. The overall answer to "does unscheduled news reprice within seconds?" is no. Only 3.4 % of pairs have a ≥2-point move within 120 s, against 1.3–1.6 % at placebo times. The first fill after the post is only modestly earlier than at random (median 89 s against 108 s), so in thin markets the post does not bring fills much sooner either.

### 5.3 The bimodal split: flagship markets versus the rest

The following splits were **not pre-registered**; they were run after seeing the primary result and should be read as interpretation, not as tests.

**Table 3.** Exploratory splits of the primary set (post hoc).

| subset | pairs | moved | median `t_move` s | pairs with ≥2-pt move within 120 s |
|---|---|---|---|---|
| all | 1,993 | 344 | 682 | 3.4 % |
| top market of each event only | 400 | 49 | 493 | 3.8 % |
| ≥ 1,000 fills in prior 7 d | 1,555 | 296 | 640 | 4.2 % (placebo 1.6 %) |
| ≥ 5,000 fills in prior 7 d | 1,144 | 231 | 603 | 5.0 % (placebo 1.8 %) |
| ≥ 100 fills in the hour before | 488 | 206 | 506 | 11.1 % |

**Table 4.** Examples. The first five rows are the five highest-activity events; the table in the repository also lists five seeded random draws, which are not repeated here.

| t0 UTC | post (start) | market | p0 | fills −60m / +5m | first fill | first ≥2-pt move |
|---|---|---|---|---|---|---|
| 2026-04-07 22:32:26 | "Based on conversations with Prime Minister Shehbaz Sharif…" | US × Iran ceasefire by April 7 | 0.335 | 6,366 / 2,390 | 5 s | 15 s |
| 2026-02-28 21:37:32 | "Khamenei, one of the most evil people in History, is dead…" | Khamenei out as Supreme Leader by Feb 28 | 0.907 | 6,433 / 1,555 | 1 s | 33 s |
| 2026-01-03 09:21:19 | "The United States of America has successfully carried out a large scale strike against Venezuela…" | Maduro out by Jan 31 2026 | 0.376 | 1,206 / 598 | 8 s | 16 s |
| 2026-04-16 15:36:39 | "I just had excellent conversations with … President Joseph Aoun, of Lebanon…" | Israel × Hezbollah ceasefire by April 30 | 0.880 | 1,681 / 536 | 3 s | 13 s |
| 2026-01-30 11:48:54 | "I am pleased to announce that I am nominating Kevin Warsh to be the Chairman of the Board…" | Will Trump nominate Judy Shelton as next Fed chair | 0.022 | 1,045 / 530 | 2 s | 130 s |

In the four most active, clearly on-topic examples the first ≥2-point fill came 13–33 s after the post, similar to the scheduled releases. The fifth example, a Fed-chair market on a different nominee, moved after 130 s. Beyond that handful, most keyword-matched markets are thin or only loosely related, and they move slowly or not at all. Restricting to markets with more prior trading shifts the share moving within two minutes from 3.4 % to 4–5 %, and to markets already busy in the preceding hour, to 11.1 %, but each of these remains a small minority. The figure "13–33 s for flagship markets" is a selection by activity after the fact, not a pre-registered statistic.

### 5.4 Robustness and verifier corrections

The independent verifier (separately written code) reproduced the numbers and corrected three readings that we adopt here.

1. **The "moved more often than placebo" gap is mostly a placebo artifact.** Event pairs moved ≥2 points within 60 minutes 17.3 % of the time against 13.4 % for placebo, a 3.8-point gap. But 23.6 % of placebo draws fell on dead markets (no trading to move), which depresses the placebo rate mechanically. With an alive-only placebo the comparison is 17.3 % against 17.2 %: no difference.[^v2]
2. **The fill excess is tail-driven.** The median pair's excess is −0.15 fills; the top 5 % of pairs carry the mean. Part of the excess is also "busy times": a difference-in-differences that nets out pre-post fill changes at placebo times gives +5.2 [1.8, 9.8], smaller than +8.5 but still above zero.[^v3]
3. **Keyword relevance is crude.** About 3 of 10 sampled pairs were clearly related to the post. Because slug terms such as `fed`, `china` and `bps` are broad, 100 % of events received at least one candidate market, which says little about true relevance. The pre-registered median `t_move` is therefore diluted by unrelated markets.

[^v1]: Our pipeline gave +8.5 [4.3, 13.9]; the verifier's independent re-derivation gave +8.7 [4.5, 14.4]. We report ours in the table and the verifier's here; the difference is within bootstrap noise.
[^v2]: Verifier correction. The raw 17.3 % vs 13.4 % comparison is what Table 2 reports; the corrected reading is the alive-only 17.3 % vs 17.2 %.
[^v3]: Verifier correction; the difference-in-differences and the median pair excess (−0.15) were computed by the verifier, not by the pre-registered pipeline.

**Net.** Activity around posts is real but concentrated in a few pairs and times; the claim that thin markets reprice *later* than random is a conditional-on-fill median compared against a placebo that is itself dominated by dead markets. The claim we can defend is narrower: where there is liquidity, prices move in seconds; where there is none, they do not move, and that is not latency.

## 6 Limitations

- **Settlement time, not match time.** Timestamps are on-chain settlement, a few seconds after the off-chain match. Second-level figures are upper bounds; sub-5 s claims are not supported.
- **Last trade only.** There are no quotes. A "move" is a different last trade price, so thin markets give stale or missing windows, and a quote that repriced without a trade would be invisible. Medians are conditional on a fill happening.
- **Keyword relevance.** The mapping from post to market is a slug-term lexicon, not a judged relation. About 3 in 10 sampled pairs were clearly related. No LLM or second human labeller was used on the archive study.
- **400-event cap.** Events cover 2025-10-22 to 2026-04-24; matched posts between 2025-01-20 and 2025-10-21 are not measured. One account, one lexicon, one venue.
- **No direction scoring.** We use |Δp|; we do not check whether prices moved the way the post implied.
- **Event time is post time.** t0 is when the post appeared, not when the news became known; reposts of known stories are only filtered by the 10-minute burst rule.
- **Event-day confounds.** A post inside a day with other news is not modelled; the clock-time-matched placebo changes nothing, and the difference-in-differences is a partial correction only.
- **Kalshi excluded.** Kalshi's Developer Agreement (v1.1, §3 and §3.1) limits API use to a member's own trading and bars storing or sharing the data without written authorization; its currency could not be confirmed. We therefore make no statement about Kalshi's repricing speed.
- **Live recorder.** We also operate a live top-of-book recorder on Polymarket. At the time of writing it has produced no news-reaction number (only three crypto-article events fell inside its first recording window, none judged to touch a recorded market), so nothing in this draft depends on it.

## 7 Conclusion

Across two classes of news and 1.2 billion fills, we find no news-to-price lag worth selling where there is liquidity. Scheduled macro releases are priced within about 6–101 s on the busiest market. Unscheduled posts bring a burst of trading, but where a market is liquid and clearly on-topic, the price moves in 13–33 s; where the keyword match is loose and trading is sparse, prices move slowly or not at all, which is illiquidity, not latency. The popular "hour-scale" figures are best read as statements about thin contracts.

*What a feed could and could not sell.* A feed that says which markets a headline touches would be selling a mapping, not a head start: in the liquid markets we measured, the price had already moved within seconds. It could, in principle, flag thin markets that have not moved, but the fills-only data here cannot tell whether those markets are mispriced or simply untraded, and a lagging price in an untraded contract is not a price anyone can trade at. We therefore treat the negative result as the finding and do not recommend building the feed. Natural extensions are an alive-only placebo as the primary comparison, trimmed or median excess as the primary statistic, an LLM relevance judgement, direction scoring, and quote-level data, where our live recorder may help.

## Data and code availability

Code, pre-registered rules, verifier notes and derived tables (including `results/backtest_truth_summary.json` and `results/archive_check_events.csv`) are in the project repository `pmflow`, which is private for now; we intend to release code and derived event tables. The Polymarket-v1 archive is CC-BY-4.0 on Hugging Face. The Truth Social archive is third-party and was used under its public availability; we do not know its terms. **Benzinga news headlines (obtained through Alpaca) were collected for a later phase and are NOT redistributable pending a licence check; none is used in this paper's results, and none is released.** Polymarket's Terms of Use could not be read and redistribution rights for its live data are therefore unknown; Kalshi data was not collected.

## References

1. Diercks, Katz and Wright. Federal Reserve Board FEDS 2026-010 (Kalshi forecast accuracy and response to macro releases). Series: https://www.federalreserve.gov/econres/feds/ (paper-specific URL not recorded in project notes).
2. Ibrahim and Zaki. arXiv:2609.06005 (173.7 M Polymarket fills and GDELT news). https://arxiv.org/abs/2609.06005
3. OpenMarket. arXiv:2607.26245 (Polymarket BTC markets against Binance, millisecond resolution). https://arxiv.org/abs/2607.26245
4. PolyBench. arXiv:2604.14199 (one-week LLM forecasting benchmark on Polymarket). https://arxiv.org/abs/2604.14199
5. Polymarket-v1 dataset. arXiv:2606.04217; https://huggingface.co/datasets/TimeSeventeen/Polymarket-v1 (CC-BY-4.0).
6. arXiv:2602.19520 (reported ~3 h timestamp noise in on-chain Polymarket data; not reproduced here). https://arxiv.org/abs/2602.19520
7. CNN-hosted Truth Social archive. https://ix.cnn.io/data/truth-social/truth_archive.json
8. Kalshi Developer Agreement v1.1. https://kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf
9. "Attention Gap" one-hour study and "80-minute repricing delay" claim (Cryptonomist): secondary and unsourced; URLs not recorded in project notes, so not cited as evidence.
10. U.S. Bureau of Labor Statistics release schedule. https://www.bls.gov/schedule/news_release/bls.ics
