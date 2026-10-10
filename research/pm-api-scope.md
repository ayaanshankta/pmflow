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
