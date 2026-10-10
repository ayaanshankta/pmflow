"""Scheduled pass after a release: map window events, measure reactions vs placebo, write data/summary.md.
Run: /opt/anaconda3/bin/python3 -W ignore event_pass.py   (launchd: com.ayaan.pmflow.pass.plist, 08:50 ET on weekdays)"""
import subprocess, sys
from datetime import datetime, timezone, timedelta
import pandas as pd
from map import RECORD_START
from run_reactions import run, summary

PY = sys.executable
subprocess.run([PY, "-W", "ignore", "map.py"], check=False)
ev = pd.read_parquet("data/events.parquet"); ev["t0_utc"] = pd.to_datetime(ev.t0_utc, utc=True)
lo, hi = pd.Timestamp(RECORD_START, tz="UTC"), pd.Timestamp.now(tz="UTC") - pd.Timedelta("61min")
w = ev[(ev.t0_utc >= lo) & (ev.t0_utc <= hi)]
m = pd.read_parquet("data/mapping.parquet"); m = m[m.market_id.notna()]
j = w.merge(m, on="event_id")
lines = [f"# pmflow pass {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z", f"events in window: {len(w)}; mapped pairs: {len(j)}; directional: {(j.direction != 'none').sum()}"]
if len(j):
    e = j[["event_id", "t0_utc", "market_id", "direction", "source"]].assign(venue="polymarket")
    df = run(e, n_placebo=20, seed=0); df.to_parquet("data/reactions.parquet")
    lines += ["", "```", str(summary(df)), "```", "", j[["source", "t0_utc", "title", "direction", "confidence"]].to_string()]
open("data/summary.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
