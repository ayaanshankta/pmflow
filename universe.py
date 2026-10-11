"""Top-N non-sports, active, order-book-enabled Polymarket markets by volume24hr (activity; DECISIONS 2026-10-10) -> data/universe_polymarket.parquet.
Sports exclusion rule is the SPORTS regex below (tags + event title/slug + question), committed before recording starts."""
import json, re, datetime as dt
import pandas as pd, requests

GAMMA = "https://gamma-api.polymarket.com/events"
TOP_N = 200
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

def with_short(df, now=None):
    """Top-N by volume24hr ('top200') unioned with the SHORT_N most active markets whose end_date is within SHORT_DAYS ('short').
    A market in both keeps slice='top200'. df must be sorted by volume24hr desc."""
    now = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    top = df.head(TOP_N).assign(slice="top200")
    end = pd.to_datetime(df.end_date, utc=True, errors="coerce")
    short = df[(end > now) & (end <= now + pd.Timedelta(days=SHORT_DAYS)) & ~df.market_id.isin(top.market_id)].head(SHORT_N).assign(slice="short")
    return pd.concat([top, short], ignore_index=True)

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
                volume24hr=float(m.get("volume24hr") or 0), end_date=m.get("endDate"), fetched_utc=now))
    df = pd.DataFrame(rows).drop_duplicates("market_id").sort_values("volume24hr", ascending=False)
    return df, n_sports

if __name__ == "__main__":
    ev = fetch_events()
    df, n_sports = build(ev, sports_tag_ids())
    top = with_short(df)
    top.drop(columns="cat1").to_parquet("data/universe_polymarket.parquet", index=False)
    print(f"events={len(ev)} eligible_nonsports={len(df)} excluded_sports={n_sports} kept={len(top)}")
    print("slices:", top.slice.value_counts().to_dict())
    print(top.cat1.value_counts().to_string())
