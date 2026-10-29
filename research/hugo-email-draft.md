Subject: Kahneman on Polymarket — what held up

Hi Hugo,

Congrats on the round. After our call I took your suggestion and tested the *Thinking, Fast and Slow* biases on
Polymarket's full trade history (Nov 2022 – Apr 2026, ~180k resolved markets). I wrote the rules down before looking
at outcomes, tuned on 2023–24 only, and ran each test once on 2025–26. Short version:

1. **A "Yes" premium is real, but it is not a thin-market effect.** Yes is priced ~1.6 pts above its hit rate, and
   the gap is the same in the lowest, middle and highest volume terciles (+1.6 / +1.6 / +1.7 pts). A fade-Yes rule
   (buy NO when Yes trades at 20–50¢) shows +5% per $1 on paper. Most of that is two things: multi-outcome fields whose
   Yes prices sum above 100%, and entering at a price from before the signal. At a price you could actually trade, only
   plain binary markets keep an edge (~+5%). Those markets trade ~$60/day, so it's real but tiny.

2. **CPI anchoring: your intuition shows up in month-on-month CPI.** When the market's expectation sits near the prior
   print, the actual print tends to land further from it than expected. Roughly, the market is 25–30% too close to the
   prior, though with only ~15 releases I can't pin the size down. I'd treat it as a lead, not a number. The market
   still beats a no-change forecast by a wide margin (0.05 vs 0.13 pp error).

3. **Sports: no regression-to-the-mean error.** After a team loses, or a player has a bad game, the next-game price is
   right on average (2,370 team series pairs; ~10k player props checked against box scores). These are the liquid
   markets, and they look efficient.

For a reference index, the practical implications I'd draw: de-bias raw Yes prices slightly, normalise multi-outcome
fields to sum to 1, and treat thin binary markets with the most suspicion. Happy to share the write-ups or code if
any of it is useful. (One more: after games end, decided props trade within ~0.1-0.3c of $1, so settlement lag is
not an opportunity; the big post-game discounts are all genuine resolution risk like stat corrections.)

Best,
Ayaan
