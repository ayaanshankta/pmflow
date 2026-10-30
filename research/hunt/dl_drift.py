# Does Yes drift down in the F2 cell before resolution? Exit at the close k calendar days after entry (or Y if resolved first).
exec(open("research/hunt/dl_rob.py").read().split("base = ")[0])
bars = b[["condition_id", "day", "close"]].copy(); bars["d"] = pd.to_datetime(bars.day)
c = x[(x.kind != "other") & (x.sched_left >= 30) & x.next_open.between(0.5, 0.95, "left")].drop_duplicates("condition_id").copy()
c["d0"] = pd.to_datetime(c.day) + pd.Timedelta(days=1)
for k in (7, 14, 30, 60):
    t = c[["condition_id", "d0"]].assign(d=c.d0 + pd.Timedelta(days=k)).sort_values("d")
    m = pd.merge_asof(t, bars.sort_values("d")[["d", "condition_id", "close"]], on="d", by="condition_id", direction="backward")
    c[f"x{k}"] = m.set_index("condition_id").close.reindex(c.condition_id).to_numpy()
    resolved = c.res_ts < ((c.d0 + pd.Timedelta(days=k)) - pd.Timestamp(0)) // pd.Timedelta(seconds=1)
    c[f"x{k}"] = np.where(resolved, c.Y, c[f"x{k}"])
for per, m in (("DEV", c.day < "2025"), ("2025-26", c.day >= "2025"), ("ALL", c.day > "")):
    print("==", per, "n", m.sum())
    for k in (7, 14, 30, 60):
        g = c[m]; pts = (g.next_open - g[f"x{k}"] - 0.02).to_numpy()  # No: entry - exit, 1c each way
        pt, dr = boot_cells(g.res_week, np.zeros(len(g), int), pts, 1)
        pe, de = boot_cells(g.event, np.zeros(len(g), int), pts, 1)
        print(f"  exit after {k:2}d: pts {ci_str(pe[0], de[:,0])} (event) {ci_str(pt[0], dr[:,0])} (res-week)  share resolved {(g.res_ts < ((g.d0 + pd.Timedelta(days=k)) - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).mean():.2f}")
    g = c[m & (c.sched_left >= 60)]
    for k in (14, 30):
        pts = (g.next_open - g[f"x{k}"] - 0.02).to_numpy(); pe, de = boot_cells(g.event, np.zeros(len(g), int), pts, 1); pt, dr = boot_cells(g.res_week, np.zeros(len(g), int), pts, 1)
        print(f"  >=60d left, exit {k}d: n {len(g)} pts {ci_str(pe[0], de[:,0])} (event) {ci_str(pt[0], dr[:,0])} (res-week)")
c["res_date"] = pd.to_datetime(c.res_ts, unit="s").dt.date.astype(str)
for drop in (["2026-01-01"], ["2026-01-01", "2026-04-01"]):
    g = c[~c.res_date.isin(drop)]
    for k in (14, 30):
        pts = (g.next_open - g[f"x{k}"] - 0.02).to_numpy(); pe, de = boot_cells(g.event, np.zeros(len(g), int), pts, 1); pt, dr = boot_cells(g.res_date, np.zeros(len(g), int), pts, 1)
        print(f"  drop {drop} exit {k}d: n {len(g)} pts {ci_str(pe[0], de[:,0])} (event) {ci_str(pt[0], dr[:,0])} (res-date)")
