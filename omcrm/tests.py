import requests


# def get_real_time_price(symbol):
#     api_key = 'J54VFE3RK2YHL5MN'  # Replace with your actual API key
#
#     url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
#     response = requests.get(url)
#     data = response.json()
#     print(data)
#     return float(data['Global Quote']['05. price'])
#
# get_real_time_price('AAPL')

import requests

# def get_crypto_price(symbol):
#     url = f'https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd'
#     response = requests.get(url)
#     data = response.json()
#     print(data)
#     return data[symbol]['usd']
#
# get_crypto_price('bitcoin')

def get_real_time_price(symbol, is_crypto=False):
    api_key = 'cr1pk1pr01qnqk1bbhsgcr1pk1pr01qnqk1bbht0'
    if is_crypto:
        url = f'https://finnhub.io/api/v1/crypto/candle?symbol=BINANCE:{symbol}USDT&resolution=1&token={api_key}'
    else:
        url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}'

    response = requests.get(url)
    data = response.json()
    print(data)
    if is_crypto:
        return data['c'][-1]  # Closing price of the latest candle
    else:
        return data['c']  # Current price
get_real_time_price("BINANCE:BTC/USD",is_crypto=True)
