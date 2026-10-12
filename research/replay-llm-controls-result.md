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
