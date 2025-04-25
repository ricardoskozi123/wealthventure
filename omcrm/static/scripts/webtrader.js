document.addEventListener('DOMContentLoaded', function() {
    initializeTradingView(); // Initialize the chart on page load
    updateInstrument(); // Initialize with the first instrument
});

function initializeTradingView() {
    new TradingView.widget({
        container_id: "tradingview_chart",
        autosize: true,
        symbol: "BTCUSD",
        interval: "D",
        timezone: "Etc/UTC",
        theme: "light",
        style: "1",
        locale: "en",
        toolbar_bg: "#f1f3f6",
        enable_publishing: false,
        allow_symbol_change: true,
        details: true,
        hotlist: true,
        calendar: true,
        news: ["headlines"],
        studies: ["BB@tv-basicstudies"]
    });
}

function updateInstrument() {
    const instrumentId = document.getElementById('instrument_id').value;
    fetch(`/get_instrument_details?instrument_id=${instrumentId}`)
        .then(response => response.json())
        .then(data => {
            updateTradingViewWidget(data.symbol);
            document.getElementById('price').value = data.current_price;
        })
        .catch(error => console.error('Error fetching instrument details:', error));
}

function updateTradingViewWidget(symbol) {
    new TradingView.widget({
        symbol: symbol,
        container_id: "tradingview_chart",
        autosize: true,
        interval: "D",
        timezone: "Etc/UTC",
        theme: "light",
        style: "1",
        locale: "en",
        toolbar_bg: "#f1f3f6",
        enable_publishing: false,
        allow_symbol_change: true,
        details: true,
        hotlist: true,
        calendar: true,
        news: ["headlines"],
        studies: ["BB@tv-basicstudies"]
    });
}