# B6 result: team series, regression to the mean after a loss (test run once, 2026-10-29)

**Verdict: NO. The market does not mark a team down too far after it loses a game.**
- The loser of game n is priced at its true win rate for game n+1.
- Buying the loser loses money. Upset-losers are, if anything, slightly *over*priced.

Data and pairs:
- Polymarket moneylines `{nba|wnba|nhl|mlb}-{a}-{b}-{date}`.
- Pre-game VWAP over 00:00 ET the day before to 11:00 ET on game day.
- Winner from the on-chain payout.
- A pair is consecutive games between the same two teams, 1–4 days apart.
- Rules: research/behavioral-rules.md (B6), code `behav_sports_analyze.py`.

## TEST (game n+1 dated 2025-01-01 .. 2026-04-28): 2,370 pairs, 1,166 series (MLB 1,958, NBA 215, NHL 173, WNBA 24)

| | n | premium_L = price − win rate (<0 = loser underpriced) |
|---|---|---|
| All losers | 2,370 | +0.001 [−0.019, +0.020] |
| Upset losers (were favourite in game n) | 1,041 | +0.029 [−0.002, +0.060] |
| Non-upset losers | 1,320 | −0.020 [−0.047, +0.006] |

**S6, buy the loser before game n+1** (CIs clustered by series)

| Variant | 1¢ | 2¢ |
|---|---|---|
| All L | −0.7% [−5.2, +3.9] | −2.9% [−7.3, +1.5] |
| Upset-only L | −6.8% [−12.4, −1.4] | −8.4% [−13.9, −3.1] |

- **Both variants FAIL the pass bar.**
- Liquidity is not the problem: the median is ~$10,000 traded pre-game per game.

Development (2023–24, 173 pairs, mostly NBA) had shown premium_L −0.076 [−0.145, −0.006] and S6 +27%. That was
small-sample noise, which is why the test exists.

Orientation check:
- When the loser is the favourite in game n+1: price 0.579, win rate 0.544.
- When it is the underdog: 0.403 vs 0.429.
- corr(price, outcome) = +0.19.
- Prices line up with outcomes in the expected direction, so the team mapping is right.

## What this means
- Together with B7 (player props): at the single-game level, sports markets on Polymarket do not show the
  regression-to-the-mean error Kahneman describes.
- The faint pattern (favourites slightly dear, underdogs slightly cheap) is the ordinary favourite–longshot shape in
  reverse. It is not significant.
- These are the most liquid markets in the study, consistent with liquid markets being efficient.
