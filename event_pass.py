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
import os
m = pd.read_parquet("data/mapping.parquet") if os.path.exists("data/mapping.parquet") else pd.DataFrame(columns=["event_id", "market_id", "direction", "confidence", "method"])
m = m[m.market_id.notna()]
j = w.merge(m, on="event_id")
lines = [f"# pmflow pass {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z", f"events in window: {len(w)}; mapped pairs: {len(j)}; directional: {(j.direction != 'none').sum()}"]
if len(j):
    e = j[["event_id", "t0_utc", "market_id", "direction", "source"]].assign(venue="polymarket")
    df = run(e, n_placebo=20, seed=0); df.to_parquet("data/reactions.parquet")
    lines += ["", "```", str(summary(df)), "```", "", j[["source", "t0_utc", "title", "direction", "confidence"]].to_string()]
health = subprocess.run([PY, "-W", "ignore", "gaps.py"], capture_output=True, text=True).stdout.strip().splitlines()
lines += ["", "## health (gaps.py)"] + [l for l in health if not l.startswith("/")]
txt = "\n".join(lines) + "\n"
open("data/summary.md", "w").write(txt); print(txt)
# self-report: commit ONLY the results file onto origin/desktop with git plumbing (no branch switch, no working-tree change,
# always a fast-forward); push. Falls back silently if the remote is unreachable.
import os, tempfile
os.makedirs("results", exist_ok=True)
fn = f"results/pass-{datetime.now(timezone.utc):%Y%m%d-%H%M}Z.md"; open(fn, "w").write(txt)
def g(*a, env=None):
    return subprocess.run(["git", *a], capture_output=True, text=True, env={**os.environ, **(env or {})})
g("fetch", "-q", "origin", "desktop")
parent = "origin/desktop" if g("rev-parse", "--verify", "-q", "origin/desktop").returncode == 0 else "HEAD"
idx = {"GIT_INDEX_FILE": os.path.join(tempfile.gettempdir(), "pmflow-pass.index")}
g("read-tree", parent, env=idx)
blob = g("hash-object", "-w", fn).stdout.strip()
g("update-index", "--add", "--cacheinfo", f"100644,{blob},{fn}", env=idx)
tree = g("write-tree", env=idx).stdout.strip()
commit = g("-c", "user.name=AyaanShankta", "-c", "user.email=ayaanshankta08@gmail.com", "commit-tree", tree, "-p", parent, "-m", f"pass {fn}").stdout.strip()
r = g("push", "-q", "origin", f"{commit}:refs/heads/desktop"); print("push:", "ok" if r.returncode == 0 else r.stderr.strip()[-200:])
