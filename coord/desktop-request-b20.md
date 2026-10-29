# Request to the desktop pmflow session (from the Mac session, for Ayaan) — 2026-10-29

Ayaan approved this. Hard rules: DO NOT reboot, sleep or restart the PC; do not touch GPU jobs or other projects.
Ask the Mac session (not Ayaan) if anything is unclear.

1. Report recorder status: alive?, conn_id, markets recorded, which exclusive families are complete, gaps since
   2026-10-13 14:16 UTC, and why the universe went from 450 to 300 on 10-13.
2. Run `python sets_check.py --tob data/tob/polymarket --raw data/sets_gamma_events_raw.json --out data/sets_out_b20`
   on data from 2026-10-13 14:16:03 UTC on (rules: research/behavioral-rules.md "B20-forward").
   - Run it at BelowNormal priority at a quiet hour (not US daytime), watch the recorder heartbeat, and stop the
     analysis at once if late_ms p99 rises above 250 ms or any 1013 close appears. The recorder wins over the analysis.
   - Do not use --fetch unless the family map is missing; if so, one fetch at human pace.
3. Send back tables.md and the episode counts per family (B side: sum of bids > 1 and > 1 + fee, duration, $ size).
4. Do not change the universe or restart the recorder for this. If widening to whole families (450) looks safe,
   say so and why; the Mac session decides with Ayaan.
