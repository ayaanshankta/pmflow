"""C2 step 1b: family map (research/structure-rules.md Definitions + C2). Reads ONLY Gamma metadata + per-market fill counts/volume; no price.
Run: /opt/anaconda3/bin/python3 leadlag_map.py -> research/leadlag-family-map.csv.gz + research/leadlag-family-map.md

FAMILY = one Gamma event (id). Kinds:
 exclusive : the event is negRisk=true and >= 2 of its markets are in the archive set.
 ladder    : the event is NOT negRisk and >= 2 of its markets share one question TEMPLATE inside the event, where the template is the
             lower-cased question with (a) a date after by/before/until/through/prior to replaced by <D> and (b) a number after a
             threshold cue (above/below/over/under/at least/more than/reach/hit/exceed/>/</>=/<=...) replaced by <N>. The cue words stay in the
             template, so every member of one ladder asks the same direction. Members must differ in the extracted values.
             Dropped as ambiguous: members differing in BOTH dates and numbers; "between" questions; a market in >1 event with no unique
             negRisk event; duplicate value tuples. A single event may hold several ladders (family id = event id + '|' + template hash).
Direction convention used later: exclusive -> siblings move opposite to the leader; ladder -> same sign.
"""
import glob, hashlib, json, re
import pandas as pd
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_RX = re.compile(rf"\b(by|before|until|through|prior to)\s+(?:the end of\s+)?((?:{MONTHS})\.?(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?(?:,?\s+\d{{4}})?|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?|\d{{4}}-\d{{2}}-\d{{2}})", re.I)
CUES = r"\b(?:above|below|over|under|at least|at most|more than|fewer than|less than|higher than|lower than|greater than|reach(?:es)?|hit(?:s)?|exceed(?:s)?|up to|dip to|fall to|drop to)|>=?|<=?|\u2265|\u2264"
NUM_RX = re.compile(rf"({CUES})\s*(\$?\s*[\d][\d,]*(?:\.\d+)?(?:\s*(?:[kmbt]\b|%|bps)|\s+(?:million|billion|trillion))?)", re.I)

def normalise(q):
    """question -> (template, date_values tuple, number_values tuple); None if 'between' (bracket, not nested)."""
    s = re.sub(r"\s+", " ", (q or "").lower()).strip()
    if re.search(r"\bbetween\b", s): return None
    dates, nums = [], []
    def d(m): dates.append(m.group(2)); return f"{m.group(1)} <D>"
    def n(m): nums.append(re.sub(r"[\s$,]", "", m.group(2))); return f"{m.group(1)} <N>"
    s = DATE_RX.sub(d, s); s = NUM_RX.sub(n, s)
    return s, tuple(dates), tuple(nums)

def pick_event(events):
    """-> event dict or None. One event -> it; several -> the unique negRisk one; else ambiguous."""
    if len(events) == 1: return events[0]
    nr = [e for e in events if e.get("negRisk")]
    return nr[0] if len(nr) == 1 else None

def build(rows):
    """rows: list of gamma_markets.jsonl dicts -> DataFrame cid, family, kind ('exclusive'|'ladder'|'dropped:<why>'|'single'|'nogamma')."""
    out, byev = {}, {}
    for r in rows:
        c = r["cid"]
        if not r.get("found"): out[c] = (None, "nogamma"); continue
        if not r.get("events"): out[c] = (None, "dropped:no_event"); continue
        e = pick_event(r["events"])
        if e is None: out[c] = (None, "dropped:multi_event"); continue
        byev.setdefault(str(e["id"]), []).append((r, e))
    for ev, ms in byev.items():
        if len(ms) < 2:
            out[ms[0][0]["cid"]] = (ev, "single"); continue
        if ms[0][1].get("negRisk"):
            for r, e in ms: out[r["cid"]] = (ev, "exclusive")
            continue
        groups = {}
        for r, e in ms:
            nm = normalise(r.get("question"))
            if nm is None: out[r["cid"]] = (ev, "dropped:between"); continue
            groups.setdefault(nm[0], []).append((r["cid"], nm[1], nm[2]))
        for tpl, g in groups.items():
            if len(g) < 2: out[g[0][0]] = (ev, "single"); continue
            dv, nv, vals = {x[1] for x in g}, {x[2] for x in g}, {(x[1], x[2]) for x in g}
            fam = ev + "|" + hashlib.md5(tpl.encode()).hexdigest()[:8]
            if len(dv) > 1 and len(nv) > 1: kind, fam = "dropped:two_dims", ev
            elif len(vals) != len(g): kind, fam = "dropped:duplicate_values", ev   # includes identical text with no extractable value
            else: kind = "ladder"
            for c, _, _ in g: out[c] = (fam, kind)
    return pd.DataFrame([(c, f, k) for c, (f, k) in out.items()], columns=["cid", "family", "kind"])

if __name__ == "__main__":
    rows = [json.loads(l) for l in open("data/leadlag/gamma_markets.jsonl")]
    fm = build(rows)
    mk = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/leadlag/mk_2025_*.parquet"))])
    mk = mk.groupby("condition_id").agg(slug=("slug", "first"), nr_mid=("nr_mid", "first"), n=("n", "sum"), usd=("usd", "sum")).reset_index().rename(columns={"condition_id": "cid"})
    g = pd.DataFrame(rows).drop_duplicates("cid").set_index("cid")
    fm = mk.merge(fm, on="cid", how="left")
    fm["kind"] = fm.kind.fillna(fm.slug.str.contains("up-?or-?down|updown", case=False).map({True: "not_looked_up:up_or_down", False: "not_looked_up:<20_fills"}))
    fm["question"] = fm.cid.map(g.question); fm["gamma_nrmid"] = fm.cid.map(g.negRiskMarketID)
    fm[~fm.kind.str.startswith("not_looked")].to_csv("research/leadlag-family-map.csv.gz", index=False)   # not-looked-up markets are counted in the md only
    tot_usd, tot_n = fm.usd.sum(), len(fm)
    s = fm.groupby("kind").agg(markets=("cid", "size"), fills=("n", "sum"), usd=("usd", "sum")); s["usd_share"] = s.usd / tot_usd; s["mkt_share"] = s.markets / tot_n
    fam = fm[fm.kind.isin(["exclusive", "ladder"])].groupby(["kind", "family"]).size().reset_index(name="members")
    cnt = fam.groupby("kind").members.agg(families="size", median_members="median", max_members="max")
    lk = fm[~fm.kind.str.startswith("not_looked")]
    nr = fm[fm.nr_mid.notna() & fm.gamma_nrmid.notna()]
    md = ["# C2 family map (2025 archive markets, Gamma event membership)", "", "Counts over all 2025 markets with >= 1 fill in daily_aligned(+multi) (2024-12-31..2025-12-31 shards).", "", s.to_markdown(floatfmt=".4f"), "", "Families:", "", cnt.to_markdown(), "",
          f"Gamma lookup: {len(lk):,} markets looked up; found {(lk.kind != 'nogamma').mean():.1%}; markets placed in exclusive or ladder family = {fm.kind.isin(['exclusive','ladder']).mean():.1%} of all markets, {fm[fm.kind.isin(['exclusive','ladder'])].usd.sum()/tot_usd:.1%} of USDC volume; of looked-up markets {lk.kind.isin(['exclusive','ladder']).mean():.1%}.",
          f"Cross-check: archive neg_risk_market_id == Gamma negRiskMarketID for {(nr.nr_mid == nr.gamma_nrmid).mean():.1%} of {len(nr):,} markets with both."]
    open("research/leadlag-family-map.md", "w").write("\n".join(md) + "\n"); print("\n".join(md))
