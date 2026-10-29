# B7 result: NBA player props — does the market overreact to one game? (rules: behavioral-rules.md B7, amendment, dev decisions)

**Answer: no tradeable bias.** The market does not overreact to one game, and the apparent "over is overpriced" edge did
not survive independent verification. Test period 2026-02-16..2026-04-28, run once; development Dec 2025..2026-02-15.

| Measure (TEST) | Result |
|---|---|
| Line move after one game (points) | −1.38 after a bad game, +0.94 after a great one |
| Real form: corr(z_n, z_n+1) | +0.099 (n = 3,296): form carries a little, so the line move is roughly justified |
| Premium great − bad (primary) | −0.030, 95 % CI [−0.067, +0.007]: no overreaction (sign even opposite) |
| S7 fade the last game | negative in every cell; k = 0.5 significantly negative (−8.1 % at 1¢) |
| S7b under, points, pair subset (pre-registered) | +7.0 %, CI [+0.9 %, +13.3 %], n = 1,634: **passes the bar, but see verification** |
| S7b under, ALL priced points main lines (verifier) | **+3.1 %, CI [−1.2 %, +7.4 %], n = 2,984: not significant** |
| … player played only | +2.0 %, n.s.; no-shows (DNP, pay the under on-chain 1,844/1,893) supply ~40 % of the point estimate |
| … at 2¢ / 3¢ slippage | +0.6 % / −1.7 % |
| Capacity | median $51 traded pre-game per points prop (p75 $286) |

**Verification (independent re-derivation, Sonnet verifier, 2026-10-29): CONFIRMED WITH CAVEATS.** Plumbing sound
(y_over vs box score 99.97 % agreement; no post-tip prices; main-line choice uses no outcome; not driven by a few players).
But the pair filter selects a favourable slice (pairs +6.4 %, non-pairs −1.6 %), the played-game part is not significant,
the DNP part uses a 6-hour VWAP that can mix pre- and post-news fills, and S7b was a development-derived hypothesis with
several variants. **Correct reading:** overs are mildly overpriced (price 0.486 vs hit rate 0.462), consistent with a
"Yes" premium, but the effect is small, not significant on the full universe, and gone after realistic slippage.

Not covered by automated tests (verifier note): the B7 code has no test file; a fixture test is owed before reuse.
