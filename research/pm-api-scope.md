# pm-api-scope (assembled 2026-10-10)
Bottom line: Kalshi technically easy, CONTRACTUALLY BLOCKED (Developer Agreement limits API use to own trading; recording/publishing/selling needs written permission). Polymarket technically open; Terms of Use could not be opened. No prior study measures second-level news-to-quote latency from order books.
## 1. Kalshi
(a) REST market data no key: /trade-api/v2/markets, /markets/{ticker}/orderbook, /markets/trades, /search/tags_by_categories (HTTP 200 on api.elections.kalshi.com); batch orderbook endpoint exists. WebSocket REQUIRES key even for public channels; channels ticker (best bid/ask+sizes, ts_ms), trade, orderbook_delta, market_lifecycle_v2. Key: log in, create in settings; §4.1.1 requires "Member" (KYC/funding/US-only unverified).
(b) Rate limits read/write per s: Basic 200/100 (signup); Advanced 300/300; Expert 600 (0.075% vol share) ... Prestige 12,000/9,600.
(c) Developer Agreement v1.1 (kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf), verbatim:
 §3 "Use of Kalshi APIs is expressly limited to facilitating a members own trading on the Exchange; all other usages are disallowed and may result in account suspension."
 §3.1 "Collecting, caching, aggregating, or storing data or content accessed via the API except for purposes of facilitating your own trading on Kalshi. You may not share such data or content with third parties in any manner without prior written authorization from Kalshi."
 §3.5 bars "monitoring the availability, performance, or functionality ... or for any other benchmarking or competitive purposes."
 §3.7 bars sublicensing. §6.4 requires written approval before public statements/disclosures relating to Kalshi.
 Reading: publishing a latency study — not allowed without permission; selling derived feed — not allowed; recording for research — outside §3. kalshi.com/developer-agreement returned 429 (v1.1 currency unconfirmed). Email Kalshi for research permission.
(d) Categories: Business, Climate and Weather, Commodities, Companies, Crypto, Economics, Elections, Entertainment, Financials, Mentions, Politics, Science and Technology, Social, Sports. Filter via GET /series?category= (exact, case-sensitive), include_volume=true. Drop multivariate combo...
(pending rest)
## 4. News sources (week-one picks)
1. BLS schedule: bls.gov/schedule/news_release/bls.ics; minute precision ET; CPI Oct 14 8:30, PPI Oct 15 8:30, import/export Oct 16 8:30.
2. BEA: bea.gov/news/schedule (ICS + apps.bea.gov/API/signup/release_dates.json); next GDP adv Q3 + PI/O Oct 29 8:30 (ET inferred).
3. Fed RSS: federalreserve.gov/feeds/press_all.xml, press_monetary.xml, speeches.xml, testimony.xml; pubDate minute-only (":00 GMT"). FOMC Oct 27-28, Dec 8-9.
4. SEC EDGAR current 8-K Atom: sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom; second precision w/ offset; 10 req/s, declared UA required.
5. Existing crypto headlines (Cointelegraph/Decrypt/The Block) — Crypto is largest non-sports category.
Not picked: GDELT (15-min batches), X API (~$0.005/post), Truth Social (third-party RSS trumpstruth.org/feed). Not checked: Reuters/AP, Google News, NewsAPI, WH/Congress; feed terms. Measure event-to-feed latency by polling every few s and logging first-seen vs stated timestamp.
## 2. Polymarket
Gamma public (markets/events/tags). CLOB GET /book,/price,/midpoint,/spread,/last-trade-price by token_id; POST /books etc max 500 items. Price history data-api.polymarket.com/v2/prices-history (1-min kept >=7 days). CLOB reads likely keyless (PublicClient).
WebSocket wss://ws-subscriptions-clob.polymarket.com/ws/market; subscribe {"assets_ids":[...],"type":"market","custom_feature_enabled":true}; events book, price_change, last_trade_price, tick_size_change (+ best_bid_ask, new_market, market_resolved with custom flag); live subscribe/unsubscribe ops; send text "PING" every 10 s -> "PONG". No auth stated; no max tokens stated.
Rate limits per IP / 10 s: Gamma general 4000, /markets 300, /tags 200; CLOB /book 1500, /books 500; throttled not rejected.
Terms: NOT OPENED (tos renders client-side; /legal/terms-of-use 404). Help page names academic researchers; code open source. Redistribution rights unknown -> read in browser.
Sports filter: GET /sports maps sport->tags; exclude those tags. Liquidity (low conf): Sports 40.6%, Other 24.7%, Crypto 17.1%, Politics 5.7% (Sep).
