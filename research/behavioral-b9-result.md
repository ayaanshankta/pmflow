# B9 result: settlement lag in NBA props (2026-10-29; rules research/behavioral-rules.md B9, commit ae927ae)

**Verdict.**
- The mechanical settlement gap is real but small: most post-game size trades within 0.1–0.3¢ of $1.
- The fills at big discounts are not free money. They are props whose outcome was genuinely uncertain: stat
  corrections, games missing from the regular box score, postponed games and unclear no-show rules.
- Not a strategy worth running. At most a few thousand dollars a season across the *whole market*.

Data:
- 23,940 props, 2025-12-07 .. 2026-04-28.
- 187,569 fills from tip + 2 h until on-chain resolution (`behav_postgame.py`).
- Analysis in `behav_postgame_analyze.py`.
- Tip → resolution: median 5.3 h.

## Main window: decided = tip + 3 h

**Volume after "decided"**
- 35,357 fills, $1.78M, on 37% of props.
- Decided → resolution: median 2.3 h, p90 5.1 h.
- Discount on the winning side 1 − q, per fill: median 0.1¢, p75 0.7¢, p90 1.1¢.

| Winning-side price q | Fills | $ | Mean return buying the winner (gross) |
|---|---|---|---|
| ≥ 0.99 | 31,773 | 1,632,913 | +0.26% |
| 0.98–0.99 | 954 | 36,689 | +1.9% |
| 0.95–0.98 | 655 | 9,759 | +3.7% |
| 0.90–0.95 | 382 | 7,508 | +8.6% |
| 0.50–0.90 | 881 | 69,699 | +49% |
| < 0.50 (the losing side was the favourite) | 712 | 26,501 | (huge) |

- The documented fee changes these by < 0.1 pt.
- Sensitivity: + 2.5 h and + 4 h give the same shape.

## Check: was the outcome actually known? (box scores, Kaggle `szymonjwiak/nba-traditional`)

**Box score agrees with the on-chain payout**
- q < 0.5: 77%.
- 0.5–0.9: 96%.
- ≥ 0.98: 94%. Most disagreements are props with no regular box-score row.

**48 props where the payout and the box score disagree.** Examples:
- NBA Cup final (2025-12-16, no regular-season box row).
- 2026-01-24 Timberwolves (box missing).
- Chet Holmgren 9 rebounds against a 9.5 line, paid over (a stat correction or a data error).

**Discount fills with q < 0.9 where the box score agrees**
- Median **13 h after tip**, not minutes after the buzzer.
- 80% of them ($70k) in January 2026.
- Examples:
  - Reed Sheppard 4 rebounds against a 3.5 line traded at 1¢ ($4.9k), consistent with a stat correction from 3 to 4.
  - Vince Williams Jr assists traded at ~50¢ with no box row (no-show / postponement rule).
- These buyers and sellers were pricing resolution risk, not ignoring a known result.

## What this means
**The clean mechanical gap**
- Winner at 98–99.9¢, resolving ~2 h later: about $1.67M of flow over 4.5 months.
- Total profit on it: about $4–5k gross, for everyone combined. The edge is 0.26% on the bulk and 1.9% on a thin $37k slice.
- That is a liquidity-provision business at best, and it carries real tail risk. One stat correction against a 1¢
  edge wipes out hundreds of wins.

**For a reference index**
- Post-game prop prices are reliable (≥ 99¢) except where resolution is ambiguous.
- Those cases are visible in real time as a sudden drop in the winner's price, and should be flagged rather than averaged.
