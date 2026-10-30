exec(open("research/hunt/hunt.py").read().split("N = [0]")[0])
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
x = b[(b.usd > 1e3) & ~b.crypto & ~b.sports & b.nr_id.isna()]
x["kind"] = np.select([x.slug.str.contains(r"-by-|-before-", na=False), x.slug.str.contains(r"-in-20\d\d", na=False)], ["by/before", "in-20xx"], "other")
x["event"] = x.slug.str.replace(r"-\d.*$", "", regex=True).str.split("-").str[:4].str.join("-")
def show(d, name, cl="res_week"):
    d = d.drop_duplicates("condition_id")
    if len(d) < 30: print(f"  {name:55} n={len(d)}"); return
    e = (d.next_open - d.Y - 0.01).to_numpy()
    pt, dr = boot_cells(d[cl], np.zeros(len(d), int), e, 1)
    print(f"  {name:55} n={len(d):5,} events {d.event.nunique():4} edge {ci_str(pt[0], dr[:,0])} price {d.next_open.mean():.2f} Yes-rate {d.Y.mean():.2f}")
for per, m in (("DEV", x.day < "2025"), ("2025-26", x.day >= "2025")):
    print("==", per)
    for k in ("by/before", "in-20xx", "other"):
        for lo, hi in ((0.05, 0.5), (0.5, 0.95)):
            for dlo, dhi in ((1, 30), (30, 1e9)):
                d = x[m & (x.kind == k) & x.next_open.between(lo, hi, "left") & x.sched_left.between(dlo, dhi, "left")]
                show(d, f"{k} Yes {lo}-{hi} {dlo}-{dhi:.0f}d")
    d = x[m & (x.kind != "other") & x.next_open.between(0.5, 0.95, "left") & (x.sched_left >= 30)]
    show(d, "by/in, Yes 0.5-0.95, 30d+ : cluster event", "event")
    print(d.drop_duplicates("condition_id")[["day", "slug", "next_open", "Y", "sched_left", "usd"]].sort_values("usd", ascending=False).head(25).to_string())
