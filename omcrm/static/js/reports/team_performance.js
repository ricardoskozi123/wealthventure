document.addEventListener('DOMContentLoaded', function() {
    // Check if reportData is available from the template
    if (!window.reportData) {
        console.error('Report data not available');
        return;
    }
    
    // Extract data using bracket notation to ensure compatibility
    const users = window.reportData["users"] || [];
    const teams = window.reportData["teams"] || [];
    const revenueByUser = window.reportData["revenueByUser"] || [];
    const revenueByTeam = window.reportData["revenueByTeam"] || [];
    const dealCountByUser = window.reportData["dealCountByUser"] || [];
    const conversionRateByUser = window.reportData["conversionRateByUser"] || [];
    const avgDealSizeByUser = window.reportData["avgDealSizeByUser"] || [];
    const currencySymbol = window.reportData["currencySymbol"] || '$';
    
    // Initialize charts
    initializeCharts();
    
    // Setup event listeners for time period selector
    setupEventListeners();
    
    function initializeCharts() {
        // Revenue by team chart
        const teamRevenueCtx = document.getElementById('teamRevenueChart');
        if (teamRevenueCtx) {
            new Chart(teamRevenueCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: teams,
                    datasets: [{
                        label: 'Revenue',
                        data: revenueByTeam,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Revenue: ' + currencySymbol + context.raw.toLocaleString();
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
        
        // Revenue by user chart
        const userRevenueCtx = document.getElementById('userRevenueChart');
        if (userRevenueCtx) {
            new Chart(userRevenueCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: users,
                    datasets: [{
                        label: 'Revenue',
                        data: revenueByUser,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
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
                                    return 'Revenue: ' + currencySymbol + context.raw.toLocaleString();
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
        
        // Deal count by user chart
        const dealCountCtx = document.getElementById('dealCountChart');
        if (dealCountCtx) {
            new Chart(dealCountCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: users,
                    datasets: [{
                        label: 'Deals Closed',
                        data: dealCountByUser,
                        backgroundColor: 'rgba(255, 159, 64, 0.6)',
                        borderColor: 'rgba(255, 159, 64, 1)',
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
                                    return 'Deals: ' + context.raw;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Conversion rate by user chart
        const conversionRateCtx = document.getElementById('conversionRateChart');
        if (conversionRateCtx) {
            new Chart(conversionRateCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: users,
                    datasets: [{
                        label: 'Conversion Rate',
                        data: conversionRateByUser,
                        backgroundColor: 'rgba(153, 102, 255, 0.6)',
                        borderColor: 'rgba(153, 102, 255, 1)',
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
                                    return 'Conversion Rate: ' + context.raw.toFixed(1) + '%';
                                }
                            }
                        }
                    },
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
                    }
                }
            });
        }
    }
    
    function setupEventListeners() {
        // Time period selector
        const timePeriodSelector = document.getElementById('timePeriodSelector');
        if (timePeriodSelector) {
            timePeriodSelector.addEventListener('change', function() {
                // In a real implementation, this would update the data based on the selected period
                console.log('Selected time period:', this.value);
            });
        }
        
        // Team filter
        const teamFilter = document.getElementById('teamFilter');
        if (teamFilter) {
            teamFilter.addEventListener('change', function() {
                // In a real implementation, this would filter by team
                console.log('Selected team filter:', this.value);
            });
        }
    }
    
    // Initialize feather icons if available
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}); 