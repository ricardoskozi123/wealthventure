# Quick Fix for Rate Limiting Issue

## Problem
The application is hitting API rate limits because it's making too many concurrent requests to free APIs.

## Immediate Solutions:

### 1. Enable Real-Time WebSockets (Recommended)
- WebSockets are already implemented and will provide real-time data without API calls
- To enable: Click "Start Real-Time Feeds" button in the WebTrader dashboard
- This will use Binance WebSocket (unlimited) and Finnhub WebSocket (60 calls/minute)

### 2. Temporary Workaround - Use Cached Prices
- The system will automatically fall back to cached/database prices when APIs are rate limited
- Users will see prices that are up to 30 seconds old instead of real-time

### 3. Manual Rate Limiting
Edit `omcrm/webtrader/routes.py` line 42 and 48:
- Change `time.sleep(0.2)` to `time.sleep(2.0)` (2 second delays)
- This will slow down API calls but prevent rate limiting

## Long-term Solution
The WebSocket real-time system is already implemented and should be used instead of HTTP polling.

## Benefits of WebSocket System:
- ✅ Real-time price updates
- ✅ No API rate limits for most instruments
- ✅ Better performance
- ✅ Professional trading experience
- ✅ Uses completely free APIs (Binance, Finnhub) 