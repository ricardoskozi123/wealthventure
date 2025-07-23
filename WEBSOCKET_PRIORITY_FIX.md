# 🔧 WebSocket Priority Fix Needed

## Current Issue
The `webtrader/get_price` function is **NOT using WebSocket data** - it's still using HTTP APIs which causes rate limiting.

**Evidence from logs:**
```
INFO:root:Got price 24.84000000 for avax from Binance
```
This shows it's using Binance **HTTP API**, not the unlimited Binance **WebSocket**.

## What Should Happen

### ✅ Priority Order:
1. **WebSocket Data** (unlimited Binance, 60/min Finnhub) 
2. **Database Cache** (if recent)
3. **HTTP API Fallback** (only if WebSocket fails)

### ❌ Current Behavior:
1. **Database Cache** (60 seconds)
2. **HTTP API** (rate limited) ⬅️ **PROBLEM!**
3. **WebSocket ignored** ⬅️ **PROBLEM!**

## Required Fix

In `omcrm/webtrader/routes.py` around line 310, change the `get_price()` function to:

```python
# FIRST: Check WebSocket real-time manager
try:
    from omcrm.webtrader.realtime_data import real_time_manager
    cached_data = real_time_manager.get_cached_price(instrument.symbol)
    if cached_data:
        new_price = cached_data.get('price')
        logging.info(f"💰 Using WebSocket price for {instrument.symbol}: ${new_price}")
    else:
        # FALLBACK: HTTP API only if WebSocket unavailable
        new_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
except Exception as e:
    # FALLBACK: HTTP API if WebSocket fails
    new_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
```

## Expected Result After Fix

**Crypto (via Binance WebSocket):**
```
💰 Using WebSocket price for BTC: $111006.69 (unlimited Binance)
💰 Using WebSocket price for ETH: $2635.67 (unlimited Binance)
💰 Using WebSocket price for AVAX: $24.84 (unlimited Binance)
```

**Stocks (via Finnhub WebSocket or HTTP fallback):**
```
💰 Using WebSocket price for AAPL: $214.09 (Finnhub)
⚠️  No WebSocket data for AAPL, falling back to HTTP API
```

## Benefits After Fix
- 🆓 **No more rate limiting** for crypto (unlimited Binance WebSocket)
- ⚡ **Real-time prices** (sub-second latency)
- 🔄 **Automatic fallback** if WebSocket unavailable
- 📈 **90% fewer HTTP API calls** 