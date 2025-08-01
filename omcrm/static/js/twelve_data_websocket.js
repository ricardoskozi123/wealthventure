/**
 * Twelve Data WebSocket Integration
 * Real-time price feeds for Forex, Crypto, Commodities, and Stocks
 * Pro Plan: 500 WebSocket Credits
 */

class TwelveDataWebSocket {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.ws = null;
        this.subscribedSymbols = new Set();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        this.callbacks = new Map();
        
        // Twelve Data WebSocket URL
        this.wsUrl = 'wss://ws.twelvedata.com/v1/quotes/price';
    }

    /**
     * Initialize WebSocket connection
     */
    connect() {
        try {
            console.log('🔌 Connecting to Twelve Data WebSocket...');
            
            this.ws = new WebSocket(`${this.wsUrl}?apikey=${this.apiKey}`);
            
            this.ws.onopen = (event) => {
                console.log('✅ Connected to Twelve Data WebSocket');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Re-subscribe to previously subscribed symbols
                this.resubscribeAll();
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };
            
            this.ws.onclose = (event) => {
                console.log('❌ WebSocket connection closed:', event.code, event.reason);
                this.isConnected = false;
                this.handleReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('🚨 WebSocket error:', error);
                this.isConnected = false;
            };
            
        } catch (error) {
            console.error('❌ Failed to connect to WebSocket:', error);
            this.handleReconnect();
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            
            if (message.event === 'price') {
                this.handlePriceUpdate(message);
            } else if (message.event === 'subscribe-status') {
                this.handleSubscriptionStatus(message);
            } else if (message.event === 'heartbeat') {
                // Keep connection alive
                console.log('💓 Heartbeat received');
            }
            
        } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error, data);
        }
    }

    /**
     * Handle price updates
     */
    handlePriceUpdate(message) {
        const { symbol, price, timestamp } = message;
        
        console.log(`📈 Price update: ${symbol} = ${price}`);
        
        // Trigger callbacks for this symbol
        const callback = this.callbacks.get(symbol);
        if (callback) {
            callback({
                symbol,
                price: parseFloat(price),
                timestamp: new Date(timestamp)
            });
        }
        
        // Update UI elements
        this.updateInstrumentUI(symbol, price);
        this.updateMarketTicker(symbol, price);
    }

    /**
     * Handle subscription status
     */
    handleSubscriptionStatus(message) {
        const { symbol, status } = message;
        
        if (status === 'ok') {
            console.log(`✅ Successfully subscribed to ${symbol}`);
            this.subscribedSymbols.add(symbol);
        } else {
            console.error(`❌ Failed to subscribe to ${symbol}:`, message);
        }
    }

    /**
     * Subscribe to price updates for a symbol
     */
    subscribe(symbol, callback = null) {
        if (!this.isConnected) {
            console.log(`⏳ Queuing subscription for ${symbol} (not connected)`);
            this.subscribedSymbols.add(symbol);
            if (callback) this.callbacks.set(symbol, callback);
            return;
        }

        try {
            const subscribeMessage = {
                action: 'subscribe',
                params: {
                    symbols: symbol
                }
            };
            
            console.log(`📡 Subscribing to ${symbol}...`);
            this.ws.send(JSON.stringify(subscribeMessage));
            
            if (callback) {
                this.callbacks.set(symbol, callback);
            }
            
        } catch (error) {
            console.error(`❌ Failed to subscribe to ${symbol}:`, error);
        }
    }

    /**
     * Unsubscribe from a symbol
     */
    unsubscribe(symbol) {
        if (!this.isConnected) return;

        try {
            const unsubscribeMessage = {
                action: 'unsubscribe',
                params: {
                    symbols: symbol
                }
            };
            
            console.log(`📡 Unsubscribing from ${symbol}...`);
            this.ws.send(JSON.stringify(unsubscribeMessage));
            
            this.subscribedSymbols.delete(symbol);
            this.callbacks.delete(symbol);
            
        } catch (error) {
            console.error(`❌ Failed to unsubscribe from ${symbol}:`, error);
        }
    }

    /**
     * Re-subscribe to all symbols after reconnection
     */
    resubscribeAll() {
        console.log(`🔄 Re-subscribing to ${this.subscribedSymbols.size} symbols...`);
        
        for (const symbol of this.subscribedSymbols) {
            setTimeout(() => {
                this.subscribe(symbol, this.callbacks.get(symbol));
            }, 100); // Small delay between subscriptions
        }
    }

    /**
     * Handle reconnection logic
     */
    handleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached. Giving up.');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`🔄 Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Update instrument price in the UI
     */
    updateInstrumentUI(symbol, price) {
        // Update trading instruments list
        const instrumentElements = document.querySelectorAll(`[data-symbol="${symbol}"]`);
        
        instrumentElements.forEach(element => {
            const priceElement = element.querySelector('.instrument-price, .price-value');
            if (priceElement) {
                const oldPrice = parseFloat(priceElement.textContent) || 0;
                const newPrice = parseFloat(price);
                
                // Update price
                priceElement.textContent = newPrice.toFixed(getInstrumentPrecision(symbol));
                
                // Add price change animation
                const changeClass = newPrice > oldPrice ? 'price-up' : newPrice < oldPrice ? 'price-down' : '';
                if (changeClass) {
                    priceElement.classList.remove('price-up', 'price-down');
                    priceElement.classList.add(changeClass);
                    
                    setTimeout(() => {
                        priceElement.classList.remove(changeClass);
                    }, 1000);
                }
            }
        });
        
        // Update current instrument if it matches
        if (window.currentInstrument && window.currentInstrument.symbol === symbol) {
            window.currentInstrument.price = parseFloat(price);
            updateInstrumentPriceAndUI();
        }
    }

    /**
     * Update market ticker
     */
    updateMarketTicker(symbol, price) {
        const tickerItems = document.querySelectorAll('.ticker-item');
        
        tickerItems.forEach(item => {
            const symbolElement = item.querySelector('.ticker-symbol');
            const priceElement = item.querySelector('.ticker-price');
            
            if (symbolElement && symbolElement.textContent === symbol && priceElement) {
                const oldPrice = parseFloat(priceElement.textContent) || 0;
                const newPrice = parseFloat(price);
                
                priceElement.textContent = newPrice.toFixed(getInstrumentPrecision(symbol));
                
                // Update change indicator
                const changeElement = item.querySelector('.ticker-change');
                if (changeElement && oldPrice > 0) {
                    const change = ((newPrice - oldPrice) / oldPrice) * 100;
                    const changeClass = change >= 0 ? 'positive' : 'negative';
                    const changeSymbol = change >= 0 ? '+' : '';
                    
                    changeElement.textContent = `${changeSymbol}${change.toFixed(2)}%`;
                    changeElement.className = `ticker-change ${changeClass}`;
                }
            }
        });
    }

    /**
     * Subscribe to multiple instruments at once
     */
    subscribeToInstruments(instruments) {
        console.log(`📡 Subscribing to ${instruments.length} instruments...`);
        
        instruments.forEach((instrument, index) => {
            // Small delay between subscriptions to avoid rate limiting
            setTimeout(() => {
                this.subscribe(instrument.symbol, (data) => {
                    console.log(`💰 ${data.symbol}: ${data.price}`);
                    
                    // Update database via API call
                    fetch('/webtrader/update_price', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            symbol: data.symbol,
                            price: data.price
                        })
                    }).catch(error => {
                        console.error('Failed to update price in database:', error);
                    });
                });
            }, index * 100); // 100ms delay between each subscription
        });
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        console.log('🔌 Disconnecting from WebSocket...');
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
        this.subscribedSymbols.clear();
        this.callbacks.clear();
    }

    /**
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            subscribedSymbols: Array.from(this.subscribedSymbols),
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

/**
 * Helper function to get instrument precision
 */
function getInstrumentPrecision(symbol) {
    // Forex pairs typically have 5 decimal places
    if (symbol.includes('/') && symbol.length <= 7) {
        return 5;
    }
    
    // Crypto typically needs 6 decimal places
    if (symbol.includes('BTC') || symbol.includes('ETH') || symbol.includes('ADA')) {
        return 6;
    }
    
    // Commodities and stocks typically 2 decimal places
    return 2;
}

/**
 * Initialize WebSocket when page loads
 */
document.addEventListener('DOMContentLoaded', function() {
    // Your actual Twelve Data API key
    const apiKey = '902d8585e8c040f591a3293d1b79ab88';
    
    if (apiKey && apiKey !== 'YOUR_TWELVE_DATA_API_KEY') {
        console.log('🚀 Initializing Twelve Data WebSocket...');
        console.log('⚠️  Note: This is supplementary to the existing price worker system');
        
        // Create global WebSocket instance
        window.twelveDataWS = new TwelveDataWebSocket(apiKey);
        
        // Connect
        window.twelveDataWS.connect();
        
        // Subscribe to all instruments on the page
        if (typeof instrumentsData !== 'undefined') {
            const allInstruments = Object.values(instrumentsData).flat();
            window.twelveDataWS.subscribeToInstruments(allInstruments);
        }
        
        // Add connection status indicator
        setTimeout(() => {
            const status = window.twelveDataWS.getStatus();
            console.log('📊 WebSocket Status:', status);
        }, 5000);
        
    } else {
        console.warn('⚠️ Twelve Data API key not configured. Real-time prices disabled.');
        console.log('💡 Using existing price worker system for price updates');
    }
});

// Add CSS for price change animations
const style = document.createElement('style');
style.textContent = `
    .price-up {
        color: #28a745 !important;
        animation: priceFlash 1s ease-in-out;
    }
    
    .price-down {
        color: #dc3545 !important;
        animation: priceFlash 1s ease-in-out;
    }
    
    @keyframes priceFlash {
        0% { background-color: transparent; }
        50% { background-color: rgba(255, 255, 0, 0.3); }
        100% { background-color: transparent; }
    }
    
    .ticker-change.positive {
        color: #28a745;
    }
    
    .ticker-change.negative {
        color: #dc3545;
    }
`;
document.head.appendChild(style); 