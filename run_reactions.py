"""Measure reactions for every (event, market) in data/events.parquet and for its placebos; print the summary.
events.parquet columns: event_id, t0_utc, venue, market_id, direction in {up, down, none}, source.
Run:  /opt/anaconda3/bin/python3 -W ignore run_reactions.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from reaction import HORIZONS, ROOT, _day_type, load_tob, measure, placebo_times

DATA = Path(__file__).parent / "data"
SIGN = {"up": 1.0, "down": -1.0}


def _dates(root, venue, market_id):
    return [f.stem.removeprefix("date=") for f in (Path(root) / venue / str(market_id)).glob("date=*.parquet")]


def run(events, root=ROOT, n_placebo=20, seed=0):
    """One row per (event, market) with kind='event', plus n_placebo rows kind='placebo' carrying the same
    event_id/direction. Placebo dates = dates for which that market has a tob file."""
    rows = []
    for k, e in enumerate(events.itertuples()):
        dates = _dates(root, e.venue, e.market_id)
        times = [(pd.Timestamp(e.t0_utc), "event")]
        if any(_day_type(d) == _day_type(e.t0_utc) for d in dates):
            times += [(t, "placebo") for t in placebo_times(dates, n_placebo, seed * 1_000_003 + k, e.t0_utc)]
        for t0, kind in times:
            tob = load_tob(e.venue, e.market_id, t0, root=root)
            rows.append({"event_id": e.event_id, "venue": e.venue, "market_id": e.market_id, "direction": e.direction,
                         "source": e.source, "kind": kind, "t0_utc": t0, **measure(tob, t0)})
    return pd.DataFrame(rows)


def boot(groups, stat, n=1000, seed=0):
    """(point, lo, hi, n_values): stat over values pooled across events; 95 % CI resampling EVENTS (groups)."""
    rng = np.random.default_rng(seed)
    ids = list(groups)
    f = lambda v: stat(v) if len(v) else np.nan
    point = f(np.concatenate([groups[i] for i in ids])) if ids else np.nan
    if not ids:
        return point, np.nan, np.nan, 0
    d = [f(np.concatenate([groups[ids[p]] for p in rng.integers(0, len(ids), len(ids))])) for _ in range(n)]
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    return point, lo, hi, sum(len(v) for v in groups.values())


def summary(df, n_boot=1000, seed=0):
    """Event vs placebo for rows with direction != none: mean |dp_h| (and signed dp_h, in the called direction)
    per horizon, median t_reprice_s. CIs: bootstrap over events."""
    d = df[df.direction != "none"].copy()
    sgn = d.direction.map(SIGN)
    for h in HORIZONS:
        d[f"|dp_{h}|"] = d[f"dp_{h}"].abs()
        d[f"signed dp_{h}"] = d[f"dp_{h}"] * sgn
    specs = [(f"|dp_{h}|", np.mean) for h in HORIZONS] + [("t_reprice_s", np.median)] + \
            [(f"signed dp_{h}", np.mean) for h in HORIZONS]
    out = []
    for col, stat in specs:
        r = {"metric": col, "stat": stat.__name__}
        for kind in ("event", "placebo"):
            g = {i: v.dropna().to_numpy() for i, v in d[d.kind == kind].groupby("event_id")[col]}
            r.update(zip((f"{kind}_{x}" for x in ("est", "lo", "hi", "n")), boot(g, stat, n_boot, seed)))
        out.append(r)
    return pd.DataFrame(out)


def main():
    ev = pd.read_parquet(DATA / "events.parquet")
    df = run(ev)
    df.to_parquet(DATA / "reactions.parquet")
    s = summary(df)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(s.to_string(index=False, float_format=lambda x: f"{x:.4g}"))


if __name__ == "__main__":
    main()
