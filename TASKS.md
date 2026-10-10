# TASKS — pmflow

Goal: measure how fast and how far non-sports Kalshi/Polymarket markets reprice after news, vs placebo. Paper only. Rules: DECISIONS.md.

| # | Task | Owner | Status | Done when (pass bar) |
|---|------|-------|--------|----------------------|
| 0 | Scaffold: repo, DECISIONS, TASKS, reaction.py copied, private remote | orchestrator | done | this file committed; `gh repo view` private |
| 1 | API + legal scoping | researcher pm-api-scope (Opus) | done (research/pm-api-scope.md) | report with primary URLs and quoted clauses |
| 2 | `universe.py`: list non-sports, active, book-enabled markets on Polymarket (and Kalshi); committed exclusion rules | builder | todo | prints counts per category; `test_universe.py` passes; sports excluded by rule |
| 3 | `record_polymarket.py`: 24/7 top-of-book recorder (websocket, REST fallback) per DECISIONS schema | builder | todo | runs >= 10 min, writes parquet, reconnects with new conn_id; `test_record.py` on a fake stream |
| 4 | `record_kalshi.py`: same for Kalshi non-sports | — | BLOCKED: Developer Agreement §3.1 (see DECISIONS); needs written permission | same bar |
| 5 | `collect.py`: news with second-precision timestamps | builder-collect (Sonnet) | done (merged; 4 tests; loop running from ~/Downloads/pmflow) | `data/events.parquet`; 10 rows spot-checked vs source |
| 6 | `reaction.py` adapted: load from pmflow tob, delta_p, time-to-reprice; placebo | builder-reaction (Sonnet) | done (2c6b7bc, merged; 7 tests) | `test_reaction.py` passes on synthetic known answers incl. time-to-reprice |
| 7 | `LABELS.md` + `map.py`: headline -> market ids + direction (LLM) + keyword baseline | builder | todo | 10-headline smoke test: parse rate, cost |
| 8 | First run on overnight data + placebo; summary table with CIs | builder | todo | `data/summary.md`; n per cell; honest verdict vs pass bar |
| 9 | Verify 6 and 8 independently | verifier | todo | numbers within tolerance; no future leak |
| 10 | Recorder kept alive overnight (caffeinate) and logged | orchestrator | todo | `data/recorder.log` shows continuous rows; row counts per hour |
| 11 | Draft Kalshi research-permission email for Ayaan to send | orchestrator | done | `research/kalshi-permission-email.md`, ready to paste |
