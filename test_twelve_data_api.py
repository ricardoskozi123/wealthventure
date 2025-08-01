#!/usr/bin/env python3
"""
Test Twelve Data API Integration
Quick test to verify API key and functionality
"""

import requests
import time

def test_twelve_data_api():
    """Test the Twelve Data API with your key"""
    
    api_key = '902d8585e8c040f591a3293d1b79ab88'
    base_url = 'https://api.twelvedata.com'
    
    # Test symbols across different asset classes
    test_symbols = [
        ('EUR/USD', 'forex'),
        ('BTC/USD', 'crypto'),
        ('XAU/USD', 'commodity'),
        ('AAPL', 'stock')
    ]
    
    print("🧪 Testing Twelve Data API Integration")
    print(f"🔑 API Key: {api_key[:8]}...")
    print("=" * 50)
    
    for symbol, asset_type in test_symbols:
        try:
            print(f"\n📊 Testing {symbol} ({asset_type})...")
            
            url = f'{base_url}/price'
            params = {
                'symbol': symbol,
                'apikey': api_key
            }
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                if 'price' in data:
                    price = float(data['price'])
                    print(f"✅ {symbol}: ${price:,.6f} (response time: {duration:.2f}s)")
                    
                elif 'message' in data:
                    print(f"⚠️  {symbol}: {data['message']}")
                    
                else:
                    print(f"❌ {symbol}: Unexpected response format")
                    print(f"   Response: {data}")
                    
            else:
                print(f"❌ {symbol}: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {str(e)}")
            
        # Small delay between requests
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("🎯 API Test Complete!")

def test_quota_info():
    """Test API quota information"""
    
    api_key = '902d8585e8c040f591a3293d1b79ab88'
    
    try:
        print("\n📊 Checking API Quota...")
        
        url = 'https://api.twelvedata.com/quota'
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Quota Info: {data}")
        else:
            print(f"❌ Quota check failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Quota check error: {str(e)}")

if __name__ == '__main__':
    test_twelve_data_api()
    test_quota_info() 