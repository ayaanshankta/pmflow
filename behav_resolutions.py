"""True resolution times for every market (the archive's resolved_at column is ~empty).

CTF/resolutions.parquet gives each condition's resolution as a Polygon log id `137_<block>_<logIndex>`. Block numbers are
converted to UTC times by linear interpolation between anchor blocks fetched from a public Polygon RPC (~2 s blocks, so an
anchor every 100k blocks is accurate to well under an hour; snapshots are weekly).

Run:  python behav_resolutions.py      Out: data/behav/resolutions.parquet (condition_id, res_ts, payout, block)
"""
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

RPC = "https://polygon-bor-rpc.publicnode.com"
SRC = Path(__file__).parent / "data" / "archive" / "CTF" / "resolutions.parquet"
OUT = Path(__file__).parent / "data" / "behav"
STEP = 100_000


def block_time(n):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [hex(n), False]}).encode()
    req = urllib.request.Request(RPC, body, {"content-type": "application/json", "user-agent": "pmflow-research"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return int(json.load(r)["result"]["timestamp"], 16)
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"block {n}: RPC failed 5 times")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r = pd.read_parquet(SRC, columns=["id", "condition_id", "payout_numerators"])
    r["block"] = r.id.str.split("_").str[1].astype(np.int64)
    r = r.sort_values("block").drop_duplicates("condition_id", keep="first")  # first resolution event per market
    anchors_path = OUT / "block_anchors.json"
    anchors = {int(k): v for k, v in json.loads(anchors_path.read_text()).items()} if anchors_path.exists() else {}
    want = list(range(r.block.min() // STEP * STEP, r.block.max() + STEP, STEP))
    for i, b in enumerate(b for b in want if b not in anchors):
        anchors[b] = block_time(b)
        time.sleep(0.4)  # polite
        if i % 50 == 0:
            anchors_path.write_text(json.dumps(anchors))
    anchors_path.write_text(json.dumps(anchors))
    ab = np.array(sorted(anchors)); at = np.array([anchors[b] for b in ab])
    assert np.all(np.diff(at) > 0), "anchor times must increase with block number"
    r["res_ts"] = np.interp(r.block, ab, at).astype(np.int64)
    r["payout"] = r.payout_numerators.map(lambda x: ",".join(x))
    r[["condition_id", "block", "res_ts", "payout"]].to_parquet(OUT / "resolutions.parquet")
    bt = np.diff(at) / STEP
    print(f"{len(r):,} markets; {len(ab)} anchors; block time {bt.min():.3f}-{bt.max():.3f} s; "
          f"{pd.to_datetime(r.res_ts.min(), unit='s')} .. {pd.to_datetime(r.res_ts.max(), unit='s')}")


if __name__ == "__main__":
    main()
