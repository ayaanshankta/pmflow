# pmflow — do prediction markets lag the news?

Records top-of-book on non-sports Kalshi and Polymarket markets 24/7, timestamps news to the second, maps each headline to the
contracts it touches, and measures time-to-reprice and the move at 1/5/15/60 min against a placebo. Methodology ported from
`~/Downloads/newsflow` (verified). Paper only. Rules and pass bar: `DECISIONS.md`. Live plan: `TASKS.md`.

Results: (none yet)

## Recorder
```
/opt/anaconda3/bin/python3 universe.py                      # refresh data/universe_polymarket.parquet (daily)
nohup /opt/anaconda3/bin/python3 record_polymarket.py > data/recorder.stdout 2>&1 &   # 24/7; log in data/recorder.log
```
Rows: `data/tob/polymarket/{market_id}/date=YYYY-MM-DD.parquet`; resolved events: `data/resolved.jsonl`.
Tests: `python test_universe.py && python test_record.py`.
