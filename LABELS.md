# LABELS — event → Polymarket market mapping (fixed before any real event is mapped; DECISIONS "Mapping")

Written 2026-10-10 ~03:25 CDT, before `map.py` was run on any event. Changing anything below = new numbered rule in DECISIONS.md.
Input is headline text only (title, source, kind, t0). The mapper never sees prices or returns.

## Output schema
One JSON array, nothing else. At most 5 elements, `[]` if no listed market is plausibly affected:

    [{"market_id": "m7", "direction": "up" | "down" | "none", "confidence": 0.0-1.0}]

- `market_id`: the short id shown in the candidate list (`m1`..`mN`); map.py resolves it to the real Polymarket market_id.
  Unknown or duplicated ids make the whole reply invalid.
- **`up` = the probability of YES in that market should rise** on this news (not "the price of the underlying rises").
  `down` = YES probability should fall. `none` = market is related but the news gives no directional information.
- `confidence`: model's probability that the stated direction is right (for `none`: that the market is related at all).

## System prompt (exact):
```
You map one news headline to prediction markets it could move. You are given the headline and a numbered list of candidate markets (id, question). Return ONLY a JSON array of at most 5 objects {"market_id": <id from the list>, "direction": "up"|"down"|"none", "confidence": <0..1>}, or [] if no listed market is plausibly affected. "up" means the probability that the market resolves YES should rise because of this headline; "down" means it should fall; "none" means related but no directional information. Judge only from the headline and the question text. Use only ids from the list. Scheduled data releases (CPI, PPI, jobs) without a result in the headline are "none". Routine items (bank approvals, enforcement actions, unrelated company filings) map to []. No prose, no code fences.
```

User message (exact format):
```
source: <source>
kind: <kind>
t0_utc: <ISO8601>
headline: <title>
markets:
m1 | <question>
m2 | <question>
...
```
Model: `claude -p --model haiku --output-format json`, tools off, one retry on an invalid reply, then the event is left unmapped
(retried next run). Candidate list = keyword-lexicon matches, at most 40, ranked by volume24hr.
If the lexicon matches nothing, no call is made and the event is recorded as `[]`.

## Keyword baseline (`LEXICON` in map.py, committed)
Event theme → market-question keywords. An event matches a theme if its title matches the event regex; candidates are universe
questions matching the theme's market regex (top 5 by volume24hr kept as the baseline mapping).

| theme | event keywords | market keywords |
|---|---|---|
| fed | fed, fomc, federal reserve, powell, warsh, rate cut/hike, interest rate | fed ... rate |
| inflation | cpi, consumer/producer price, inflation, ppi, pce, real earnings | fed ... rate |
| bitcoin | bitcoin, btc, crypto, etf, sec, tether, stablecoin | bitcoin |
| ethereum | ethereum, eth, ether, starknet | ethereum |
| oil | oil, crude, opec, wti | wti, crude |
| iran | iran, hormuz, kharg, blockade, bessent | iran, hormuz, kharg, blockade |
| ukraine | ukraine, zelensky, putin, russia, nato | ukraine, putin, russia, zelensky, nato |
| midterms | midterm, senate, house, republican, democrat | midterm, senate, house |
| people | surnames of candidates in the universe (lula, bolsonaro, le pen, vance, rubio, netanyahu, ...) | same surname |

Direction rules (baseline):
- Scheduled releases (`kind` = scheduled, or an inflation-theme headline) are `none` unless the headline carries a surprise word:
  higher / hotter / beats / rises (hawkish, +) or lower / cooler / misses / falls (dovish, −).
  hawkish → "decrease" Fed markets `down`, "increase" Fed markets `up`; dovish → the reverse; "no change" markets stay `none`.
- Fed statements: "cut/lower/reduce ... rate" → dovish; "raise/hike/increase ... rate" → hawkish; otherwise `none`.
- Crypto / oil / Iran: positive words (surge, rally, jump, rebound, approve, deal, ...) → `up`, negative words (plunge, crash, hack,
  ban, sue, strike, attack, ...) → `down`, both or neither → `none`. Markets phrased "dip"/"(LOW)"/"between" flip or void:
  "dip"/"(LOW)" take the opposite sign; "between" is `none`. For Iran, "ceasefire continues" / "blockade ends" / "reopen" markets follow the sign.
- Politics / people: always `none` (relatedness only).
- Keyword confidence is fixed at 0.3.

## Storage
`data/mapping.parquet`: event_id, market_id, direction, confidence, method ∈ {llm, keyword}, mapped_utc.
An event with no affected market is stored as one row with market_id = null, direction = "none", confidence = 0 (marks it mapped).
Downstream analysis uses rows with market_id not null and direction != "none". Rerun skips events already mapped under the same method.
