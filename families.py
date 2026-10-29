"""Family map for research/structure-rules.md C1 (rules blob 1582327e1f20). Built from saved raw Gamma events only; reads no prices.

  python families.py --tob data/tob/polymarket --raw data/sets_gamma_events_raw.json [--fetch] [--out data/sets_families.json]
--fetch re-downloads the Gamma event of every market under --tob into --raw first (<= ~3 requests/s; closed markets need closed=true).

DEFINITIONS (C1)
 exclusive: an event with negRisk=true. Its markets are mutually exclusive, exactly one resolves YES.
   REQUIRED members = every market of the event, except markets that closed before RECORD_START with YES price 0
   (already resolved NO, so they add nothing to the sum). A market with no order book still counts as required: it can
   resolve YES, so a family containing one is never complete. complete = every required member is recorded
   (has a folder under --tob). Otherwise partial. negRiskAugmented events carry unnamed placeholder outcomes; they are
   flagged `augmented` but treated the same (an unrecorded placeholder makes the family partial anyway).
 ladder: nested claims inside one event that is NOT negRisk. LADDER RULE (written before any price is examined):
   1. Within an event, group markets by TEMPLATE = question with every calendar date ("October 31", "June 30, 2027")
      replaced by <DATE> and every number ("$80,000", "$1.75T", "20") replaced by <NUM>.
   2. A group needs >= 2 markets, at most one number per question, and must not look like brackets
      ("between", "x-y" number ranges once dates are masked); otherwise it is dropped. Date masking includes
      day ranges ("October 5-11").
   3. Exactly one thing may vary across the group:
      - dates vary, numbers constant -> DEADLINE ladder, ordered by market endDate (all distinct).
          template contains "through"           -> persistence ("ceasefire continues through D"): EARLIER deadline is the
                                                   weaker (superset) claim.
          template contains " by " or "before"  -> onset ("X happens by D"): LATER deadline is the weaker claim.
          neither -> dropped (direction ambiguous).
      - numbers vary, dates constant, all endDates equal -> THRESHOLD ladder.
          explicit markers decide first: "(LOW)" or "↓" -> DOWN, "(HIGH)" or "↑" -> UP; else words:
          "dip", "below", "under", "fall", "drop" -> DOWN: the HIGHER number is weaker;
          "reach", "hit", "above", "exceed", "over" -> UP: the LOWER number is weaker.
          neither -> dropped.
      - both vary, or neither -> dropped.
   Equal claims (same threshold or same end date, e.g. a duplicate listing) share a rank and are tested in both directions.
   Weaker claim = superset: P(weaker YES) >= P(stronger YES), because stronger YES implies weaker YES.
   complete ladder = every market of the group is recorded; partial otherwise (any recorded pair is still a valid test).
 Dropped groups are counted with a reason in the output.
"""
import argparse, json, re, sys, time
import pandas as pd
from pathlib import Path
import requests

GAMMA = "https://gamma-api.polymarket.com"
RECORD_START = "2026-10-10T08:06:00Z"
DEFAULT_RATE = 0.04  # C1: "rate from the universe file where present, else 0.04"
MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_RE = re.compile(rf"\b{MONTHS}\.? \d{{1,2}}(?:st|nd|rd|th)?(?:\s?[-–]\s?\d{{1,2}})?(?:,? \d{{4}})?\b", re.I)
NUM_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s?[kKmMbBtT]?(?![a-z])")


def recorded_markets(tob_root):
    return sorted(p.name for p in Path(tob_root).iterdir() if p.is_dir())


def fetch(market_ids, sleep=0.3):
    m2e, events = {}, {}
    for i in range(0, len(market_ids), 20):
        for closed in ("false", "true"):  # Gamma hides closed markets unless asked
            r = requests.get(f"{GAMMA}/markets", params=[("condition_ids", c) for c in market_ids[i:i+20]] + [("closed", closed), ("limit", 100)], timeout=30)
            r.raise_for_status()
            for m in r.json():
                m2e[m["conditionId"]] = [str(e["id"]) for e in m.get("events") or []]
            time.sleep(sleep)
    for eid in sorted({e for v in m2e.values() for e in v}):
        r = requests.get(f"{GAMMA}/events", params={"id": eid}, timeout=30)
        r.raise_for_status()
        j = r.json()
        events[eid] = j[0] if isinstance(j, list) and j else j
        time.sleep(sleep)
    return dict(fetched_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), recorded=market_ids, market_to_events=m2e, events=events)


def _num(s):
    s = s.replace("$", "").replace(",", "").strip()
    mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}.get(s[-1:].lower())
    return float(s[:-1]) * mult if mult else float(s)


def fee_rate(m):
    """Taker fee rate of one Gamma market: its feeSchedule rate if present, else DEFAULT_RATE. Returns (rate, from_schedule)."""
    fs = m.get("feeSchedule") or {}
    if fs.get("rate") is not None:
        return float(fs["rate"]), True
    return DEFAULT_RATE, False


def _member(m, rec):
    rate, sched = fee_rate(m)
    return dict(market_id=m["conditionId"], question=m.get("question"), title=m.get("groupItemTitle"), end=m.get("endDate"),
                recorded=m["conditionId"] in rec, fee_rate=rate, fee_from_schedule=sched)


def _required(m, record_start):
    """Exclusive-family member that must be recorded for the family to be complete."""
    ct, op = m.get("closedTime"), m.get("outcomePrices")
    if ct and op:  # already resolved NO before recording began -> no longer part of the live sum
        try:
            if str(ct).replace(" ", "T")[:19] < record_start[:19] and float(json.loads(op)[0]) == 0.0:
                return False
        except (ValueError, TypeError, IndexError):
            pass
    return True


def _ladder_group(ms):
    """-> (direction, ordered members weakest-first) or (None, reason)."""
    texts = [m["question"] or "" for m in ms]
    if any(re.search(r"between|\d\s?[-–]\s?\d", DATE_RE.sub("<DATE>", t)) for t in texts):
        return None, "bracket-like"
    dates = [DATE_RE.findall(t) for t in texts]
    masked = [NUM_RE.sub("<NUM>", DATE_RE.sub("<DATE>", t)) for t in texts]
    nums = [[_num(x) for x in NUM_RE.findall(DATE_RE.sub("<DATE>", t))] for t in texts]
    if any(len(n) > 1 for n in nums):
        return None, "more than one number"
    dvary, nvary = len({tuple(d) for d in dates}) > 1, len({tuple(n) for n in nums}) > 1
    ends = [m["end"] for m in ms]
    low = " ".join(masked).lower() + " " + " ".join((m["title"] or "") for m in ms)
    if dvary and not nvary:
        if any(e is None for e in ends):  # Gamma omits endDate on some members; unorderable, so unclassifiable
            return None, "missing end date"
        if re.search(r"\bthrough\b", low):
            return "deadline_persist", sorted(zip(ends, ms), key=lambda x: x[0])  # earlier = weaker
        if re.search(r"\bby\b|\bbefore\b", low):
            return "deadline_onset", sorted(zip(ends, ms), key=lambda x: x[0], reverse=True)
        return None, "deadline direction ambiguous"
    if nvary and not dvary:
        if len(set(ends)) != 1:
            return None, "threshold ends differ"
        # explicit markers win: "hit (LOW) $60" contains "hit" but is a DOWN claim
        down = re.search(r"\(low\)|↓", low) or (not re.search(r"\(high\)|↑", low) and re.search(r"\bdip\b|\bbelow\b|\bunder\b|\bfall\b|\bdrop\b", low))
        up = re.search(r"\(high\)|↑", low) or (not down and re.search(r"\breach\b|\bhit\b|\babove\b|\bexceed\b|\bover\b", low))
        if down and not up:
            return "threshold_down", sorted(zip([n[0] for n in nums], ms), key=lambda x: -x[0])
        if up and not down:
            return "threshold_up", sorted(zip([n[0] for n in nums], ms), key=lambda x: x[0])
        return None, "threshold direction ambiguous"
    return None, "both or neither vary"


def build(raw, record_start=RECORD_START):
    rec = set(raw["recorded"])
    fams, dropped = [], []
    for eid, e in raw["events"].items():
        ms = e.get("markets") or []
        if e.get("negRisk"):
            req = [m for m in ms if _required(m, record_start)]
            mem = [_member(m, rec) for m in req]
            n = sum(x["recorded"] for x in mem)
            if n:
                fams.append(dict(kind="exclusive", event_id=eid, key=eid, title=e.get("title"), augmented=bool(e.get("negRiskAugmented")),
                                 n_members=len(mem), n_recorded=n, complete=n == len(mem), members=mem))
            continue
        groups = {}
        for m in ms:
            t = NUM_RE.sub("<NUM>", DATE_RE.sub("<DATE>", m.get("question") or ""))
            groups.setdefault(t, []).append(_member(m, rec))
        for t, g in groups.items():
            n = sum(x["recorded"] for x in g)
            if len(g) < 2 or n < 1:
                continue
            direction, res = _ladder_group(g)
            if direction is None:
                if n >= 2:
                    dropped.append(dict(event_id=eid, title=e.get("title"), template=t, reason=res, n_members=len(g), n_recorded=n))
                continue
            mem, key = [], None
            for k, m in res:  # weakest (superset) first; rank = position of the distinct strength level, equal claims share a rank
                rank = 0 if key is None else rank + (k != key)
                key = k
                mem.append(dict(m, rank=rank))
            fams.append(dict(kind="ladder", event_id=eid, key=f"{eid}:{t}", title=e.get("title"), direction=direction, template=t,
                             n_members=len(mem), n_recorded=n, complete=n == len(mem), members=mem))
    return dict(rules_blob="1582327e1f20", record_start=record_start, n_recorded_markets=len(rec), families=fams, dropped=dropped)


def from_universe(u, recorded):
    """Family map (same shape as build()) from the stored universe columns event_id / family_kind / family_key / family_rank /
    family_size, so no API call is needed. `u` is a universe parquet DataFrame (or a dated history copy), `recorded` the set of
    market ids that have data. Complete = every member of the family (family_size, which counts members without a book) recorded."""
    rec, fams = set(recorded), []
    d = u[u.family_kind.isin(["exclusive", "ladder"])]
    for key, g in d.groupby("family_key", sort=False):
        mem = []
        for r in g.itertuples():
            fr = getattr(r, "fee_rate", None)
            ok = fr is not None and fr == fr
            mem.append(dict(market_id=r.market_id, question=r.question, title=(r.question or "")[-40:], end=r.end_date, recorded=r.market_id in rec,
                            fee_rate=float(fr) if ok else DEFAULT_RATE, fee_from_schedule=bool(ok), rank=0 if pd.isna(r.family_rank) else int(r.family_rank)))
        n = sum(m["recorded"] for m in mem)
        size = max(int(g.family_size.iloc[0]), len(mem))
        if n:
            kind = g.family_kind.iloc[0]
            if kind == "ladder":
                mem.sort(key=lambda m: m["rank"])
            fams.append(dict(kind=kind, event_id=str(g.event_id.iloc[0]), key=str(key), title=str(g.question.iloc[0])[:60], n_members=size,
                             n_recorded=n, complete=n == size, members=mem))
    return dict(rules_blob="1582327e1f20", source="universe", families=fams, dropped=[])


def summary(out):
    import collections
    c = collections.Counter()
    for f in out["families"]:
        c[(f["kind"], "complete" if f["complete"] else "partial", "testable" if f["n_recorded"] >= 2 else "single")] += 1
    return c


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tob", default="data/tob/polymarket")
    ap.add_argument("--raw", default="data/sets_gamma_events_raw.json")
    ap.add_argument("--out", default="data/sets_families.json")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--record-start", default=RECORD_START)
    a = ap.parse_args()
    if a.fetch:
        raw = fetch(recorded_markets(a.tob))
        Path(a.raw).write_text(json.dumps(raw))
    raw = json.loads(Path(a.raw).read_text())
    out = build(raw, a.record_start)
    Path(a.out).write_text(json.dumps(out, indent=1))
    for k, v in sorted(summary(out).items()):
        print(k, v)
    print("dropped groups with >=2 recorded:", len(out["dropped"]))
