# pmflow — do prediction markets lag the news?

Records top-of-book on non-sports Kalshi and Polymarket markets 24/7, timestamps news to the second, maps each headline to the
contracts it touches, and measures time-to-reprice and the move at 1/5/15/60 min against a placebo. Methodology ported from
`~/Downloads/newsflow` (verified). Paper only. Rules and pass bar: `DECISIONS.md`. Live plan: `TASKS.md`.

Results: (none yet)

## collect.py (task 5) — events -> data/events.parquet
Columns: event_id, source, t0_utc, first_seen_utc, title, url, kind (scheduled|release|filing|article). Append-only, dedup by event_id.
Sources: BLS + BEA ICS (ET->UTC, next 14 days, re-polled every 10 min), Fed RSS x3, SEC 8-K Atom, Cointelegraph/Decrypt/The Block RSS.
`first_seen_utc` of rows from the very first poll is the poll time, not a real arrival time (backlog) — only rows first seen
at t0 + small lag in later polls are valid for lag questions. Fed pubDate is minute precision.
```
python3 collect.py --once
cd ~/Downloads/pmflow && nohup /opt/anaconda3/bin/python3 collect.py --loop 15 > data/collect.log 2>&1 &
python3 -m pytest test_collect.py
```
## Recorder
```
/opt/anaconda3/bin/python3 universe.py                      # refresh data/universe_polymarket.parquet (daily)
nohup /opt/anaconda3/bin/python3 record_polymarket.py > data/recorder.stdout 2>&1 &   # 24/7; log in data/recorder.log
```
Rows: `data/tob/polymarket/{market_id}/date=YYYY-MM-DD.parquet`; resolved events: `data/resolved.jsonl`.
Tests: `python test_universe.py && python test_record.py`.
