exec(open("research/hunt/dl_dig.py").read().split("def show")[0])
x["hold"] = (x.res_ts - x.last_ts) / 86400
W = r"iran|israel|ukraine|russia|hamas|hezbollah|lebanon|gaza|strike|ceasefire|war|invade"
def show(d, name):
    d = d.drop_duplicates("condition_id")
    if len(d) < 30: print(f"  {name:50} n={len(d)}"); return
    e = (d.next_open - d.Y - 0.01).to_numpy(); r = h.trade(d, "NO", "next_open").to_numpy()
    pe, de = boot_cells(d.event, np.zeros(len(d), int), e, 1)
    pr, dr_ = boot_cells(d.event, np.zeros(len(d), int), r, 1)
    t = r < np.quantile(r, 0.99); pt, dt_ = boot_cells(d.event[t], np.zeros(t.sum(), int), r[t], 1)
    pw, dw = boot_cells(d.res_week, np.zeros(len(d), int), r, 1)
    print(f"  {name:50} n={len(d):4} edge {ci_str(pe[0], de[:,0])} ret {ci_str(pr[0], dr_[:,0])} trim1% {ci_str(pt[0], dt_[:,0])} ret/res-week {ci_str(pw[0], dw[:,0])} hold med {d.hold.median():.0f}d win {(1-d.Y).mean():.2f}")
base = x[(x.kind != "other") & (x.sched_left >= 30)]
for per, m in (("2023", base.day < "2024"), ("2024", (base.day >= "2024") & (base.day < "2025")), ("2025", (base.day >= "2025") & (base.day < "2026")), ("2026", base.day >= "2026"), ("ALL", base.day > "")):
    d = base[m]; print("==", per)
    show(d[d.next_open.between(0.5, 0.95, "left")], "Yes 0.5-0.95 (the cell)")
    if per == "ALL":
        for lo, hi in ((0.3, 0.5), (0.5, 0.7), (0.7, 0.95)): show(d[d.next_open.between(lo, hi, "left")], f"Yes {lo}-{hi}")
        c = d[d.next_open.between(0.5, 0.95, "left")]
        show(c[~c.slug.str.contains(W, na=False)], "cell, excluding war/geopolitics")
        show(c[c.slug.str.contains(W, na=False)], "cell, war/geopolitics only")
        show(c[c.kind == "by/before"], "cell, by/before only"); show(c[c.kind == "in-20xx"], "cell, in-20xx only")
        show(c[c.usd > 1e4], "cell, usd > 10k"); show(c[c.sched_left > 90], "cell, > 90d left")
        # any later day, not just first: every 7th liquid day per market (re-entry robustness)
        print("  Yes-rate vs price by sched_left in cell:", c.drop_duplicates("condition_id").groupby(pd.cut(c.drop_duplicates("condition_id").sched_left, [30, 60, 120, 400, 1e4]), observed=True).apply(lambda g: f"{len(g)} p={g.next_open.mean():.2f} Y={g.Y.mean():.2f}").to_dict())
