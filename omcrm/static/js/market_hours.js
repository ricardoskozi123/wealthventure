/**
 * Market Hours JavaScript Module for Wealth Venture
 * =================================================
 * 
 * Handles market status checking and trading restrictions on the frontend
 */

class MarketHoursChecker {
    constructor() {
        this.apiBaseUrl = '/api/market';
        this.statusCache = null;
        this.cacheExpiry = null;
        this.cacheTimeout = 60000; // 1 minute cache
        this.checkInterval = null;
    }

    /**
     * Get current market status from API
     */
    async getMarketStatus(extendedHours = false) {
        try {
            // Check cache first
            if (this.statusCache && this.cacheExpiry && Date.now() < this.cacheExpiry) {
                return this.statusCache;
            }

            const url = `${this.apiBaseUrl}/status?extended_hours=${extendedHours}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const status = await response.json();
            
            // Cache the result
            this.statusCache = status;
            this.cacheExpiry = Date.now() + this.cacheTimeout;
            
            return status;
        } catch (error) {
            console.error('Error fetching market status:', error);
            return {
                is_open: false,
                trading_allowed: false,
                status: 'ERROR',
                message: 'Unable to check market status',
                error: error.message
            };
        }
    }

    /**
     * Simple check if trading is allowed
     */
    async canTrade(extendedHours = false) {
        try {
            const url = `${this.apiBaseUrl}/can_trade?extended_hours=${extendedHours}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error checking trading status:', error);
            return {
                can_trade: false,
                reason: `Error: ${error.message}`,
                extended_hours_enabled: extendedHours
            };
        }
    }

    /**
     * Update market status display on page
     */
    async updateMarketStatusDisplay(elementId = 'market-status', extendedHours = false) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const status = await this.getMarketStatus(extendedHours);
        
        // Clear previous classes
        element.className = element.className.replace(/market-\w+/g, '');
        
        // Add status-specific class and content
        if (status.trading_allowed) {
            element.classList.add('market-open');
            element.innerHTML = `
                <i class="fas fa-circle text-success"></i>
                <span class="text-success">Market Open</span>
                <small class="text-muted">${status.session || 'REGULAR'}</small>
            `;
        } else {
            element.classList.add('market-closed');
            element.innerHTML = `
                <i class="fas fa-circle text-danger"></i>
                <span class="text-danger">Market Closed</span>
                <small class="text-muted">${status.message}</small>
            `;
        }

        // Add tooltip with detailed info
        element.title = `${status.message}\nCurrent Time: ${status.current_time_et || 'Unknown'}`;
        
        return status;
    }

    /**
     * Show/hide trading buttons based on market status
     */
    async toggleTradingControls(extendedHours = false) {
        const status = await this.canTrade(extendedHours);
        
        // Find all trading buttons
        const tradingButtons = document.querySelectorAll('.trading-btn, [data-trading-action]');
        
        tradingButtons.forEach(button => {
            if (status.can_trade) {
                button.disabled = false;
                button.classList.remove('disabled');
                button.title = 'Trading is allowed';
            } else {
                button.disabled = true;
                button.classList.add('disabled');
                button.title = `Trading disabled: ${status.reason}`;
            }
        });

        return status;
    }

    /**
     * Show market closed modal/alert
     */
    showMarketClosedAlert(status) {
        const alertHtml = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Market Closed</strong> - ${status.reason}
                ${status.next_open ? `<br><small>Next open: ${status.next_open}</small>` : ''}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Add to alerts container or create one
        let alertContainer = document.getElementById('market-alerts');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'market-alerts';
            alertContainer.className = 'market-alerts-container';
            document.body.insertBefore(alertContainer, document.body.firstChild);
        }
        
        alertContainer.innerHTML = alertHtml;
    }

    /**
     * Start automatic market status checking
     */
    startAutoCheck(intervalMinutes = 1, extendedHours = false) {
        // Clear existing interval
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }

        // Update immediately
        this.updateMarketStatusDisplay('market-status', extendedHours);
        this.toggleTradingControls(extendedHours);

        // Set up recurring check
        this.checkInterval = setInterval(async () => {
            await this.updateMarketStatusDisplay('market-status', extendedHours);
            await this.toggleTradingControls(extendedHours);
        }, intervalMinutes * 60 * 1000);
    }

    /**
     * Stop automatic checking
     */
    stopAutoCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    /**
     * Validate trading action before execution
     */
    async validateTradingAction(action, extendedHours = false) {
        const status = await this.canTrade(extendedHours);
        
        if (!status.can_trade) {
            this.showMarketClosedAlert(status);
            return false;
        }
        
        return true;
    }
}

// Global instance
window.marketChecker = new MarketHoursChecker();

// jQuery integration for existing code
if (typeof $ !== 'undefined') {
    $(document).ready(function() {
        // Auto-start market checking if market status element exists
        if ($('#market-status').length > 0) {
            window.marketChecker.startAutoCheck(1); // Check every minute
        }

        // Intercept trading form submissions
        $('form[data-trading-form]').on('submit', async function(e) {
            const extendedHours = $(this).data('extended-hours') === true;
            const isValid = await window.marketChecker.validateTradingAction('trade', extendedHours);
            
            if (!isValid) {
                e.preventDefault();
                return false;
            }
        });

        // Intercept trading button clicks
        $('.trading-btn, [data-trading-action]').on('click', async function(e) {
            const extendedHours = $(this).data('extended-hours') === true;
            const isValid = await window.marketChecker.validateTradingAction('trade', extendedHours);
            
            if (!isValid) {
                e.preventDefault();
                return false;
            }
        });
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarketHoursChecker;
}
