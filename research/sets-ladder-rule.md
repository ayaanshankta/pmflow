# C1 family map and ladder rule (written 2026-10-12, before any price was read for C1)

Rules: research/structure-rules.md blob 1582327e1f20. Code: families.py (the docstring is the rule). Raw Gamma events: data/sets_gamma_events_raw.json
(sha256 prefix 40c6f89ddeb1d58e; 200 recorded markets -> 71 events; fetched 2026-10-12, two days after the recording).

- Exclusive = event with negRisk=true. Required members = every market in the event except those already closed with YES = 0 before 2026-10-10 08:06 UTC. A market with no book still counts, so such a family is partial.
- Ladder = non-negRisk event; markets grouped by question template (dates and numbers masked). One thing may vary: deadline ("by" -> later is weaker; "through" -> earlier is weaker) or threshold ("(HIGH)"/up -> lower is weaker; "(LOW)"/down -> higher is weaker). Brackets, two varying things, or unknown direction are dropped and counted.
- Equal claims (duplicate listings) share a rank and are tested both ways. A ladder is complete only if every market of the group is recorded; any recorded pair is still an exact test.
- Fee rate per market = Gamma feeSchedule.rate where present, else 0.04.
- Changes made after seeing the family map (no prices): deadline ladders may have 0 numbers; date masking includes day ranges; explicit (LOW)/(HIGH)/arrow markers beat verbs; ties allowed; markets without a book count as required.
