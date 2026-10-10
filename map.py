"""Map each news event to affected Polymarket markets + direction (spec: LABELS.md).

  python3 map.py [--keyword-only] [--limit N]   map events with no row yet for this method -> data/mapping.parquet
Reads headline text + question text only. Never reads prices. Per-run cost cap $0.50.
"""
import argparse, json, os, re, subprocess, sys, time
RECORD_START = "2026-10-10 08:06:00"  # UTC; first recorder row
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
OUT = os.path.join(D, "mapping.parquet")
CLAUDE = os.path.expanduser("~/.local/bin/claude")
CAP_USD, MAX_CAND, MAX_OUT = 0.50, 40, 5
SYSTEM = re.search(r"System prompt \(exact\):\n```\n(.*?)\n```", open(os.path.join(HERE, "LABELS.md")).read(), re.S).group(1)
FED_M = r"\bfed\b.*(rate|interest)"
# theme -> (event regex, market regex); people surnames are appended below
LEXICON = {
    "fed": (r"\b(fed|fomc|federal reserve|powell|warsh|rate (cut|hike)s?|interest rates?)\b", FED_M),
    "inflation": (r"\b(cpi|consumer price|inflation|ppi|producer price|pce|real earnings)", FED_M),
    "bitcoin": (r"\b(bitcoin|btc|crypto\w*|etfs?|sec|tether|stablecoins?)\b", r"bitcoin"),
    "ethereum": (r"\b(ethereum|eth|ether|starknet)\b", r"ethereum"),
    "oil": (r"\b(oil|crude|opec|wti)\b", r"wti|crude"),
    "iran": (r"\b(iran\w*|hormuz|kharg|blockade|bessent)\b", r"iran|hormuz|kharg|blockade"),
    "ukraine": (r"\b(ukrain\w*|zelensk\w*|putin|russia\w*|nato)\b", r"ukrain|putin|russia|zelensk|nato"),
    "midterms": (r"\b(midterms?|senate|house|republicans?|democrats?)\b", r"midterm|senate|house"),
}
for p in ["lula", "bolsonaro", "le pen", "bardella", "vance", "rubio", "netanyahu", "sánchez", "putin", "xi jinping", "trump"]:
    LEXICON["person:" + p] = (r"\b" + p + r"\b", p)
POS = r"surg|rall|jump|soar|rebound|rise|gain|approv|record|deal|agree|truce|reopen|launch"
NEG = r"plung|crash|fall|drop|slump|hack|exploit|ban|bars|sue|lawsuit|fraud|theft|stolen|probe|strike|attack|collapse|seiz"
HAWK, DOVE = r"\b(higher|hotter|beats?|rises?|rose|accelerat\w*)\b", r"\b(lower|cooler|misses|falls?|fell|slows?|eases)\b"
SURPRISE_THEMES = {"fed", "inflation"}


def candidates(title, universe):
    """-> (themes matched, universe rows matching any matched theme's market regex), ranked by volume24hr, <= MAX_CAND."""
    t = title.lower()
    themes = [k for k, (ev, _) in LEXICON.items() if re.search(ev, t)]
    if not themes:
        return themes, universe.iloc[0:0]
    q = universe.question.str.lower()
    hit = pd.Series(False, index=universe.index)
    for k in themes:
        hit |= q.str.contains(LEXICON[k][1], regex=True)
    return themes, universe[hit].sort_values("volume24hr", ascending=False).head(MAX_CAND)


def _sign(t, pos, neg):
    p, n = bool(re.search(pos, t)), bool(re.search(neg, t))
    return 1 if p and not n else -1 if n and not p else 0


def keyword_dir(title, kind, themes, question):
    """Direction of YES probability for one (event, market) pair under the LABELS.md baseline rules."""
    t, q = title.lower(), question.lower()
    if re.search(FED_M, q):  # Fed rate markets
        if not SURPRISE_THEMES & set(themes):
            return "none"
        hawk = 1 if re.search(HAWK, t) or re.search(r"\b(raise|hike|increase)\w* .*rate|rate hike", t) else 0
        dove = 1 if re.search(DOVE, t) or re.search(r"\b(cut|lower|reduc)\w* .*rate|rate cut", t) else 0
        s = hawk - dove
        if s == 0 or "no change" in q:
            return "none"
        s = -s if re.search(r"decrease|cut", q) else s
        return "up" if s > 0 else "down"
    if kind == "scheduled" or any(k.startswith("person:") or k in ("midterms", "ukraine") for k in themes):
        return "none"
    if re.search(r"between", q):
        return "none"
    s = _sign(t, POS, NEG)
    if re.search(r"\bdip\b|\(low\)", q):
        s = -s
    return {1: "up", -1: "down", 0: "none"}[s]


def keyword_map(row, cand, themes):
    return [{"market_id": m, "direction": keyword_dir(row["title"], row["kind"], themes, qu), "confidence": 0.3}
            for m, qu in zip(cand.market_id[:MAX_OUT], cand.question[:MAX_OUT])]


def user_message(row, cand):
    lines = [f"m{i + 1} | {q}" for i, q in enumerate(cand.question)]
    return (f"source: {row['source']}\nkind: {row['kind']}\nt0_utc: {row['t0_utc']:%Y-%m-%dT%H:%M:%SZ}\n"
            f"headline: {row['title']}\nmarkets:\n" + "\n".join(lines))


def parse_reply(text, ids):
    """Model reply text -> (list of {market_id (real), direction, confidence} | None, error | None)."""
    m = re.search(r"\[.*\]", text or "", re.S)  # tolerate stray prose / fences around the array
    try:
        arr = json.loads(m.group(0)) if m else None
    except ValueError:
        arr = None
    if not isinstance(arr, list) or len(arr) > MAX_OUT:
        return None, "not a JSON array of <= 5: " + str(text)[:120]
    out, seen = [], set()
    for a in arr:
        if (not isinstance(a, dict) or set(a) != {"market_id", "direction", "confidence"} or a["market_id"] not in ids
                or a["market_id"] in seen or a["direction"] not in ("up", "down", "none")
                or isinstance(a["confidence"], bool) or not isinstance(a["confidence"], (int, float))
                or not 0 <= a["confidence"] <= 1):
            return None, "bad element: " + str(a)[:120]
        seen.add(a["market_id"])
        out.append({"market_id": ids[a["market_id"]], "direction": a["direction"], "confidence": float(a["confidence"])})
    return out, None


def call_llm(msg):
    """-> (reply text | None, cost, error | None)."""
    try:
        r = subprocess.run([CLAUDE, "-p", msg, "--model", "haiku", "--system-prompt", SYSTEM, "--output-format", "json",
                            "--tools", "", "--safe-mode", "--no-session-persistence", "--max-budget-usd", "0.25"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180).stdout
        env = json.loads(r)
    except (subprocess.TimeoutExpired, ValueError) as e:
        return None, 0.0, f"call failed: {e!r}"[:200]
    if env.get("is_error"):
        return None, env.get("total_cost_usd") or 0.0, "is_error: " + str(env.get("result"))[:200]
    return env.get("result"), env.get("total_cost_usd") or 0.0, None


def llm_map(row, cand):
    """-> (mapping list | None, cost, error). One retry on an invalid reply."""
    ids, cost, err = {f"m{i + 1}": m for i, m in enumerate(cand.market_id)}, 0.0, None
    for _ in range(2):
        text, c, err = call_llm(user_message(row, cand))
        cost += c
        if err is None:
            res, err = parse_reply(text, ids)
            if err is None:
                return res, cost, None
    return None, cost, err


def run(keyword_only, limit, out=OUT, universe=None, events=None):
    method = "keyword" if keyword_only else "llm"
    universe = universe if universe is not None else pd.read_parquet(os.path.join(D, "universe_polymarket.parquet"))
    if events is None:  # DECISIONS 2026-10-10: only events inside the recording window are mapped (backfill mapped Jan recaps to Oct markets)
        events = pd.read_parquet(os.path.join(D, "events.parquet"))
        events = events[pd.to_datetime(events.t0_utc, utc=True) >= pd.Timestamp(RECORD_START, tz="UTC")]
    old = pd.read_parquet(out) if os.path.exists(out) else pd.DataFrame(
        columns=["event_id", "market_id", "direction", "confidence", "method", "mapped_utc"])
    done = set(old[old.method == method].event_id)
    rows, cost, calls, ok, bad = [], 0.0, 0, 0, 0

    def save():
        pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_parquet(out, index=False)

    for ev in events[~events.event_id.isin(done)].sort_values("t0_utc", ascending=False).to_dict("records"):
        themes, cand = candidates(ev["title"], universe)
        res = []
        if len(cand):
            if keyword_only:
                res = keyword_map(ev, cand, themes)
            else:
                if calls >= limit or cost > CAP_USD:
                    continue
                calls += 1
                res, c, err = llm_map(ev, cand)
                cost += c
                if res is None:
                    bad += 1
                    print(f"FAILED {ev['event_id']}: {err}", file=sys.stderr)
                    continue
                ok += 1
        now = datetime.now(timezone.utc).isoformat()
        rows += [dict(event_id=ev["event_id"], **r, method=method, mapped_utc=now) for r in res] or [
            dict(event_id=ev["event_id"], market_id=None, direction="none", confidence=0.0, method=method, mapped_utc=now)]
        save()
    if rows:
        save()
    print(f"method={method} new_rows={len(rows)} llm_calls={calls} parsed={ok} failed={bad} cost=${cost:.4f} (cap ${CAP_USD})")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword-only", action="store_true")
    ap.add_argument("--limit", type=int, default=10**9, help="max LLM calls this run")
    a = ap.parse_args()
    run(a.keyword_only, a.limit)
