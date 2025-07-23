/**
 * Report Data Handler - Utility for handling data passed from templates to JavaScript
 * 
 * This script provides a consistent way to extract data from window.reportData
 * and handle errors if data is not properly formatted.
 */

class ReportDataHandler {
    /**
     * Initialize the handler with data from window.reportData
     */
    constructor() {
        if (!window.reportData) {
            console.error('Report data not available');
            this.data = {};
            this.available = false;
            return;
        }
        
        this.data = window.reportData;
        this.available = true;
    }
    
    /**
     * Get a value from the report data
     * @param {string} key - The key to retrieve
     * @param {any} defaultValue - Default value if key doesn't exist
     * @returns {any} The value or default
     */
    get(key, defaultValue = []) {
        if (!this.available) return defaultValue;
        
        // Try different access patterns since templates may have different quoting
        if (this.data[key] !== undefined) {
            return this.data[key];
        }
        
        // Try with quoted key (when template uses unquoted keys)
        if (key in this.data) {
            return this.data[key];
        }
        
        return defaultValue;
    }
    
    /**
     * Get a numeric value, ensuring it's properly converted
     * @param {string} key - The key to retrieve
     * @param {number} defaultValue - Default value if key doesn't exist
     * @returns {number} The numeric value or default
     */
    getNumber(key, defaultValue = 0) {
        const value = this.get(key, null);
        if (value === null) return defaultValue;
        
        const num = Number(value);
        return isNaN(num) ? defaultValue : num;
    }
    
    /**
     * Get a string value
     * @param {string} key - The key to retrieve
     * @param {string} defaultValue - Default value if key doesn't exist
     * @returns {string} The string value or default
     */
    getString(key, defaultValue = '') {
        const value = this.get(key, null);
        if (value === null) return defaultValue;
        return String(value);
    }
    
    /**
     * Get all available keys in the data
     * @returns {string[]} Array of keys
     */
    getKeys() {
        if (!this.available) return [];
        return Object.keys(this.data);
    }
    
    /**
     * Check if data contains a specific key
     * @param {string} key - The key to check
     * @returns {boolean} True if key exists
     */
    has(key) {
        if (!this.available) return false;
        return key in this.data || this.data[key] !== undefined;
    }
}

// Make available globally
window.ReportDataHandler = ReportDataHandler; 