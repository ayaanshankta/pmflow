# Fixed prompts for the memorisation controls (addendum B3)

Committed before any control model call. The control script reads the blocks below verbatim from this file; do not edit after the first call.

Same model alias as the B2 arm (`claude -p --model haiku`), one call per (event, market) pair, no tools, no session, no other context. The same 677 liquid event pairs as B2. Answers are cached in their own files (`data/controls_c1_dirs.jsonl`, `data/controls_c2_dirs.jsonl`).

## Control 1: no post (market title only)
The model sees only the market slug with hyphens turned into spaces. It is never given a post, a date, or a price. Wording is the B2 prompt with the post removed and nothing else changed except the question being "which way will the price move next".

System prompt (exact):
```
You read the title of one prediction market. Decide which way the price of YES in that market will move next. Answer with exactly one word: up, down or none. Answer none unless the title clearly bears on the direction. Give no explanation.
```

User message template (exact; `{question}` = slug with `-` replaced by a space):
```
Market: {question}
Answer (up, down or none):
```

## Control 2: wrong post
Uses the B2 prompt in `research/replay-llm-prompt.md` unchanged (system prompt and user template). Only the `{post}` text differs: for each of the 677 pairs, the post text of another event is substituted. The substitute is drawn with `numpy.random.RandomState(0)`, one draw per pair, taking pairs in the order of the B2 liquid-pair table, uniformly from the events (of the 400 selected events) whose post time is at least 7 days (604800 s) from the pair's own event's post time. The pair's own event is never eligible. The market slug is the pair's own.

## Parsing, retry, cap
Identical to B2: reply must be exactly `up`, `down` or `none`; one retry; a double failure is a failure, not `none`. Combined spend cap for both controls: $1.

## Control 3 (addendum B3b): forced choice, no post
Appended before any call for this control; the text above is unchanged. The model sees only the market slug with hyphens turned into spaces; no post, date or price. It has no "none" option. Same model alias, same 677 liquid pairs, one call per pair, cached in `data/controls_c3_dirs.jsonl`, spend cap $0.50. A reply that is not exactly `up` or `down` (including `none`) is a parse failure: retried once, and if it fails again the pair is a failure and is excluded, never coerced.

System prompt (exact):
```
You read the title of one prediction market. Decide which way the price of YES in that market will move next. Answer with exactly one word: up or down. You must choose one. Give no explanation.
```

User message template (exact; `{question}` = slug with `-` replaced by a space):
```
Market: {question}
Answer (up or down):
```
