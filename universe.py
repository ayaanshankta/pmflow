"""Top-N non-sports, active, order-book-enabled Polymarket markets by volume24hr (activity; DECISIONS 2026-10-10) -> data/universe_polymarket.parquet.
Sports exclusion rule is the SPORTS regex below (tags + event title/slug + question), committed before recording starts."""
import json, os, re, datetime as dt
import pandas as pd, requests

GAMMA = "https://gamma-api.polymarket.com/events"
FAMILY_CAP = 450  # total markets after the 'family' slice; recorder was ~250 markets at ~10 % of one core
TOP_N = 200
# Events always recorded whole, whatever their volume (slice='pinned'), because a known release will hit them.
# 2026-10-12: US CPI for September (annual, monthly, core MoM, core YoY; release Wed 2026-10-14 12:30 UTC) and PPI YoY (Thu 10-15).
PINNED_EVENTS = ("1005013", "1005014", "1005015", "1005022", "1006134")
SHORT_N, SHORT_DAYS = 50, 7  # 'short-dated': most-active markets ending within a week
GENERIC = {"All", "Featured", "United States", "Politics", "Elections", "World"}
SPORTS_KW = [
    "sports", "sport", "nba", "wnba", "nfl", "mlb", "nhl", "mls", "ncaa", "ncaab", "ncaaf", "cfb", "cbb", "soccer",
    "football", "basketball", "baseball", "hockey", "tennis", "golf", "pga", "ufc", "mma", "boxing", "f1", "formula 1",
    "formula one", "nascar", "indycar", "motogp", "esports", "e-sports", "cricket", "ipl", "rugby", "olympics",
    "olympic", "premier league", "la liga", "serie a", "bundesliga", "ligue 1", "champions league", "europa league",
    "world cup", "super bowl", "stanley cup", "world series", "nba finals", "march madness", "wimbledon", "us open",
    "grand slam", "atp", "wta", "fifa", "uefa", "league of legends", "counter-strike", "cs2", "dota", "valorant",
    "bowl game", "playoffs", "grand prix", "tour de france", "cycling", "volleyball", "darts", "snooker", "chess",
    "wrestling", "wwe", "lacrosse", "handball", "badminton", "table tennis", "swimming", "athletics", "marathon",
]
SPORTS = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(k) for k in SPORTS_KW) + r")(?![a-z0-9])", re.I)

def is_sports(tags, *texts):
    """tags: iterable of tag labels/slugs; texts: question, event title/slug. Slug hyphens count as spaces."""
    blob = " | ".join([*tags, *texts]).replace("-", " ").replace("_", " ")
    return bool(SPORTS.search(blob))

def fetch_events():
    out, off = [], 0
    while True:
        r = requests.get(GAMMA, params=dict(active="true", closed="false", limit=100, offset=off, order="liquidity", ascending="false"), timeout=30)
        if r.status_code == 422: return out  # API caps offset (~2100); liquidity-sorted so the top-N is already in hand
        r.raise_for_status()
        page = r.json()
        if not page: return out
        out += page; off += len(page)

def fetch_pinned(ev, ids=PINNED_EVENTS):
    """Append pinned events that the liquidity-ordered paging did not reach (they can be far down the list)."""
    have = {str(e["id"]) for e in ev}
    for i in ids:
        if i in have: continue
        r = requests.get(GAMMA, params=dict(id=i), timeout=30)
        if r.ok and r.json(): ev = ev + r.json()[:1]
    return ev

def with_pinned(df, top, ids=PINNED_EVENTS):
    """Add every eligible market of the pinned events that is not already in `top`, as slice='pinned'. Existing rows keep their slice."""
    add = df[df.event_id.astype(str).isin(ids) & ~df.market_id.isin(top.market_id)].assign(slice="pinned")
    return pd.concat([top, add], ignore_index=True) if len(add) else top

def with_short(df, now=None):
    """Top-N by volume24hr ('top200') unioned with the SHORT_N most active markets whose end_date is within SHORT_DAYS ('short').
    A market in both keeps slice='top200'. df must be sorted by volume24hr desc."""
    now = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    top = df.head(TOP_N).assign(slice="top200")
    end = pd.to_datetime(df.end_date, utc=True, errors="coerce")
    short = df[(end > now) & (end <= now + pd.Timedelta(days=SHORT_DAYS)) & ~df.market_id.isin(top.market_id)].head(SHORT_N).assign(slice="short")
    return pd.concat([top, short], ignore_index=True)

def econ(m):
    """Tick/reward/fee fields of one Gamma market (None where the market does not carry the field).
    reward_daily_rate = sum of rewardsDailyRate over clobRewards entries (0 if none)."""
    f = lambda k: (float(m[k]) if m.get(k) not in (None, "") else None)
    fs = m.get("feeSchedule") or {}
    return dict(
        tick_size=f("orderPriceMinTickSize"), min_order_size=f("orderMinSize"),
        rewards_min_size=f("rewardsMinSize"), rewards_max_spread=f("rewardsMaxSpread"),
        reward_daily_rate=float(sum(float(r.get("rewardsDailyRate") or 0) for r in m.get("clobRewards") or [])),
        fees_enabled=m.get("feesEnabled"), fee_type=m.get("feeType"),
        fee_rate=fs.get("rate"), fee_exponent=fs.get("exponent"), fee_taker_only=fs.get("takerOnly"),
        fee_rebate_rate=fs.get("rebateRate"), maker_base_fee=f("makerBaseFee"), taker_base_fee=f("takerBaseFee"))

def sports_tag_ids():
    """Tag ids of every sport/league listed by Gamma /sports."""
    r = requests.get("https://gamma-api.polymarket.com/sports", timeout=30); r.raise_for_status()
    return {t for s in r.json() for t in str(s.get("tags", "")).split(",") if t}

def build(events, sport_ids=frozenset()):
    rows, n_sports = [], 0
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for e in events:
        tags = [t.get(k, "") for t in (e.get("tags") or []) for k in ("label", "slug")]
        e_sport = any(str(t.get("id")) in sport_ids for t in e.get("tags") or [])
        for m in e.get("markets") or []:
            if not (m.get("active") and not m.get("closed") and m.get("enableOrderBook") and m.get("clobTokenIds")):
                continue
            toks = json.loads(m["clobTokenIds"]) if isinstance(m["clobTokenIds"], str) else m["clobTokenIds"]
            outs = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else (m.get("outcomes") or [])
            if len(toks) != 2: continue
            yi = outs.index("Yes") if "Yes" in outs else 0
            if e_sport or is_sports(tags, m.get("question", ""), e.get("title", ""), e.get("slug", "")):
                n_sports += 1; continue
            labels = [t["label"] for t in (e.get("tags") or []) if t.get("label")]
            rows.append(dict(
                market_id=m["conditionId"], question=m.get("question"), token_id_yes=toks[yi], token_id_no=toks[1 - yi],
                category="|".join(labels), cat1=next((l for l in labels if l not in GENERIC and not l.startswith(("Earn", "Rewards"))), "none"),
                liquidity=float(m.get("liquidityNum") or m.get("liquidity") or 0),
                volume24hr=float(m.get("volume24hr") or 0), end_date=m.get("endDate"), fetched_utc=now, **econ(m)))
    df = pd.DataFrame(rows).drop_duplicates("market_id").sort_values("volume24hr", ascending=False)
    return df.assign(**family_cols(events, df)), n_sports

def family_cols(events, df):
    """event_id / family_kind ('exclusive'|'ladder'|'none') / family_key / family_rank (ladders) / family_size for every row of df.
    Classification is families.py (C1 definitions); family_size counts all members of the family incl. ones without a book."""
    import families
    ids = set(df.market_id)
    fm = families.build(dict(recorded=list(ids), events={str(e["id"]): e for e in events}))
    info = {}
    for f in fm["families"]:
        for m in f["members"]:
            if m["market_id"] in ids:
                info[m["market_id"]] = (f["event_id"], f["kind"], f["key"], m.get("rank"), f["n_members"])
    ev = {m["conditionId"]: str(e["id"]) for e in events for m in e.get("markets") or [] if m["conditionId"] in ids}
    get = lambda i, j, dflt: [info.get(m, (ev.get(m),) + (dflt,) * 4)[j] for m in df.market_id]
    return dict(event_id=[ev.get(m) for m in df.market_id], family_kind=get(0, 1, "none"), family_key=get(0, 2, None),
                family_rank=pd.array(get(0, 3, None), dtype="Int64"), family_size=pd.array(get(0, 4, None), dtype="Int64"))

def with_family(df, top, cap=FAMILY_CAP):
    """Add slice='family': for every exclusive family / ladder with >= 1 market already in `top`, all its other eligible (book-enabled,
    non-sports, rows of df) markets. Families are taken in order of the share of their 24h volume already in the universe and ADDED WHOLE
    or not at all (a family that would pass `cap` is skipped; smaller ones may still fit). Existing rows keep their slice.
    Returns (universe, n_families_left_out_by_cap)."""
    have_ids, total, left, add = set(top.market_id), len(top), 0, []
    cands = []
    for key, g in df[df.family_kind.isin(["exclusive", "ladder"])].groupby("family_key"):
        have = g.market_id.isin(have_ids)
        if not have.any() or have.all():
            continue
        vt, vi = g.volume24hr.sum(), g[have].volume24hr.sum()
        cands.append((-(vi / vt if vt > 0 else 0.0), -vi, key, g[~have]))
    for _, _, key, miss in sorted(cands, key=lambda c: c[:3]):
        if total + len(miss) > cap:
            left += 1
            continue
        add.append(miss.assign(slice="family"))
        total += len(miss)
    return (pd.concat([top, *add], ignore_index=True) if add else top), left

def cap_arg(argv):
    """--cap N from argv (total-market cap for the family slice); default FAMILY_CAP."""
    return int(argv[argv.index("--cap") + 1]) if "--cap" in argv else FAMILY_CAP

if __name__ == "__main__":
    import sys
    cap = cap_arg(sys.argv)
    ev = fetch_pinned(fetch_events())
    df, n_sports = build(ev, sports_tag_ids())
    top, left_out = with_family(df, with_pinned(df, with_short(df)), cap)  # pinned counts toward cap and is never trimmed
    out = top.drop(columns="cat1")
    out.to_parquet("data/universe_polymarket.parquet", index=False)
    os.makedirs("data/universe_history", exist_ok=True)  # reward/fee settings per day; the dated copy is overwritten by a second run the same day
    now = dt.datetime.now(dt.timezone.utc)
    out.to_parquet(f"data/universe_history/universe_{now:%Y-%m-%d}.parquet", index=False)
    out.to_parquet(f"data/universe_history/universe_{now:%Y-%m-%dT%H%M%S}.parquet", index=False)  # time-stamped: never overwritten
    print(f"events={len(ev)} eligible_nonsports={len(df)} excluded_sports={n_sports} kept={len(top)}")
    print("slices:", top.slice.value_counts().to_dict(), "total", len(top), "families left out by cap:", left_out)
    import families
    fm = families.build(dict(recorded=list(top.market_id), events={str(e["id"]): e for e in ev}))
    c = {}
    for f in fm["families"]:
        c[(f["kind"], f["complete"])] = c.get((f["kind"], f["complete"]), 0) + 1
    print("C1 families with >= 1 market in universe (kind, complete): n =", c)
    print(top.cat1.value_counts().to_string())
