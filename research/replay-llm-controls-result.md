# Memorisation controls for the LLM-direction arm (addendum B3)

Rules: `research/ml-rules.md` B3 (committed before either control ran). Prompts: `research/replay-llm-controls.md` (commit d68eff3, 00:36 CDT, before the first control call). Code: `replay_controls.py` (+ `test_replay_controls.py`), reusing `replay_llm.py` / `replay_truth.py` unchanged. Same 677 liquid event pairs, same engine and placebo set, same bootstrap (1,000 event-cluster draws, RandomState(0)), same model alias `haiku`. Raw answers: `data/controls_c1_dirs.jsonl`, `data/controls_c2_dirs.jsonl` (gitignored; caches, so a rerun makes no calls). Numbers: `results/replay_controls_summary.json`.

## Conclusion under the B3 rule
At Δ = 10 s, both controls have gross event-minus-placebo intervals that include 0 (C1 -0.07 [-1.39, +1.28]; C2 +0.05 [-1.22, +1.43]) and point estimates below +0.84. **The second description applies: B2 is "consistent with reading the post; not yet confirmed out of sample".** B2 is still not a pass; the profit bar already failed.

Read this with its main caveat: **the controls have almost no trades** (11 and 8 at 10 s), because the model answered "none" for 97 to 98 % of pairs. Their intervals are about ±1.3 points wide, so they cannot rule out an effect as large as the rule's +0.84 threshold. The rule is met literally, but the test has little power.

## Counts and spend
| | B2 (original) | C1 no post | C2 wrong post |
|---|---|---|---|
| up / down / none | 192 / 141 / 344 | 10 / 8 / 659 | 4 / 8 / 665 |
| parse failures, call errors, uncalled | 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| spend | $0.171 | $0.056 | $0.040 (controls total $0.096 of the $1 cap) |
| served by | mostly claude-haiku-5-5 | claude-haiku-5-5 (677) | claude-haiku-5-5 (677) |
| event trades, first entry, 2 / 10 / 30 s | 214 / 226 / 235 | 11 / 11 / 11 | 8 / 8 / 8 |
| placebo trades, 2 / 10 / 30 s | 2940 / 2952 / 2896 | 125 / 121 / 120 | 79 / 78 / 78 |

## Event minus placebo, gross (0 % fee), first-trade entry, points, 95 % event-cluster CI
| Δ s | B2 | C1 no post | C2 wrong post |
|---|---|---|---|
| 2 | +1.88 [+0.40, +3.77] | -0.04 [-1.37, +1.32] | +0.01 [-1.22, +1.35] |
| 10 | +1.67 [+0.35, +3.49] | -0.07 [-1.39, +1.28] | +0.05 [-1.22, +1.43] |
| 30 | +1.40 [+0.32, +2.82] | -0.16 [-1.48, +1.01] | -0.05 [-1.31, +1.16] |

B2 values reproduce the committed result exactly. Event-only mean PnL: C1 -0.18 / -0.20 / -0.29, C2 +0.09 / +0.09 / -0.14 (B2 +1.90 / +1.70 / +1.42).

## Agreement with B2 (same non-none direction)
| | share of all 677 pairs | share of the 333 pairs where B2 is non-none |
|---|---|---|
| C1 no post | 0.7 % (5 pairs) | 1.5 % |
| C2 wrong post | 0.1 % (1 pair) | 0.3 % |

## What this does and does not show
- Without the post, or with the wrong post, the model almost never commits to a direction. B2's 333 directions therefore depend on the specific post being paired with the market, which is what reading would predict and what pure recall from the market title would not. That is the clearest result here, and it does not depend on the thin trade counts.
- It does not show the model read the post rather than remembered the post's outcome. The right post may itself cue recall of what followed that specific post; neither control removes that. Only posts after the model's training cutoff do.
- The 11 and 8 control trades cannot detect a small leak; the intervals are as wide as the effect being tested for.
- Controls use one call per pair, so run-to-run noise is unmeasured. Haiku alias drift is unchanged from B2 (3 of B2's calls were served by an older haiku; all control calls were by claude-haiku-5-5).

## Remaining unknowns
Out-of-sample posts after the model's cutoff (the collector keeps recording); whether the model's directions are stable across repeated calls; spread and impact on the trades that carry the B2 mean.

---

# Addendum B3b: forced-choice, no-post control

Rules: `research/ml-rules.md` B3b. Prompt: appended to `research/replay-llm-controls.md` (commit afa8d1e, 01:06 CDT, before the first call). Code: `replay_controls.py --b3b`. Same 677 liquid pairs, model alias, engine and bootstrap. Cache `data/controls_c3_dirs.jsonl` (gitignored), numbers `results/replay_controls_b3b_summary.json`.

## Counts
| | |
|---|---|
| pairs / parse failures (excluded, never coerced) | 677 / 0 |
| up / down | 80 / 597 (up share 11.8 %) |
| up share on the 333 pairs where B2 gave a direction | 9.3 % (B2's own up share there: 57.7 %) |
| spend | $0.050 of the $0.50 cap |
| served by | claude-haiku-5-5 on all 677 |
| event trades, first entry, 2 / 10 / 30 s: set (i) 333 pairs | 214 / 226 / 235 (same trades as B2) |
| event trades, all 677 | 437 / 439 / 453 |

## Event minus placebo, gross (0 % fee), first-trade entry, points, 95 % event-cluster CI
| Δ s | B2 | forced choice, set (i): 333 pairs | forced choice, set (ii): all 677 |
|---|---|---|---|
| 2 | +1.88 [+0.40, +3.77] | -0.43 [-1.92, +0.75] | -0.29 [-1.04, +0.29] |
| 10 | +1.67 [+0.35, +3.49] | -0.45 [-1.86, +0.68] | -0.31 [-1.04, +0.28] |
| 30 | +1.40 [+0.32, +2.82] | -0.24 [-1.51, +0.75] | -0.21 [-0.90, +0.33] |

Placebo trades: 2,940 / 2,952 / 2,896 (set i), 5,993 / 5,987 / 5,922 (set ii).

## Agreement with B2's direction on the 333 pairs
**43.8 % (146 of 333)**, 50 % = unrelated. Because the forced guess is 91 % "down" on these pairs and B2 is 58 % "up", independent answers would agree about 0.577 x 0.093 + 0.423 x 0.907 = 43.7 %. So the observed figure is what unrelatedness predicts given the skew; it is not evidence that the title guess is the opposite of B2.

## Reading rule on set (i), Δ = 10 s
- Description 1 (title-only guess recovers part of B2's edge: interval excludes 0 or estimate >= +0.84): **does not apply**. Estimate -0.45, interval [-1.86, +0.68].
- Description 2 (estimate < +0.84, interval includes 0, AND agreement within 45-55 %): its first two conditions hold; **the agreement condition is not met as written (43.8 %, outside 45-55 %)**. Strictly, neither description is satisfied.
- My reading, stated as a judgement and not as the rule: the 43.8 % is the independence value for these skewed marginals (above), the 95 % interval for agreement under independence at n = 333 is roughly 33 to 55 % around that value, and the forced guess has no positive edge. I read it as "B2's directions are not explained by the title alone", but the written band was missed and the rule's author should decide whether to accept that.

## What this changes and what it does not
- The title-only guess carries no positive edge: the point estimates are negative in both sets, and the 333-pair interval is again about ±1.3 points wide, now with 214-235 trades (comparable to B2's), so it is a real test of an effect of B2's size. An effect of +1.4 or more is excluded; one of +0.7 is not.
- The model's forced title-only guess is heavily "down" (89 %), so a market-level bias toward "down" exists but did not pay.
- Unchanged: the correct post may cue recall of what followed that specific post; only posts after the model's training cutoff remove that.
