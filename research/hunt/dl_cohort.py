# F2 cell by deadline cohort: each scheduled-close month is one roughly independent draw. How many months are positive?
exec(open("research/hunt/dl_rob.py").read().split("base = ")[0])
c = x[(x.kind != "other") & (x.sched_left >= 30) & x.next_open.between(0.5, 0.95, "left")].drop_duplicates("condition_id").copy()
c["edge"] = c.next_open - c.Y - 0.01
c["cohort"] = c.close_at.dt.strftime("%Y-%m")
t = c.groupby("cohort").agg(n=("edge", "size"), events=("event", "nunique"), price=("next_open", "mean"), yes=("Y", "mean"), edge=("edge", "mean"))
print(t.round(3).to_string())
for name, g in (("all months", t), ("months n>=5", t[t.n >= 5]), ("months n>=10", t[t.n >= 10])):
    pos, k = (g.edge > 0).sum(), len(g)
    rng = np.random.default_rng(0); e = g.edge.to_numpy()
    dr = e[rng.integers(0, k, (2000, k))].mean(1)
    print(f"{name}: {pos}/{k} positive; equal-weight mean {e.mean():+.4f} [{np.percentile(dr, 2.5):+.4f}, {np.percentile(dr, 97.5):+.4f}]; median {np.median(e):+.4f}")
c["qe"] = c.close_at.dt.month.isin([3, 6, 9, 12]) & (c.close_at.dt.day >= 28) | (c.close_at.dt.month.isin([1, 4, 7, 10]) & (c.close_at.dt.day == 1))
for k, g in c.groupby("qe"):
    pe, de = boot_cells(g.cohort, np.zeros(len(g), int), g.edge.to_numpy(), 1)
    print(f"quarter-end deadline={k}: n {len(g)} edge {ci_str(pe[0], de[:,0])} (cluster = month)")
