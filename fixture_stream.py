"""Fixture message stream shared by test_record.py (pins the top-of-book output of the pre-change recorder)."""
DAY1 = 1_760_000_000 * 10**9  # 2025-10-09 UTC
BOOK = {"event_type": "book", "asset_id": "YES1", "market": "M1",
        "bids": [{"price": "0.40", "size": "10"}, {"price": "0.45", "size": "5"}],
        "asks": [{"price": "0.55", "size": "7"}, {"price": "0.60", "size": "9"}]}
pc = lambda px, sz, side, t="YES1": {"event_type": "price_change", "price_changes": [
    {"asset_id": t, "price": px, "size": sz, "side": side}]}
TRADE = {"event_type": "last_trade_price", "market": "M1", "asset_id": "YES1", "price": "0.46", "size": "12.5",
         "fee_rate_bps": "0", "side": "SELL", "timestamp": "1760000000123", "transaction_hash": "0xabc"}
TICK = {"event_type": "tick_size_change", "market": "M1", "asset_id": "YES1", "old_tick_size": "0.01",
        "new_tick_size": "0.001", "timestamp": "1760000000456"}
S = 10**9
# (msg, recv_ns); trade/tick lines are inert for the legacy recorder
STREAM = [(BOOK, DAY1), (pc("0.46", "3", "BUY"), DAY1 + 1), (TRADE, DAY1 + 2), (pc("0.46", "3", "BUY"), DAY1 + 3),
          (pc("0.20", "8", "BUY"), DAY1 + 4), (TICK, DAY1 + 5), (pc("0.46", "0", "BUY"), DAY1 + 6),
          (pc("0.55", "0", "SELL"), DAY1 + 7), (BOOK, DAY1 + 3 * S), (pc("0.50", "1", "BUY"), DAY1 + 86_400 * S)]
