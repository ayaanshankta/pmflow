# pmflow — do prediction markets lag the news, and where?

**Question.** When news arrives, how long does a Polymarket contract take to reprice, and is there any place (scheduled
releases, unscheduled posts, thin markets, related markets on the same event) where the lag is long enough and large enough
to trade after costs?

**Answer across seven results.** No such lag was found, in any of the places looked at. Liquid markets reprice scheduled
releases within seconds to about 100 s, and the liquid on-topic markets moved 13–33 s after unscheduled posts (a post hoc
split). Thin, loosely related markets move late or not at all, which is a property of illiquidity, not of latency. A language
model reading the posts picks directions that beat random times by roughly half a point to a point before fees once one event
is removed; that is the size of the fee, and it has not been tested on posts after the model's training cutoff. A model
trained on headlines found no directional signal. Related-market (sibling) lead-lag in the 2025
trade archive is real but worth 0.15–0.25 points gross against a fee several times larger. One question is left genuinely open:
whether sibling *quotes* lag, which the trade archive cannot show.

**Method.** The test, the bar and the data were written down and committed before each test was run; every result was
re-derived by an independent verifier writing its own code (exceptions are marked in the table); and corrections, including to
the author's own first readings, are recorded in `DECISIONS.md`. This is measurement and paper analysis only: nothing was
traded, and nothing here is described as an edge.

## Results

All seven come from the dated log in `DECISIONS.md`; the per-result files are in `research/`. Intervals are 95 %.
"Verified" means a verifier re-derived the numbers with independent code.

| # | What was tested | Data and sample | Headline number | Verdict against the pre-set bar | Main caveat |
|---|---|---|---|---|---|
| 1 | Do prices move at scheduled macro releases within seconds? (`archive-check.md`) | 19 scheduled 2025 releases (8 FOMC, 11 CPI); Polymarket on-chain fills archive | Fill activity peaks in minute 0 for 12 of 19 events and within 2 min for 18; first ≥2-pt move 6–101 s after release (12 events with a move; 7 of 19 already pinned ≥0.99). Verified, 5 of 5 re-derived events identical | No lag to sell on scheduled news (descriptive; no numeric bar was set for the archive check) | Best case (everyone is waiting); last-trade prices only; on-chain stamps trail the match by seconds, so the seconds are upper bounds |
| 2 | Do unscheduled Truth Social posts move Polymarket within seconds? (`backtest-truth.md`) | 400 posts, 2025-10-22 to 2026-04-24, keyword-matched to 1,993 markets; 20 placebo times per pair | Fills in first 5 min 14.8 vs 6.0–6.3 placebo, excess +8.5 [4.3, 13.9]; median time to ≥2-pt move 682 s [531, 900] vs ~1,200 s placebo. Verified | Activity criterion passes; "median < 120 s" fails | Excess is tail-driven; keyword relevance crude (about 3 of 10 sampled pairs clearly related); move-frequency gap was a placebo artifact |
| 3 | Would trading 2–30 s after a matched post have paid? Fills-only replay (`replay-result.md`) | Same 400 posts, liquid markets (677 pairs); $500 paper orders | Lexicon arm at 1 % fee, 2 s: −0.68 [−1.17, −0.12] points, n=32 vs placebo −0.69 [−0.84, −0.55], n=670. No detectable gross difference. Verified | Fails at every delay (also n<100) | Lexicon arm has only 20 events; fills only (no spread or impact); 2 s is inside settlement jitter |
| 4 | Does a language model reading the post pick direction? (`replay-llm-result.md`, `replay-llm-controls-result.md`) | Haiku on the same 677 pairs: 192 up / 141 down / 344 none | Gross event-minus-placebo at 10 s +1.67 [+0.36, +3.61] (226 trades, 122 posts); +0.84 [+0.24, +1.52] without the one Maduro post; +0.44 [+0.07, +0.84] without the top three posts. At the venue fee, first-trade entry +1.20 [−0.06, +3.07] | Fails the profit bar at every delay and fee | One post is 49 % of the PnL; gain is the size of the fee; training cutoff not excluded; main arm verified, the controls not independently re-derived |
| 5 | Can a model trained on headlines predict which markets move, and which way? (`ml-result.md`) | 127,297 Benzinga + Truth Social headlines paired to markets; test 2026-01 to 04: 29,952 pairs, 2,195 movers | "Will it move" AUC 0.892 vs price-only 0.876 vs baseline 0.772; direction on movers 51.7 % [49.6, 53.8] vs always-up 52.1 %. Verified | Fails (move criterion passes; direction needs >55 % with CI above 50 %) | The AUC gain over price-only is market identity, not headline content; relevance crude, so this does not show news cannot predict direction |
| 6 | Are complete sets of related markets priced consistently on live quotes? (`sets-result.md`) | Recorder data, 200 markets, 7.98 h observed on 2026-10-10 (Saturday, with a 4.3 h hole) | Exactly 1 complete exclusive family (14 brackets): 0 fee-clearing episodes; 22 episodes at zero fee, ≤2.0 points, ≤$13 | Bar not met, and this data could not have met it (needed ≥3 complete families) | **Not independently verified.** One family, 8 hours, a weekend |
| 7 | Do sibling markets follow a leader's jump, tradeably? (`leadlag-result.md`) | 2025 archive, test half 2025-07 to 12: 75,852 leader jumps, 333,170 (jump, sibling) pairs | Paper trade at 30 s: +0.19 points gross, −0.51 [−0.56, −0.46] at the venue fee (21,482 jumps); median volume near the entry $0 vs bar $200. Verified | Fails; exclusive and ladder families fail separately | Cannot speak to quotes: 56 % of siblings never trade within 15 min of a jump; the 2025 fee is hypothetical (0 on sampled fills) |

## What each result says, corrected

**1. Scheduled releases.** Prices step to their resolved level within seconds to minutes; the fastest were 6 s (FOMC
2025-12-10) and 7 s (CPI 2025-09-11). The archive's `block_timestamp` is second-precise (0 conflicts within a block,
monotone, ~2.13 s per block), so a published claim of hours of timestamp noise is not reproduced on this dataset. It is
the best case for a fast market, so it says little about thinner events.

**2. Unscheduled posts.** The verifier's corrections stand as the reading. The gap in "moved within 60 min" (17.3 % vs 13.4 %)
is mostly a placebo artifact: 23.6 % of placebo draws landed on dead markets, and an alive-only placebo gives 17.3 vs 17.2 %.
The fill excess is carried by the tail (median pair excess −0.15; the top 5 % of pairs carry it) and partly by busy times
(difference-in-differences +5.2 [1.8, 9.8]). Only 3.4 % of pairs move ≥2 points within 120 s (1.3–1.6 % at random). The
13–33 s reactions of flagship markets (Iran ceasefire, Khamenei, Maduro, Lebanon) are a post hoc split.

**3. Latency replay.** The finding is *no detectable gross edge* from entering 2–30 s after matched posts: event is about
equal to placebo. Three corrections to the first reading. (a) The "oracle" arm is **not an upper bound**: its direction is the
sign of the first post-t0 trade, and 92 % of 2 s entries are that same trade, so it buys the print it was selected on.
Entering on the next trade instead gives +0.001 [−0.73, +0.83] points at 0 % fee (n=323); read it as a momentum-with-bounce
control. (b) The lexicon arm is underpowered (32 trades over 20 events; 91 % of liquid pairs had no direction) and supports no
conclusion about news direction. (c) Flat 1–2 % fees overstate cost; at the documented rate × p(1−p) with rate 0.04 the
lexicon arm is +0.02 (a wash).

**4. Language-model direction.** A model reading the post picks directions that beat placebo times by a small gross
amount. It shrinks hard under scrutiny: one post (Maduro, 2026-01-03) is 49 % of all PnL, 226 trades are at most 122
independent bets (one averaged trade per post: +0.96 [+0.23, +2.04]), and three of the Iran winners had $553, $23 and $10
within 2 cents of entry, so those gains were not available at $500. The standing description is therefore **roughly half a
point to a point gross, once one event is removed, about the size of the fee, so it does not clear costs**. It has not been
tested on posts after the model's training cutoff, so recall of what followed a post is not excluded. The "larger edge before
February" is the one Maduro event (+0.70 without it); the before/after split says nothing about memorisation. The memorisation
controls were of limited use: the first two (no post; wrong post) had almost no power, because the model answered "none" on
97–98 % of control pairs (8 and 11 trades, intervals about ±1.3 points) — my design flaw, since the prompt allowed
abstaining. What they do show is that without the right post the model almost never commits to a direction (agreement with the
main arm 1.5 % and 0.3 %), so its calls depend on the post and not on the market title. The forced-choice, title-only control
(677 calls) gave −0.45 [−1.86, +0.68] on the same 226 trades; it excludes a title-only effect of +1.4 or more but not one of
about +0.7. **Its reading rule was not satisfied as written**: agreement with the main arm was 43.8 %, outside the 45–55 %
band I had committed to, because the forced guess was 91 % "down" against 58 % "up" and independent answers would agree about
43.7 % of the time. The rule was not rewritten afterwards.

**5. Headline model.** The "will it move" AUC (~0.88) mostly measures which markets are active, and holds for markets
never seen in training. The gain of text-plus-price (0.892) over price-only (0.876) is **market identity, not headline
content**: an ablation gives price 0.871, price plus market-slug embedding 0.893, price plus headline 0.884, and headline on
top of the slug adds −0.001. Direction on movers shows no signal in any subset (Truth Social 47.1 %, n=121; top-decile
confidence 49.5 %). The up-or-down market exclusion was committed before labelling; the feature set's ordering relative to the
test set cannot be proven from the record.

**6. Complete sets.** This was a test that could not be passed: the universe was "top 200 by volume", which cut 30 of 31
exclusive families and all 29 ladders apart, leaving **exactly one complete family** to test. Supplementary, outside the bar:
partial families and ladder pairs gave 41 fee-clearing episodes in 4 of 37 testable families, almost all worth cents to about a
dollar; the largest (2.29 points, $1.67) lasted 0.09 s and looks like one leg updating before the other. The universe now keeps
families whole. This result was not independently verified.

**7. Sibling lead-lag.** Siblings do follow a leader's jump: +0.12 / +0.18 / +0.24 points versus placebo at 1 / 5 / 15 min.
About 71 % of the 15-min move is already in the price at the sibling's first trade, and visible flow is almost nil. But the
result **cannot speak to quotes**: 56 % of siblings never trade in the 15 minutes after a jump, a pair with no trade is scored
"unchanged" by construction, and "already in the price at the first trade" cannot distinguish a fast market from one nobody
touched. The sign rule I wrote for exclusive families ("opposite to the leader") is right only 57 % of the time, because
bracket families move with the underlying. About fifteen after-the-fact cuts were looked at without correction and none is a
finding. The question is open, not closed.

## What is still open

Two pre-registered tests have not run.

1. **C3 — quotes around leader jumps on whole families** (`research/structure-rules.md`, section C3, committed 2026-10-12
   04:25 CDT). Uses recorded top-of-book quotes, takes direction from price arithmetic rather than a sign rule, and is
   evaluated once, after 100 leader jumps in complete families. The bar is at least 20 fee-clearing violations lasting ≥ 2 s
   with ≥ $100 available, across ≥ 3 families, and a post-jump violation rate above placebo. It is the reason the recorder now
   keeps families whole.
2. **Prospective check of the language-model direction** on posts after the model's training cutoff, from the recorded
   Truth Social feed with the prompt held fixed. This is the only thing that removes the recall confound in Result 4. The
   line of work stops here otherwise.

## Live recorder

Everything above except Result 6 comes from the public trade archive. The recorder is separate and has so far produced
**no reported news-reaction number**.

- **What it records** (Polymarket international exchange, top-of-book via websocket, `recv_ns` at receipt, `conn_id`
  incremented on every reconnect): best bid and ask with sizes for a universe of 250 markets (top 200 by 24 h volume plus 50
  short-dated); since 2026-10-12 05:20 UTC also trades (price, size, side, exchange timestamp, fee rate), depth within 1, 2 and
  5 cents of mid, tick-size changes, and market metadata with reward and fee fields. News feeds: BLS/BEA schedules, Fed
  releases, SEC 8-K, crypto feeds, Truth Social (polled every 5 min), and 48 Bluesky accounts.
- **Where it runs:** a Windows desktop, separate from the development Mac, since 2026-10-10 20:09 UTC. The Mac recorded
  08:06–20:25 UTC on 10-10 before that.
- **Clock-offset correction:** the desktop clock was found to be about 1.33 s slow with the Windows Time service stopped, so
  every desktop `recv_ns` between 2026-10-10 20:09 and 2026-10-12 05:20 UTC carries an uncorrected error of roughly 1.3 s, to
  be stated wherever that span is used. From 05:32 UTC `clock.py` logs the NTP offset every minute to
  `data/clock_offset.jsonl` (offset +1.34 s then); analysis must apply `recv_ns + offset_s·1e9`. The Mac was +0.06 to
  +0.08 s. Results 1–5 and 7 use archive timestamps and are unaffected.
- **Staged widening:** a widening to 450 markets (adding whole families and the CPI/PPI events) is on hold. After a
  "slow consumer" socket close at 05:30:47 UTC, the depth calculation was moved off the per-message path and a heartbeat now
  logs event-loop lateness. Plan: stage 1 at `--cap 300` (250 plus 46 pinned CPI/PPI markets), watch the heartbeat through a
  full US session, then 450. Not run on Windows at the time of the last log entry.
- **Known gaps and polled windows:** a Mac sleep gap 14:58–19:17 UTC on 2026-10-10 (259 min); roughly 2–3 s socket gaps at
  each desktop restart (20:04 UTC 10-11, 05:20 UTC 10-12); 13 reconnects in 34.3 h (one slow-consumer close); three windows on
  10-11 (12:47:44, 19:40:30, 19:46:11 UTC, 66–78 s each) covered only by 1 Hz REST polling, which `gaps.py` does not flag and
  any timing measure must exclude; 10.5 % of overnight rows have an empty bid side (mostly one market) and have no mid. Windows
  spanning a reconnect are NaN'd by rule.
- **Legal position.** Kalshi is excluded: its Developer Agreement (v1.1 §3/§3.1) limits API use to the member's own trading
  and bars storing or sharing its data without written authorization. The recorded venue is Polymarket's international
  exchange, which US persons cannot trade on (close-only), so everything here is measurement and paper analysis. Polymarket's
  Terms of Use could not be read, so redistribution rights are unknown; Benzinga headlines are not redistributable and none
  appear in the results.

The first scheduled events inside the recording window are CPI (Wed 2026-10-14) and PPI (Thu 2026-10-15), 12:30 UTC.

## Reproduce

Python is `/opt/anaconda3/bin/python3`; archive downloads go to `data/archive/` (gitignored). Rules for each test are in
`research/*-rules.md` and `DECISIONS.md`; `ml_train.py test` refuses to run twice and `leadlag.py test` refuses to run with a dirty tree.

```
cd ~/Downloads/pmflow
P=/opt/anaconda3/bin/python3
# recorder, collector, feeds
$P -W ignore universe.py                       # refresh the universe (top-200 + short + pinned + family slices; --cap N limits total)
nohup caffeinate -i $P -W ignore record_polymarket.py > data/recorder.stdout 2>&1 &   # log: data/recorder.log
nohup caffeinate -i $P -W ignore collect.py --loop 15 > data/collect.log 2>&1 &       # also polls Truth Social every 5 min
nohup caffeinate -i $P -W ignore bluesky.py > data/bluesky.stdout 2>&1 &              # accounts in bluesky_accounts.txt
$P clock.py --loop 60                          # NTP offset -> data/clock_offset.jsonl
$P -W ignore map.py                            # headline -> markets (Haiku via claude -p; cap $0.50/run)
$P -W ignore run_reactions.py                  # live reactions + placebo -> data/reactions.parquet + summary
# archive results
$P archive_check.py                            # Result 1 (downloads ~130 MB daily files + 2 raw shards)
$P backtest_truth.py                           # Result 2 -> research/backtest-truth.md
$P replay_truth.py                             # Result 3
$P replay_llm.py                               # Result 4 main arm (model calls, cap $2; --no-calls replays the cache)
$P replay_controls.py                          # Result 4 controls B3 (--b3b for the forced-choice control)
pip install -r requirements-ml.txt
$P ml_fetch.py && $P ml_dataset.py             # Result 5 data
$P ml_train.py select && $P ml_train.py test   # Result 5 (test scores once)
python sets_check.py --tob <folder> --raw <events json> --out <outdir> [--fetch]   # Result 6
$P leadlag_fetch.py && $P leadlag_gamma.py && $P leadlag_map.py                    # Result 7 inputs
$P leadlag.py dev                              # then: $P leadlag.py test (once; needs a clean tree)
$P -m pytest -q                                # tests (test_ml.py skips without the model libraries)
```

Scheduled pass (CPI Wed 10-14, PPI Thu 10-15): `event_pass.py` maps window events and measures reactions against placebo.
Load once (runs 07:50 and 09:50 CDT daily):
```
cp ~/Downloads/pmflow/com.ayaan.pmflow.pass.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.ayaan.pmflow.pass.plist
```

## Mistakes and corrections

Kept visible on purpose; each is recorded in `DECISIONS.md`.

- **Weekday error.** I called 2026-10-10 a weekday; it is a Saturday. CPI is Wednesday 10-14, PPI Thursday 10-15 (the dates
  were right, the names wrong).
- **Overnight mapping was backfill.** Every directional mapping from the first night was feed backfill from before the
  recorder started, several plainly wrong; `map.py` now maps only events inside the recording window.
- **A stale-quote rule that blanked half the data.** 60 s staleness NaN'd 169 of 400 placebo windows; changed to 3,600 s
  before any real event was measured.
- **Mac sleep.** Closing the lid slept the recorder for 259 min; `caffeinate -i` does not prevent lid-close sleep. The
  recorder moved to the desktop.
- **Uncorrected recorder clock.** The desktop clock was ~1.33 s slow for about 33 hours before it was noticed; the span is
  uncorrectable and flagged above.
- **Recorder backoff never reset.** Reconnect counters accumulated over the process lifetime; fixed 2026-10-11.
- **Tracked data files broke pulls on the second machine.** `data/recorder.stdout` was tracked while the desktop held it open,
  and an upstream delete would have aborted its pull; it is now frozen, `data/summary.md` was untracked, and the rule is never
  `git commit -a`.
- **Universe selection cut families apart.** Ranking by volume left one complete family for Result 6; the universe now keeps
  families whole.
- **CPI-linked markets were not being recorded.** The dedicated September inflation and PPI events trade about $15k a day,
  so volume ranking never selected them, and the recorder measured CPI on Fed-decision markets only; they are now pinned.
- **Tick size assumed 0.01.** The median tick in the universe is 0.001. The pre-registered 0.01 threshold was kept as
  primary and a tick-based measure added as secondary.
- **My first readings of results, corrected by verifiers.** "Even following the first trade loses" (Result 3, the oracle arm
  is not an upper bound); the 17.3 vs 13.4 % move-frequency gap (Result 2, a placebo artifact); "0.016 AUC is the headline's
  contribution" (Result 5, it is market identity); "+4.0 before February looks like memorisation" (Result 4, one event);
  "the sibling result closes the question" (Result 7, quotes untested).
- **Control designs that could not detect anything.** The first memorisation controls let the model abstain (97–98 % did);
  the forced-choice control's agreement band was mis-specified, so its reading rule was not satisfied as written.
- **Test infrastructure.** `test_record.py` failed on Windows (path separator), `test_ml.py` failed to collect on the
  recording machine (missing libraries), and the first recorder rewrite re-wrote every day file on each flush; all fixed.
- **Unverified.** Result 6 was not independently verified, and the live recorder's tick-size path and Windows run of the
  newest code were not verified at the last log entry.

## Where things are

`DECISIONS.md` the dated log and authoritative statements; `research/` result files and pre-registered rule files; `paper/paper.md`
a draft covering Results 1 and 2 only; `TASKS.md` plan; `LABELS.md` fixed prompt for the headline mapper.
