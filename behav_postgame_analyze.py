"""B9 settlement lag in NBA props (research/behavioral-rules.md, B9). Descriptive; no pass bar.

Inputs: data/behav/postgame_fills.parquet (behav_postgame.py), props.parquet, resolutions.parquet.
Run:  python behav_postgame_analyze.py
"""
import numpy as np
import pandas as pd

from behav_analyze import boot_cells, ci


def main():
    f = pd.read_parquet("data/behav/postgame_fills.parquet")
    props = pd.read_parquet("data/behav/props.parquet", columns=["condition_id", "stat", "tip", "gdate", "player"])
    r = pd.read_parquet("data/behav/resolutions.parquet", columns=["condition_id", "payout", "res_ts"])
    props = props.merge(r, on="condition_id", how="left")
    props["y_over"] = props.payout.map({"1,0": 1, "0,1": 0})
    props = props.dropna(subset=["y_over", "res_ts"])
    props["tip_s"] = props.tip.astype("int64") // 10**9 if props.tip.dt.unit == "ns" else props.tip.astype("int64") // 10**6
    f = f.merge(props, on="condition_id")
    f["q"] = np.where(f.y_over == 1, f.p_event, 1 - f.p_event)  # price of the side that won
    f = f[f.ts < f.res_ts]
    print(f"props {len(props):,}; tip→resolution median {((props.res_ts - props.tip_s) / 3600).median():.1f} h")
    for h in (2.5, 3, 4):
        g = f[f.ts >= f.tip_s + h * 3600]
        print(f"\n== decided = tip + {h} h: {len(g):,} fills, ${g.usd.sum():,.0f}, on {g.condition_id.nunique():,} props "
              f"({g.condition_id.nunique() / len(props):.1%} of props) ==")
        if not len(g):
            continue
        disc = (1 - g.q) * 100
        print("  discount 1−q (cents), per fill: " + "  ".join(f"p{k}={np.percentile(disc, k):.1f}" for k in (10, 25, 50, 75, 90)))
        print(f"  $ at q ≤ 0.98: ${g.usd[g.q <= .98].sum():,.0f}   q ≤ 0.95: ${g.usd[g.q <= .95].sum():,.0f}   "
              f"LOSING side paid up (q < 0.5): {(g.q < .5).sum():,} fills, ${g.usd[g.q < .5].sum():,.0f}")
        dec_ts = props.tip_s + h * 3600
        print(f"  decided → resolution: median {((props.res_ts - dec_ts) / 3600).median():.1f} h, "
              f"p90 {np.percentile((props.res_ts - dec_ts) / 3600, 90):.1f} h")
        b = pd.cut(g.q, [0, .5, .9, .95, .98, .99, 1.0001], right=False)
        ret = 1 / g.q - 1
        fee = 0.04 * g.q * (1 - g.q) / g.q
        t = pd.DataFrame({"fills": g.groupby(b, observed=True).size(), "usd": g.usd.groupby(b, observed=True).sum().round(0),
                          "ret_gross": ret.groupby(b, observed=True).mean(), "ret_doc_fee": (ret - fee).groupby(b, observed=True).mean()})
        print(t.round(4).to_string())
        if h == 3:
            by = g.groupby("stat").agg(fills=("q", "size"), usd=("usd", "sum"), med_disc_c=("q", lambda x: (1 - x.median()) * 100))
            print(by.round(2).to_string())
            pp = g.groupby("condition_id").apply(lambda x: pd.Series({"usd": x.usd.sum(), "ret": (x.usd * (1 / x.q - 1)).sum()}), include_groups=False)
            pt, dr = boot_cells(pp.index.to_series().map(props.set_index("condition_id").gdate), np.zeros(len(pp), int),
                                (pp.ret / pp.usd).to_numpy(), 1)
            lo, hi = ci(dr[:, 0])
            print(f"  $-weighted return per prop, buying the winner at every post-decided fill: {pt[0]:+.4f} [{lo:+.4f}, {hi:+.4f}] "
                  f"(cluster = game date); total $ {pp.usd.sum():,.0f}, total profit ${pp.ret.sum():,.0f}")
            bad = g[g.q < .5].merge(props[["condition_id"]], on="condition_id")
            print("  losing-side fills, examples:", bad[["player", "stat", "gdate", "q", "usd"]].head(8).to_dict("records"))


if __name__ == "__main__":
    main()
