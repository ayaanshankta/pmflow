# pmflow — do prediction markets lag the news?

Records top-of-book on the 200 most-active non-sports Polymarket markets 24/7, timestamps news to the second, maps each
headline to the contracts it touches, and measures time-to-reprice and the move at 1/5/15/60 min against a placebo.
Methodology ported from `~/Downloads/newsflow` (verified). Paper only. Rules and pass bar: `DECISIONS.md`. Plan: `TASKS.md`.
Legal: Kalshi is excluded until written permission (its Developer Agreement bars storing/sharing API data; draft request in
`research/kalshi-permission-email.md`). Polymarket data is public/on-chain; its Terms of Use are still to be read.

## Result so far (first night + morning, 2026-10-10 03:06–09:15 CDT)

**No news-reaction number yet.** 375k quote rows recorded over 6 h on 200 markets, but only 3 news events (crypto articles) fell
inside the window and the mapper judged none of them to touch a recorded market. The first measurable events are Tuesday's CPI
and Wednesday's PPI (12:30 UTC). What the night did produce:

- **Recorder (verified independently):** 200 markets, 270,947 rows 08:06–12:12 UTC (~1,000 rows/min), timestamps monotone,
  0 duplicates, 0 empty minutes, 4 reconnects with gaps of 0.5–8 s, mids within 0.0005 of the live API. Flags: 10.5 % of rows
  have an empty bid side (26,602 of them one market, "Bitcoin $96,000 Oct 5–11", which therefore has no mid and is excluded);
  34 rows (0.013 %) briefly crossed by ≤ 0.007.
- **Overnight liveness (verified; placebo, 40 most-active markets × 10 random times, 08:10–11:50 UTC):** at a random moment
  only **~10 %** of markets moved by ≥ 1 tick (0.01) within the next 60 min (ours 11 %, verifier 10.1 ± 1.4 over 20 seeds);
  among movers the median wait was **~10–15 min** (noisy: ~40 movers per seed). Mean |move| at 15 min: 0.0013 probability
  points (n ≈ 309). Windows spanning a reconnect are NaN'd, so ~10 % is a lower bound (17 % among reconnect-free windows).
  Overnight these markets are mostly static; the lag question can only be answered around US-hours events.
- **Events collected:** 184 (BLS/BEA schedules, Fed press releases + speeches, SEC 8-K filings, 3 crypto feeds); the first
  scheduled events inside the window are **CPI Tue Oct 14 and PPI Wed Oct 15, both 12:30 UTC**.
- **Mapping:** 86 LLM calls (Haiku), 100 % parsed, $0.04 — but every directional mapping was feed backfill from before the
  recorder started (several plainly wrong, e.g. January recaps mapped to Oct-10 BTC markets at confidence 0.1–0.3). They are
  excluded; `map.py` now only maps events inside the recording window. **Directional events inside the window so far: 0.**
  Scheduled CPI/PPI map to 5 markets each with direction "none" (correct before the print). BLS release *time* 08:30 ET is
  verified; the Oct 14 *date* could not be confirmed from the live BLS page.
- **Rule change before any real event was measured:** a standing quote is the price until changed (STALE 60 s → 3600 s);
  see DECISIONS.

What decides the question: the Tuesday/Wednesday prints and any Fed/political headline during US hours. The pre-registered
pass bar (DECISIONS) is unchanged.

## Repro
```
cd ~/Downloads/pmflow
/opt/anaconda3/bin/python3 -W ignore universe.py                                   # refresh the 200-market universe
nohup caffeinate -i /opt/anaconda3/bin/python3 -W ignore record_polymarket.py > data/recorder.stdout 2>&1 &   # log: data/recorder.log
nohup caffeinate -i /opt/anaconda3/bin/python3 -W ignore collect.py --loop 15 > data/collect.log 2>&1 &
/opt/anaconda3/bin/python3 -W ignore map.py            # headline -> markets (Haiku via claude -p; cap $0.50/run)
/opt/anaconda3/bin/python3 -W ignore run_reactions.py  # reactions + placebo -> data/reactions.parquet + summary
/opt/anaconda3/bin/python3 -m pytest -q                # tests
```

## Scheduled pass (CPI Tue 10-14, PPI Wed 10-15, 8:30 ET)
`event_pass.py` maps window events, measures reactions vs placebo, writes `data/summary.md`. Load the launchd job once
(runs 07:50 and 09:50 CDT daily, i.e. 20 min and 2 h 20 min after the 8:30 ET prints):
```
cp ~/Downloads/pmflow/com.ayaan.pmflow.pass.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.ayaan.pmflow.pass.plist
```
