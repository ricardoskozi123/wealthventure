#!/usr/bin/env python3
"""
Simplified version of the Flask app without Socket.IO complications
This will run the WebTrader with basic WebSocket functionality
"""

import os
from omcrm import create_app

# Temporarily disable Socket.IO to avoid WSGI environment issues
os.environ['DISABLE_SOCKETIO'] = '1'

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting WebTrader without Socket.IO complications...")
    print("📱 WebSocket real-time data will work via HTTP polling")
    print("🌐 Access at: http://127.0.0.1:5000")
    print("-" * 50)
    
    app.run(debug=True, host='127.0.0.1', port=5000) 