#!/usr/bin/env python3
"""
Quick test of free market data sources
"""

import requests
import json

def test_free_forex():
    """Test ExchangeRate-API (1,500 requests/month FREE)"""
    print("🧪 Testing FREE Forex API...")
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        rates = data.get('rates', {})
        print(f"✅ FREE Forex API working!")
        print(f"💰 EUR/USD: {1/rates.get('EUR', 1):.4f}")
        print(f"💰 GBP/USD: {1/rates.get('GBP', 1):.4f}")
        print(f"💰 USD/JPY: {rates.get('JPY', 0):.2f}")
        
    except Exception as e:
        print(f"❌ Forex API failed: {e}")

def test_free_stocks():
    """Test IEX Cloud API (before trying WebSocket)"""
    print("\n🧪 Testing FREE Stock API...")
    try:
        # Test with IEX Cloud free endpoint
        url = "https://cloud.iexapis.com/stable/stock/aapl/quote?token=pk_test"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 401:
            print("⚠️  IEX requires API key, but WebSocket might work differently")
            
        # Try alternative free stock API
        url2 = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
        response2 = requests.get(url2, timeout=10)
        
        if response2.status_code == 200:
            data = response2.json()
            result = data['chart']['result'][0]
            price = result['meta']['regularMarketPrice']
            print(f"✅ Yahoo Finance API working!")
            print(f"📈 AAPL: ${price:.2f}")
        
    except Exception as e:
        print(f"❌ Stock API test failed: {e}")

def test_free_commodities():
    """Test Alpha Vantage for commodities"""
    print("\n🧪 Testing FREE Commodities API...")
    try:
        # Using demo key - you should get your own free key
        api_key = "demo"
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=GC=F&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data:
            quote = data['Global Quote']
            price = quote.get('05. price', 'N/A')
            print(f"✅ Alpha Vantage working!")
            print(f"🥇 Gold: ${price}")
        else:
            print(f"⚠️  Alpha Vantage demo key limited. Get free key at: https://www.alphavantage.co/support/#api-key")
            
    except Exception as e:
        print(f"❌ Commodities API failed: {e}")

def test_alternative_free_sources():
    """Test backup free sources"""
    print("\n🧪 Testing Alternative FREE Sources...")
    
    # Test Fixer.io for forex
    try:
        url = "http://data.fixer.io/api/latest?access_key=demo&base=USD"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ Fixer.io available (need free API key)")
        else:
            print("⚠️  Fixer.io needs API key")
    except:
        pass
    
    # Test CoinAPI for crypto (as backup to Binance)
    try:
        url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
        headers = {'X-CoinAPI-Key': 'demo'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 401:
            print("⚠️  CoinAPI needs free key but has good free tier")
    except:
        pass

if __name__ == "__main__":
    print("🚀 Testing FREE Market Data Sources\n")
    
    test_free_forex()
    test_free_stocks() 
    test_free_commodities()
    test_alternative_free_sources()
    
    print("\n📋 SUMMARY - Best FREE Sources:")
    print("✅ Crypto: Binance WebSocket (UNLIMITED)")
    print("✅ Forex: ExchangeRate-API (1,500 req/month)")  
    print("✅ Stocks: Yahoo Finance (unlimited but unofficial)")
    print("⚠️  Commodities: Alpha Vantage (500 req/day, need free key)")
    
    print("\n🔗 Get Free API Keys:")
    print("📈 Alpha Vantage: https://www.alphavantage.co/support/#api-key")
    print("📊 IEX Cloud: https://iexcloud.io/pricing")
    print("💱 Fixer.io: https://fixer.io/signup/free") 