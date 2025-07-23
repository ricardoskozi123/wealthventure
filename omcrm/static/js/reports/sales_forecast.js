document.addEventListener('DOMContentLoaded', function() {
    // Check if reportData is available from the template
    if (!window.reportData) {
        console.error('Report data not available');
        return;
    }
    
    // Get data from the window object (works with both quoted and unquoted keys)
    const historicalLabels = window.reportData.historicalLabels || window.reportData["historicalLabels"] || [];
    const historicalData = window.reportData.historicalData || window.reportData["historicalData"] || [];
    const quarterlyLabels = window.reportData.quarterlyLabels || window.reportData["quarterlyLabels"] || [];
    const quarterlyData = window.reportData.quarterlyData || window.reportData["quarterlyData"] || [];
    const forecastLabels = window.reportData.forecastLabels || window.reportData["forecastLabels"] || [];
    const forecastData = window.reportData.forecastData || window.reportData["forecastData"] || [];
    const quarterlyForecastLabels = window.reportData.quarterlyForecastLabels || window.reportData["quarterlyForecastLabels"] || [];
    const quarterlyForecastData = window.reportData.quarterlyForecastData || window.reportData["quarterlyForecastData"] || [];
    const stageLabels = window.reportData.stageLabels || window.reportData["stageLabels"] || [];
    const stagePotentialData = window.reportData.stagePotentialData || window.reportData["stagePotentialData"] || [];
    const stageProbabilities = window.reportData.stageProbabilities || window.reportData["stageProbabilities"] || [];
    const currencySymbol = window.reportData.currencySymbol || window.reportData["currencySymbol"] || '$';
    
    // View state
    let isMonthlyView = true;
    
    // Chart instances
    let salesForecastChart;
    let dealStageChart;
    
    // Initialize charts
    function initCharts() {
        // Sales Forecast Chart
        const salesForecastCtx = document.getElementById('salesForecastChart').getContext('2d');
        salesForecastChart = new Chart(salesForecastCtx, {
            type: 'line',
            data: getSalesForecastData(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + currencySymbol + context.raw.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return currencySymbol + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
        
        // Deal Stage Probability Chart
        const dealStageCtx = document.getElementById('dealStageProbabilityChart').getContext('2d');
        dealStageChart = new Chart(dealStageCtx, {
            type: 'bar',
            data: {
                labels: stageLabels,
                datasets: [{
                    label: 'Potential Revenue',
                    data: stagePotentialData,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                return [
                                    'Potential: ' + currencySymbol + context.raw.toLocaleString(),
                                    'Probability: ' + stageProbabilities[index] + '%'
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return currencySymbol + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Get the appropriate data based on the current view
    function getSalesForecastData() {
        return {
            labels: isMonthlyView ? 
                historicalLabels.concat(forecastLabels) : 
                quarterlyLabels.concat(quarterlyForecastLabels),
            datasets: [{
                label: 'Historical Sales',
                data: isMonthlyView ? historicalData : quarterlyData,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true
            }, {
                label: 'Forecast Sales',
                data: isMonthlyView ? 
                    Array(historicalLabels.length).fill(null).concat(forecastData) : 
                    Array(quarterlyLabels.length).fill(null).concat(quarterlyForecastData),
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderDash: [5, 5],
                tension: 0.1,
                fill: true
            }]
        };
    }
    
    // Switch between monthly and quarterly views
    function toggleView() {
        isMonthlyView = !isMonthlyView;
        
        // Update button text
        const toggleBtn = document.getElementById('toggleViewBtn');
        toggleBtn.textContent = isMonthlyView ? 'Switch to Quarterly' : 'Switch to Monthly';
        
        // Update chart data
        salesForecastChart.data = getSalesForecastData();
        salesForecastChart.update();
    }
    
    // Initialize toggle button
    const toggleBtn = document.getElementById('toggleViewBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleView);
    }
    
    // Initialize dropdown functionality
    const timeframeDropdown = document.getElementById('timeframeDropdown');
    if (timeframeDropdown) {
        timeframeDropdown.addEventListener('change', function() {
            // Here you would adjust the data based on the selected timeframe
            // For the demo, we'll just log the selection
            console.log('Selected timeframe:', this.value);
        });
    }
    
    // Initialize feather icons if available
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Initialize the charts
    initCharts();
}); 