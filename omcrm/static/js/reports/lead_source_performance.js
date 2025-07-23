document.addEventListener('DOMContentLoaded', function() {
    // Check if reportData is available from the template
    if (!window.reportData) {
        console.error('Report data not available');
        return;
    }
    
    // Extract data using bracket notation to ensure compatibility
    const sourceLabels = window.reportData["sourceLabels"] || [];
    const leadsData = window.reportData["leadsData"] || [];
    const conversionRates = window.reportData["conversionRates"] || [];
    const revenueData = window.reportData["revenueData"] || [];
    const currencySymbol = window.reportData["currencySymbol"] || '$';
    
    // Initialize charts
    initializeCharts();
    
    // Setup event listeners for period selector
    setupEventListeners();
    
    function initializeCharts() {
        // Lead Source Distribution Chart
        const leadSourceCtx = document.getElementById('leadSourceChart');
        if (leadSourceCtx) {
            new Chart(leadSourceCtx.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: sourceLabels,
                    datasets: [{
                        data: leadsData,
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(153, 102, 255, 0.8)',
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(255, 159, 64, 0.8)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${value} leads (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Conversion Rate Chart
        const conversionCtx = document.getElementById('conversionRateChart');
        if (conversionCtx) {
            new Chart(conversionCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: sourceLabels,
                    datasets: [{
                        label: 'Conversion Rate (%)',
                        data: conversionRates,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Conversion Rate: ' + context.raw.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Revenue by Source Chart
        const revenueCtx = document.getElementById('revenueBySourceChart');
        if (revenueCtx) {
            new Chart(revenueCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: sourceLabels,
                    datasets: [{
                        label: 'Revenue',
                        data: revenueData,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return currencySymbol + value.toLocaleString();
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Revenue: ' + currencySymbol + context.raw.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    function setupEventListeners() {
        // Period selector
        const periodSelector = document.getElementById('periodSelector');
        if (periodSelector) {
            periodSelector.addEventListener('change', function() {
                // In a real implementation, this would fetch new data from the server
                console.log('Selected period:', this.value);
            });
        }
        
        // Source filter
        const sourceFilters = document.querySelectorAll('.source-filter');
        sourceFilters.forEach(function(filter) {
            filter.addEventListener('change', function() {
                // This would filter the displayed data based on the selection
                console.log('Source filter changed:', this.value, this.checked);
            });
        });
    }
    
    // Initialize feather icons if available
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}); 