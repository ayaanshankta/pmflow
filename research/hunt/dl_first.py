exec(open("research/hunt/dl_rob.py").read().split("base = ")[0])
f = x.drop_duplicates("condition_id")  # first liquid day per market, as the F1 scanner enters
c = f[(f.kind != "other") & (f.sched_left >= 30) & f.next_open.between(0.5, 0.95, "left")]
for per, m in (("DEV", c.day < "2025"), ("2025-26", c.day >= "2025"), ("ALL", c.day > "")): show(c[m], f"first-liquid-day version {per}")
