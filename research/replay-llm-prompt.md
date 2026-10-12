# Fixed prompt for the LLM-direction arm (addendum B2)

Committed before any model call. `replay_llm.py` reads both blocks below verbatim from this file; do not edit after the first call.

Model: `claude -p --model haiku`, one call per (event, market) pair, no tools, no session, no other context.
The model sees only the post text and the market slug with hyphens turned into spaces. It is never given the post date, any price, or anything after the post.

System prompt (exact):
```
You read one social-media post and the title of one prediction market. Decide what the post, on its own, should do to the price of YES in that market right after it is published. Answer with exactly one word: up, down or none. Answer none unless the post clearly bears on the question. Give no explanation.
```

User message template (exact; `{post}` = post text, `{question}` = slug with `-` replaced by a space):
```
Post: {post}
Market: {question}
Answer (up, down or none):
```

Parsing: the reply, lower-cased with surrounding punctuation/whitespace stripped, must be exactly `up`, `down` or `none`. Anything else counts as a parse failure; the call is retried once, and if it fails again the pair gets no direction (counted as a failure, not as `none`).
