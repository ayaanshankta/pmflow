"""Forward paper test F1 (research/behavioral-rules.md, "F1"): buy No in binary, non-sports, non-crypto Polymarket
markets on the first daily scan in which they trade >= $1,000 in 24 h, at the live No ask (1 - Yes best bid).

Run once a day:  python forward_no.py          appends new entries to data/forward/f1_entries.csv
Settle:          python forward_no.py settle   writes data/forward/f1_settled.csv and prints the running result
Paper only; Gamma public endpoints at one page per request (well under its stated limits).
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests

import universe as u

OUT = Path(__file__).parent / "data" / "forward"
ENTRIES, SETTLED = OUT / "f1_entries.csv", OUT / "f1_settled.csv"
FIELDS = ["entered_utc", "condition_id", "slug", "question", "end_date", "volume24hr", "yes_bid", "yes_ask", "no_ask"]
CRYPTO = re.compile(r"(?<![a-z0-9])(crypto|bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|dogecoin|memecoin|airdrop|fdv|token)(?![a-z0-9])", re.I)


def candidates(events, sport_ids, seen):
    """Rows for markets that qualify now and have never been entered."""
    now, rows = dt.datetime.now(dt.timezone.utc).isoformat(), []
    for e in events:
        if e.get("negRisk") or e.get("enableNegRisk"):
            continue
        tags = [t.get(k, "") for t in (e.get("tags") or []) for k in ("label", "slug")]
        if any(str(t.get("id")) in sport_ids for t in e.get("tags") or []):
            continue
        for m in e.get("markets") or []:
            if m.get("negRisk") or not (m.get("active") and not m.get("closed") and m.get("enableOrderBook")):
                continue
            outs = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else (m.get("outcomes") or [])
            if sorted(outs) != ["No", "Yes"] or m["conditionId"] in seen:
                continue
            text = " ".join([*tags, m.get("question", ""), e.get("title", ""), e.get("slug", ""), m.get("slug", "")])
            if u.is_sports(tags, text) or CRYPTO.search(text.replace("-", " ")) or "up-or-down" in (m.get("slug") or ""):
                continue
            vol, bid, ask = float(m.get("volume24hr") or 0), m.get("bestBid"), m.get("bestAsk")
            if vol < 1000 or bid is None or ask is None:
                continue
            bid, ask = float(bid), float(ask)
            if outs[0] != "Yes":  # Gamma best bid/ask are for the first outcome
                bid, ask = 1 - ask, 1 - bid
            if not 0.05 <= bid <= 0.95:
                continue
            rows.append(dict(entered_utc=now, condition_id=m["conditionId"], slug=m.get("slug"), question=m.get("question"),
                             end_date=m.get("endDate"), volume24hr=round(vol, 2), yes_bid=bid, yes_ask=ask, no_ask=round(1 - bid, 4)))
    return rows


def scan():
    OUT.mkdir(parents=True, exist_ok=True)
    seen = set()
    if ENTRIES.exists():
        with ENTRIES.open() as f:
            seen = {r["condition_id"] for r in csv.DictReader(f)}
    rows = candidates(u.fetch_events(), u.sports_tag_ids(), seen)
    new = not ENTRIES.exists()
    with ENTRIES.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)
    print(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} new entries {len(rows)}, total {len(seen) + len(rows)}")


def settle():
    with ENTRIES.open() as f:
        ents = list(csv.DictReader(f))
    out = []
    for i in range(0, len(ents), 50):  # one request per 50 markets
        ids = [e["condition_id"] for e in ents[i:i + 50]]
        r = requests.get("https://gamma-api.polymarket.com/markets", params=[("condition_ids", c) for c in ids] + [("limit", 50)], timeout=30)
        r.raise_for_status()
        by = {m["conditionId"]: m for m in r.json()}
        for e in ents[i:i + 50]:
            m = by.get(e["condition_id"])
            if not m or not m.get("closed") or m.get("umaResolutionStatus") not in (None, "resolved"):
                continue
            outs = json.loads(m["outcomes"]) if isinstance(m["outcomes"], str) else m["outcomes"]
            px = [float(x) for x in (json.loads(m["outcomePrices"]) if isinstance(m["outcomePrices"], str) else m["outcomePrices"])]
            if sorted(px) not in ([0.0, 1.0], [0.5, 0.5]):
                continue
            v_no = px[outs.index("No")]
            out.append({**e, "v_no": v_no, "ret": v_no / float(e["no_ask"]) - 1, "closed_time": m.get("closedTime")})
    if out:
        with SETTLED.open("w", newline="") as f:
            w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
    rets = sorted(float(o["ret"]) for o in out)
    n = len(rets)
    print(f"entries {len(ents)}, settled {n}" + (f", mean {sum(rets) / n:+.4f}, trimmed-top-1% mean "
          f"{sum(rets[:n - max(1, n // 100)]) / max(1, n - max(1, n // 100)):+.4f}" if n else ""))


def _selfcheck():
    ev = [dict(negRisk=False, tags=[dict(id="1", label="Politics", slug="politics")], title="T", slug="t",
               markets=[dict(conditionId="c1", active=True, closed=False, enableOrderBook=True, outcomes='["Yes","No"]',
                             question="Will X happen by June?", slug="x", volume24hr=5000, bestBid=0.30, bestAsk=0.32),
                        dict(conditionId="c2", active=True, closed=False, enableOrderBook=True, outcomes='["Yes","No"]',
                             question="Will bitcoin hit 200k?", slug="btc", volume24hr=5000, bestBid=0.30, bestAsk=0.32),
                        dict(conditionId="c3", active=True, closed=False, enableOrderBook=True, outcomes='["Yes","No"]',
                             question="Will Y happen?", slug="y", volume24hr=500, bestBid=0.30, bestAsk=0.32)])]
    rows = candidates(ev, set(), set())
    assert [r["condition_id"] for r in rows] == ["c1"] and rows[0]["no_ask"] == 0.70, rows
    assert candidates(ev, set(), {"c1"}) == []
    print("selfcheck ok")


if __name__ == "__main__":
    {"settle": settle, "check": _selfcheck}.get(sys.argv[1] if len(sys.argv) > 1 else "", scan)()
