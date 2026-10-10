# DECISIONS — pmflow (prediction-market news reaction)

Started 2026-10-10 by the neurotutor orchestrator on Ayaan's instruction. Sibling of ~/Downloads/newsflow; reuses its verified
reaction measurement (reaction.py, test_reaction.py copied at newsflow b4f8f31). Paper only. No trading, no signals sold.

## Pre-registered rules (written before any real event is measured)
- **Universe:** Polymarket + Kalshi markets that are active, order-book enabled, and NOT sports (exclude by category/tag/series;
  the exclusion list is written in universe.py and committed before recording starts). Refresh the universe daily; markets created
  mid-run are added at the next refresh.
- **Recording:** best bid, best ask, sizes at the top, on every change (websocket) or at <= 1 s polling; `recv_ns` = UTC epoch ns
  at receipt; `conn_id` increments on every (re)connect; one parquet per venue/market/UTC-day:
  `data/tob/{venue}/{market_id}/date=YYYY-MM-DD.parquet` with columns recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz.
  Prices in probability units [0, 1] (Kalshi cents / 100).
- **Events:** news items with publish time to the second (UTC). Sources and their timestamp field are listed in collect.py.
  Scheduled releases (BLS, BEA, Fed) use the official schedule time as t0.
- **Mapping:** an LLM (cheapest that passes a 10-headline smoke test) maps each headline to a list of affected market ids with a
  direction (up/down/none) and confidence; prompt fixed in LABELS.md before any reaction is computed. Keyword baseline kept.
- **Reaction windows:** as newsflow (DECISIONS "Reaction windows"): mid0 = last quote at or before t0 (NaN if > 60 s old);
  horizons 1/5/15/60 min; NaN across a conn_id change. Because prices are probabilities, the primary measure is
  **delta_p = mid(t0+h) - mid0 in probability points**, not log return. Spread, update rate and vol pre/post as newsflow.
- **Time-to-reprice:** seconds from t0 to the first quote whose mid differs from mid0 by >= 1 tick (0.01); NaN if none within 60 min.
- **Placebo:** uniform random UTC times per market over the same dates, excluding the first and last 60 min of each day, matched by
  day type (weekday/weekend); seeded generator; >= 20 placebo times per real event.
- **Pass bar for "a lag exists that is worth measuring/selling":** over mapped (direction != none) events,
  (1) median time-to-reprice > 60 s, AND (2) |delta_p| at 15 min exceeds the placebo level with a 95 % bootstrap CI excluding 0.
  If markets reprice within seconds, report that as the result; it is still the study.
- **Honesty:** rules above are not changed after real events are measured; any change is a new numbered rule here with the date.
- **Legal:** recording public data for a study. No redistribution of Kalshi data until its Developer Agreement is read verbatim
  (researcher pm-api-scope, 2026-10-10). Polymarket data is public/on-chain.

## Choices and bugs (append-only)
- 2026-10-10: `websockets` not installed in /opt/anaconda3 python; builders may `pip install websockets` or use REST polling.
- 2026-10-10: Kalshi public REST answered without a key (markets list, orderbook); first market hit was sports with an empty book.
  Polymarket gamma + CLOB public endpoints answered without a key.

## Mistakes
(none yet)
- 2026-10-10: newsflow lead confirmed reaction.py unchanged since d6db4d8 (vol_pre load window t0-16 min) and "Reaction windows" unchanged; newsflow tree clean at 40d3253. Builders/verifiers run on Sonnet (Ayaan: usage limits); researchers on Opus.
- 2026-10-10 (pm-api-scope): Kalshi Developer Agreement v1.1 §3/§3.1 limit API use to the member's own trading and bar storing/sharing data without written authorization; §6.4 bars public statements without approval. DECISION: tonight is POLYMARKET-ONLY. No Kalshi recording (REST or websocket) until Ayaan has written permission from Kalshi; task 4 blocked; a permission-request email is drafted for him instead.
- 2026-10-10 02:55 CDT: Polymarket Terms of Use could not be read (client-rendered; empty accessibility tree in Chrome). Redistribution rights unknown; recording for a private study proceeds; selling/publishing waits on reading the ToS. Kalshi blocked (above).
- Usage credits expected to lapse ~03:20 CDT and reset ~07:00; one-shot wake-ups set for 07:06 and 07:39 CDT to resume.
- 2026-10-10 (task 6, pm/reaction 2c6b7bc, merged): deviations from "as newsflow" accepted as rules — spread = ask − bid in probability points (relative spread explodes near 0/1); vol = std of 1 s mid changes in points (log returns meaningless near 0); placebo seeded per event (seed*1_000_003 + index); placebo dates = dates with a tob file for that market. Tests: 7 passed.
