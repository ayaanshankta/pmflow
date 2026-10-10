# pmflow — do prediction markets lag the news?

Records top-of-book on the 200 most-active non-sports Polymarket markets 24/7, timestamps news to the second, maps each
headline to the contracts it touches, and measures time-to-reprice and the move at 1/5/15/60 min against a placebo.
Methodology ported from `~/Downloads/newsflow` (verified). Paper only. Rules and pass bar: `DECISIONS.md`. Plan: `TASKS.md`.
Legal: Kalshi is excluded until written permission (its Developer Agreement bars storing/sharing API data; draft request in
`research/kalshi-permission-email.md`). Polymarket data is public/on-chain; its Terms of Use are still to be read.

## Result so far (first night, 2026-10-10 03:06–07:30 CDT)

**No news-reaction number yet: no mapped news event fell inside the recording window overnight.** What the night did produce:

- **Recorder:** 200 markets, ~264k top-of-book rows in the first 4 h (~800–1,000 rows/min), 3 server-side disconnects
  (reconnected within seconds, new `conn_id` each time). (verification pending)
- **Overnight liveness (placebo, 40 most-active markets × 10 random times, 08:10–11:50 UTC):** at a random moment only
  **11 %** of markets moved by ≥ 1 tick (0.01) within the next 60 min; among those that moved, the median wait was **663 s**.
  Mean |move| at 15 min: 0.0013 probability points (n = 309 windows). Overnight these markets are mostly static, so the
  lag question can only be answered around US-hours events. (verification pending)
- **Events collected:** 184 (BLS/BEA schedules, Fed press releases + speeches, SEC 8-K filings, 3 crypto feeds); the first
  scheduled events inside the window are **CPI Tue Oct 14 and PPI Wed Oct 15, both 12:30 UTC**.
- **Mapping:** 86 LLM calls (Haiku), 100 % parsed, $0.04; most crypto headlines judged unrelated to the 200-market universe;
  scheduled CPI/PPI map to 5 markets each with direction "none" (correct before the print).
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
