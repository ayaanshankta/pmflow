## F1 forward paper test (2026-10-29, before any forward outcome is known): "nothing ever happens" in binary event markets
- Source: open exploration on the archive (DECISIONS 2026-10-29). Binary non-sports non-crypto markets, bought No at
  the next day's first fill after their first $1k day: +9.1% (2023-24), +11.3% (2025), +13.9% (2026 Jan-Apr) per trade,
  but the top 1% of trades give 72-87% of the return (rare collapses of 90-95% favourites); trimmed mean +1-4%, not
  significant. Calibration shows Yes overpriced by ~3-7 pts at every price level. 2025-26 was seen during exploration,
  so only forward data can confirm.
- Rule (forward_no.py): daily Gamma scan; binary (Yes/No), not neg-risk, not sports (universe.is_sports + Gamma sports
  tags), not crypto/airdrop (regex in forward_no.py), not up-or-down; volume24hr >= $1,000; Yes best bid in
  [0.05, 0.95]. Entry once per market at the first qualifying scan, price = live No ask (1 - Yes best bid). $1 notional
  each, held to resolution. Fees ignored (most such markets have none; report if not).
- The first scan (2026-10-29 19:55 UTC, 198 markets already liquid) is a backlog: data/forward/f1_backlog_2026-10-29.csv,
  reported separately, not in the confirmatory set (those markets are not at their first liquid day).
- Evaluate once at 300 settled confirmatory entries or on 2027-01-31, whichever is first.
  Pass: mean return > 0 with a 95% CI clustered by resolution week excluding 0, AND trimmed (top 1% removed) mean > 0.
  Also report: clustered by event (slug template), the share of return from the top 1%, and by price bin.
## F2 forward paper test (2026-10-30, before any forward outcome is known): long-dated deadline markets overpriced
- Source: open exploration on daily bars (DECISIONS 2026-10-30; hunt.log, ~95 cells this pass). Binary non-sports
  non-crypto markets whose slug says "by"/"before"/"in 20xx", >= 30 days to scheduled close, Yes 0.50-0.95 at the next
  open after a $1k day, bought No +1c, held to resolution: edge +13 pts [+9, +17] (cluster = event), return +44%,
  trimmed top 1% +32%, n = 733; positive every year 2023-2026, every price band, with and without war/geopolitics.
  First-liquid-day version (what the scanner does): +12 pts [+7, +16], n = 523. Clustered by resolution week the
  return CI includes 0 (-10% .. +85%): many markets share deadlines. Selected post hoc from many cells, so only
  forward data counts.
- Rule: the F1 rows (data/forward/f1_entries.csv and every f1_backlog*.csv, deduplicated by condition_id, earliest
  row kept) whose slug matches `-by-|-before-|-in-20\d\d`, with end_date - entered_utc >= 30 days and Yes bid in
  [0.50, 0.95). Return = No value / No ask - 1, held to resolution, no fees. Backlog rows are included (entered
  2026-10-29, outcomes unknown then; the archive cell holds on any qualifying day, n = 733) and also reported apart.
- Evaluate once at 100 settled rows or on 2027-06-30, whichever is first (`python forward_no.py f2`).
  Pass: mean return > 0 with a 95% CI clustered by event (slug with dates/numbers stripped, first 4 words) excluding 0,
  AND point mean > 0 when clustered by resolution week, AND trimmed (top 1% removed) mean > 0.
  Also report: edge in points (No value - No ask), by price band, backlog vs confirmatory.
