"""Behavioral-bias snapshot table (research/behavioral-rules.md).

Streams the Polymarket-v1 archive one UTC day at a time (binary + neg-risk layers), keeps per-market running state,
and at every Monday 00:00 UTC emits one row per open market: price over the previous 24 h, volume to date, outcome.
Only information available at T enters a row except the outcome columns. Raw day files are deleted after reading.

Run:  python behav_build.py [start YYYY-MM-DD] [end YYYY-MM-DD]     (resumable; state in data/behav/)
Out:  data/behav/snapshots.parquet
"""
import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "TimeSeventeen/Polymarket-v1"
LAYERS = {"daily_aligned": "binary", "daily_aligned_multi": "multi"}
OUT = Path(__file__).parent / "data" / "behav"
COLS = ["block_timestamp", "p_event", "usdc_amount", "condition_id", "outcome_seq", "outcome_label",
        "winning_outcome_label", "resolution_status", "taker_base_fee", "close_at", "resolved_at",
        "market_slug", "category"]
META = ["slug", "category", "layer", "close_at", "resolved_at", "resolution_status", "win_label", "fee", "nr_id"]


def load_day(d, tmp, local=Path(__file__).parent / "data" / "archive"):
    """One UTC day, both layers, reduced to the columns we need. Uses a local copy if present."""
    frames = []
    for layer, name in LAYERS.items():
        fn = f"{layer}/{d:%Y_%m_%d}.parquet"
        cached = local / fn
        try:
            p = cached if cached.exists() else Path(hf_hub_download(REPO, fn, repo_type="dataset", local_dir=tmp))
        except Exception as e:  # a missing day in one layer is recorded, not fatal
            print(f"  {fn}: {type(e).__name__}", flush=True)
            continue
        cols = COLS + (["neg_risk_market_id"] if name == "multi" else [])
        f = pd.read_parquet(p, columns=cols)
        f["layer"] = name
        frames.append(f)
        if not cached.exists():
            p.unlink()
    return pd.concat(frames, ignore_index=True) if frames else None


def day_aggregates(f):
    """Per-market aggregates for one day: $ volume, fill count, VWAP of p_event, last fill, metadata, seq-1 label."""
    f = f.assign(pv=f.p_event * f.usdc_amount).sort_values("block_timestamp")
    g = f.groupby("condition_id", sort=False)
    a = g.agg(usd=("usdc_amount", "sum"), n=("p_event", "size"), pv=("pv", "sum"),
              last_ts=("block_timestamp", "last"), last_p=("p_event", "last"),
              slug=("market_slug", "first"), category=("category", "first"), layer=("layer", "first"),
              close_at=("close_at", "first"), resolved_at=("resolved_at", "first"),
              resolution_status=("resolution_status", "first"), win_label=("winning_outcome_label", "first"),
              fee=("taker_base_fee", "max"))
    a["nr_id"] = g["neg_risk_market_id"].first() if "neg_risk_market_id" in f else None
    s1 = f[f.outcome_seq == 1].groupby("condition_id")["outcome_label"].first()
    a["seq1_label"] = s1
    a["vwap"] = np.where(a.usd > 0, a.pv / a.usd.where(a.usd > 0), a.last_p)
    return a


class State:
    """Running per-market state across days: cumulative $ before today, last fill, daily VWAPs of the last 2 days."""

    def __init__(self, path, res_ts):
        self.path = path
        self.s = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        self.res_ts = res_ts  # condition_id -> on-chain resolution time (unix s); archive resolved_at is ~empty

    def snapshot(self, T, d_minus1, d_minus2):
        """Rows for Monday T (00:00 UTC). d_minus1 = Sunday aggregates (the 24 h before T), d_minus2 = Saturday."""
        s = self.s
        if s.empty:
            return None
        Ts = int(pd.Timestamp(T, tz="UTC").timestamp())
        res = self.res_ts.reindex(s.index)
        open_ = (s.last_ts >= Ts - 7 * 86400) & (res > Ts)  # never-resolved markets (NaN) are excluded
        r = s[open_].copy()
        r["T"] = pd.Timestamp(T, tz="UTC")
        r["res_ts"] = res[open_]
        r["p"] = d_minus1.vwap.reindex(r.index) if d_minus1 is not None else np.nan
        r["p_from_last_fill"] = r.p.isna()
        r["p"] = r.p.fillna(r.last_p)
        r["p_24h"] = d_minus2.vwap.reindex(r.index) if d_minus2 is not None else np.nan
        r["usd_24h"] = (d_minus1.usd.reindex(r.index) if d_minus1 is not None else np.nan)
        r["V"] = r.cum_usd
        r["days_to_close"] = (r.close_at - r["T"]).dt.total_seconds() / 86400
        return r.reset_index()[["condition_id", "T", "p", "p_from_last_fill", "p_24h", "usd_24h", "V", "days_to_close",
                                "last_ts", "res_ts", "seq1_label"] + META]

    def update(self, a):
        """Fold one day's aggregates in (cum_usd counts only days strictly before the next snapshot)."""
        if self.s.empty:
            self.s = a.assign(cum_usd=a.usd)[["cum_usd", "last_ts", "last_p", "seq1_label"] + META]
            return
        s = self.s.reindex(self.s.index.union(a.index))
        s["cum_usd"] = s.cum_usd.fillna(0) + a.usd.reindex(s.index).fillna(0)
        for c in ["last_ts", "last_p"]:
            s[c] = a[c].reindex(s.index).combine_first(s[c])
        for c in META + ["seq1_label"]:
            s[c] = s[c].combine_first(a[c].reindex(s.index)) if c in s else a[c].reindex(s.index)
        # ponytail: prune markets resolved over 8 days ago; they can never enter a snapshot again
        cutoff = int(a.last_ts.max()) - 8 * 86400
        self.s = s[~(self.res_ts.reindex(s.index) < cutoff)]

    def save(self):
        self.s.to_parquet(self.path)


def main(start="2022-11-21", end="2026-04-28"):
    OUT.mkdir(parents=True, exist_ok=True)
    prog_path = OUT / "progress.json"
    prog = json.loads(prog_path.read_text()) if prog_path.exists() else {"next_day": start, "parts": []}
    res = pd.read_parquet(Path(__file__).parent / "data" / "behav" / "resolutions.parquet")
    state = State(OUT / "state.parquet", res.set_index("condition_id").res_ts)
    d, stop = date.fromisoformat(prog["next_day"]), date.fromisoformat(end)
    prev1 = prev2 = None  # aggregates of the previous two days (rebuilt after a resume: first snapshot may lack p)
    rows, tmp = [], Path(tempfile.mkdtemp(prefix="behav_"))
    try:
        while d <= stop:
            if d.weekday() == 0:  # Monday: snapshot at 00:00 before folding in today
                snap = state.snapshot(d, prev1, prev2)
                if snap is not None and len(snap):
                    rows.append(snap)
            f = load_day(d, tmp)
            a = day_aggregates(f) if f is not None and len(f) else None
            if a is not None:
                state.update(a)
            prev2, prev1 = prev1, a
            d += timedelta(days=1)
            if d.day == 1 or d > stop:  # checkpoint monthly
                if rows:
                    part = OUT / f"snap_{d:%Y_%m_%d}.parquet"
                    pd.concat(rows, ignore_index=True).to_parquet(part)
                    prog["parts"].append(part.name)
                    rows = []
                state.save()
                prog["next_day"] = d.isoformat()
                prog_path.write_text(json.dumps(prog))
                print(f"{d} markets in state {len(state.s):,} parts {len(prog['parts'])}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    snaps = pd.concat([pd.read_parquet(OUT / p) for p in prog["parts"]], ignore_index=True)
    snaps.to_parquet(OUT / "snapshots.parquet")
    print(f"snapshots {len(snaps):,} rows, {snaps.condition_id.nunique():,} markets")


if __name__ == "__main__":
    main(*sys.argv[1:3])
