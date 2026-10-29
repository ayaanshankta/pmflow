# B1/B2/B4/B5 + S1 result (test run once, 2026-10-29; rules: research/behavioral-rules.md; frozen choice: DECISIONS.md, commit 8b50fd5)

**Verdict.**
- **Hugo's thin-market "Yes" premium: NO.**
- **A general Yes premium: YES, about +1.6 pts.** It is the same in thin and thick markets.
- **The fade-Yes strategy passes as pre-registered on paper, but most of it does not survive at a price you could
  actually trade.**
- **The remaining candidate is binary (non-neg-risk) markets only.** It is post-hoc and tiny in capacity, so it needs
  a fresh out-of-sample test before anyone believes it.

## Pre-registered results, TEST = snapshots 2025-01-06 .. 2026-03-30 (363,885 snapshots, 133,289 markets)

**B1 calibration**
- Logit slope 0.99 per snapshot, 0.95 with one snapshot per market: close to calibrated.
- The outcome-1 ("Yes") side is slightly dear across most price bins, by 1–5 pts:
  - 10–20¢ bin: price 0.145 vs win rate 0.112.
  - 90–95¢ bin: price 0.925 vs win rate 0.870.

**B2 (PRIMARY), price-bin-adjusted Yes premium, Yes/No markets**

| Volume tercile | Premium | 95% CI |
|---|---|---|
| Low | +0.0162 | [+0.0138, +0.0186] |
| Mid | +0.0155 | [+0.0106, +0.0200] |
| High | +0.0173 | [+0.0105, +0.0238] |
| **Low − high** | **−0.0011** | **[−0.0080, +0.0061]** |

- The pass bar needs low > high. **Fails.**
- Event clustering gives the same answer. Dev (2023–24) agreed: low − high +0.004 [−0.012, +0.021].

**B4 deadline markets (`-by-`/`-before-`) vs others:**
- Difference +0.002 [−0.006, +0.010].
- No base-rate-neglect effect.

**B5 after a ≥10-pt move in 24 h (real VWAP prices only):**
- The signed premium is −0.014 [−0.021, −0.007]. Moves *under*-shoot slightly (mild momentum), the opposite of overreaction.
- Dev had n = 1,316 and the CI included 0.

**S1 fade Yes, the frozen cell** (lowest tercile, V < $3,838; Yes at 0.20–0.50; buy NO at 1 − p + slippage; first
snapshot per market)
- Return per $1: +5.1% [+4.2%, +6.1%] at 1¢ (event-clustered [+4.3%, +5.9%]), and +3.6% at 2¢.
- n = 18,614 trades, win rate 0.718.
- **PASSES the pre-registered bar.**
- The documented fee (0.04·q·(1−q)) costs under 0.1 pt.
- Capacity: median **$62** traded on the market in the 24 h before entry.
- Same band over all terciles: +5.1% (n = 23,284). Not a thin-market effect, as written down before the test.
- Mirror check, buying YES in the same cell: −16.3%.

## Checks after the test (all post-hoc; none changes the verdict above)

**Independent verifier (Sonnet), re-derived from the parquet files with its own code:** CONFIRMED WITH CAVEATS.
- Reproduced exactly: n, +5.11%, CIs. No lookahead: no entry has resolution ≤ T.
- Not concentrated: the top-10 events hold 5% of PnL; excluding them gives +4.9%.
- Positive in every quarter: 2025Q4 +2.2%, others +5.5% to +10.2%.
- Excluding crypto price ladders: +5.1%.
- Selection on resolved-by-archive-end markets does not favour NO. Long-dated markets are the most positive.
- **Neg-risk (multi-outcome) half, n = 12,120, +4.1%, is an overround artifact.**
  - Where the siblings' Yes prices sum to ≤ 1.05, the return is +0.6% [−0.4, +1.6].
  - It rises to +16% to +29% where the field sums to 1.2–3.
  - The NO side isn't mispriced by itself. The field is overpriced as a whole, and no sibling-level edge exists.
- Stale last-fill prices (24% of trades) return +8.1%, against +4.2% on real VWAP prices.

**Executable entry (behav_entry.py).**
- The rule's entry is the VWAP of the 24 h *before* T, which nobody could trade at.
- Re-priced at the first fill after T, and at Monday's VWAP, for the 13,787 entries with a Monday fill (event-clustered CIs).

| Entry | All, 1¢ | Binary, 1¢ | Neg-risk, 1¢ |
|---|---|---|---|
| Pre-registered (VWAP before T), same 13,787 | +3.1% [+2.2, +4.1] | +5.9% [+4.0, +8.0] | +1.6% [+0.6, +2.6] |
| Monday VWAP (executable proxy) | **−0.1% [−1.3, +1.3]** | **+5.5% [+2.6, +8.9]** | **−3.2% [−4.2, −2.1]** |
| First fill after T (single prints, heavy-tailed) | +5.1% [+3.1, +7.4] | +11.9% [+7.6, +16.7] | +1.3% [−0.5, +3.3] |

- Markets with no Monday fill (4,827 of 18,614) can't be entered that day. On paper they were the better trades.
- At the conservative executable price, **the whole strategy is ~0 and the neg-risk half loses.**
- **Binary markets keep +5.5% at 1¢ (+3.4% at 2¢).**

## What this means
- Polymarket prices "Yes" ~1.5–2 pts too high on average, independent of volume.
- The pre-registered strategy's paper edge is mostly (a) the overround of multi-outcome fields and (b) entering at a
  price from before the signal.
- The residual binary-market edge (+5.5% at an executable price, median ~$60/day of flow) is the one thing worth a forward test.
  - It is a post-hoc subset, so it must be re-run on data never looked at: the live recorder's markets from now on,
    or archive months after 2026-04.
  - Size is the binding limit. A $62/day market cannot take more than tens of dollars per trade.
- For Hugo: his thin-market claim does not hold, but a broad, small Yes bias does, and fields sum above 1.
  - A reference index built on these prices should de-bias Yes and normalise multi-outcome fields.

## CORRECTION (later on 2026-10-29, after the round-2 crypto test): the binary "survivor" is weaker than stated above
The B11 test showed that crypto price markets move together: one rally or sell-off decides all of them. Applied here,
binary S1 at the Monday-VWAP entry (+5.5%, n = 4,919) splits into:
- **Crypto price markets (15% of trades):** +17.9%. This is a bet that crypto falls, which happened in 2025–26, not a bias.
- **Everything else:** +3.3% [+0.8, +6.0] clustered by event, **[−0.2, +7.0] clustered by week** (common shocks),
  and decaying: +10% in 2025Q1, +1.5% in 2026Q1. It still contains Equities/Finance price markets (+25%), which are the
  same kind of direction bet.
- It is not an artifact of short-dated markets (excluding resolution within 2 days: +11.9% at Monday VWAP).
**Revised reading:** no reliable fade-Yes edge remains once market-wide direction is separated out. The general ~1.6 pt
Yes premium (B2) stands. The tradeable strategy does not.
