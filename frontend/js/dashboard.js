/**
 * Dashboard Functions for ESR Foods
 */

let salesTrendChart = null;
let topProductsChart = null;
let topRestaurantsChart = null;
let inventoryDistributionChart = null;

// Initialize dashboard
async function initDashboard() {
    if (!requireAuth()) return;
    
    try {
        // Load dashboard summary
        await loadDashboardSummary();
        
        // Load charts
        await loadDashboardCharts();
        
        // Load 15-day summary
        await load15DaySummary();
        
        // Load outstanding payments
        await loadOutstandingPayments();
        
    } catch (error) {
        console.error('Dashboard initialization error:', error);
        showToast('Failed to load dashboard data', 'error');
    }
}

// Load dashboard summary
async function loadDashboardSummary() {
    try {
        const summary = await dashboardAPI.getSummary();
        
        if (summary) {
            document.getElementById('todaySales').textContent = formatCurrency(summary.today_sales);
            document.getElementById('todayPurchases').textContent = formatCurrency(summary.today_purchases);
            document.getElementById('monthlySales').textContent = formatCurrency(summary.monthly_sales);
            document.getElementById('outstandingReceivables').textContent = formatCurrency(summary.outstanding_receivables);
            document.getElementById('totalStockValue').textContent = formatCurrency(summary.total_stock_value);
            document.getElementById('activeRestaurants').textContent = summary.active_restaurants;
            document.getElementById('lowStockProducts').textContent = summary.low_stock_products;
            document.getElementById('expiringProducts').textContent = summary.expiring_products;
        }
    } catch (error) {
        console.error('Error loading dashboard summary:', error);
    }
}

// Load dashboard charts
async function loadDashboardCharts() {
    try {
        const charts = await dashboardAPI.getCharts();
        
        if (charts) {
            // Sales Trend Chart
            createSalesTrendChart(charts.sales_trend);
            
            // Top Products Chart
            createTopProductsChart(charts.top_products);
            
            // Top Restaurants Chart
            createTopRestaurantsChart(charts.top_restaurants);
            
            // Inventory Distribution Chart
            createInventoryDistributionChart(charts.inventory_distribution);
        }
    } catch (error) {
        console.error('Error loading dashboard charts:', error);
    }
}

// Create Sales Trend Chart
function createSalesTrendChart(data) {
    const ctx = document.getElementById('salesTrendChart');
    if (!ctx) return;
    
    if (salesTrendChart) {
        salesTrendChart.destroy();
    }
    
    salesTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.month),
            datasets: [{
                label: 'Sales',
                data: data.map(item => item.sales),
                borderColor: '#008C95',
                backgroundColor: 'rgba(0, 140, 149, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create Top Products Chart
function createTopProductsChart(data) {
    const ctx = document.getElementById('topProductsChart');
    if (!ctx) return;
    
    if (topProductsChart) {
        topProductsChart.destroy();
    }
    
    topProductsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.name),
            datasets: [{
                label: 'Sales Amount',
                data: data.map(item => item.amount),
                backgroundColor: '#39C6B4',
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create Top Restaurants Chart
function createTopRestaurantsChart(data) {
    const ctx = document.getElementById('topRestaurantsChart');
    if (!ctx) return;
    
    if (topRestaurantsChart) {
        topRestaurantsChart.destroy();
    }
    
    topRestaurantsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.name),
            datasets: [{
                label: 'Sales',
                data: data.map(item => item.sales),
                backgroundColor: '#063B5C',
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create Inventory Distribution Chart
function createInventoryDistributionChart(data) {
    const ctx = document.getElementById('inventoryDistributionChart');
    if (!ctx) return;
    
    if (inventoryDistributionChart) {
        inventoryDistributionChart.destroy();
    }
    
    inventoryDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.category),
            datasets: [{
                data: data.map(item => item.value),
                backgroundColor: [
                    '#063B5C',
                    '#008C95',
                    '#39C6B4',
                    '#FF6B5A',
                    '#F39C12'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Load 15-day summary
async function load15DaySummary() {
    try {
        const summary = await dashboardAPI.get15DaySummary();
        
        if (summary) {
            const container = document.getElementById('fifteenDaySummary');
            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Period</div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${formatDate(summary.period_start)} - ${formatDate(summary.period_end)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Total Sales</div>
                        <div style="font-weight: 600; font-size: 1.1rem; color: var(--success-color);">${formatCurrency(summary.total_sales)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Total Collected</div>
                        <div style="font-weight: 600; font-size: 1.1rem; color: var(--info-color);">${formatCurrency(summary.total_collected)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Total Outstanding</div>
                        <div style="font-weight: 600; font-size: 1.1rem; color: var(--danger-color);">${formatCurrency(summary.total_outstanding)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Collection Rate</div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${summary.collection_rate.toFixed(1)}%</div>
                    </div>
                </div>
                
                <div style="border-top: 1px solid #e0e0e0; padding-top: 20px;">
                    <h4 style="margin-bottom: 15px; color: var(--primary-color);">Restaurant Breakdown</h4>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Restaurant</th>
                                    <th>Orders</th>
                                    <th>Sales</th>
                                    <th>Collected</th>
                                    <th>Outstanding</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${summary.restaurant_breakdown.map(r => `
                                    <tr>
                                        <td>${r.restaurant_name}</td>
                                        <td>${r.orders}</td>
                                        <td>${formatCurrency(r.sales)}</td>
                                        <td>${formatCurrency(r.collected)}</td>
                                        <td style="color: ${r.outstanding > 0 ? 'var(--danger-color)' : 'var(--success-color)'}">${formatCurrency(r.outstanding)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading 15-day summary:', error);
        document.getElementById('fifteenDaySummary').innerHTML = '<p style="color: var(--danger-color);">Failed to load 15-day summary</p>';
    }
}

// Load outstanding payments
async function loadOutstandingPayments() {
    try {
        const restaurants = await restaurantsAPI.getAll();
        
        if (restaurants) {
            const tbody = document.getElementById('outstandingPaymentsTable');
            tbody.innerHTML = restaurants.map(restaurant => {
                const outstanding = restaurant.outstanding_amount || 0;
                const status = outstanding > 0 ? 'Pending' : 'Clear';
                const statusColor = outstanding > 0 ? 'var(--danger-color)' : 'var(--success-color)';
                
                return `
                    <tr>
                        <td>${restaurant.name}</td>
                        <td style="font-weight: 600;">${formatCurrency(outstanding)}</td>
                        <td style="color: ${statusColor}; font-weight: 600;">${status}</td>
                    </tr>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading outstanding payments:', error);
        document.getElementById('outstandingPaymentsTable').innerHTML = '<tr><td colspan="3" style="color: var(--danger-color);">Failed to load outstanding payments</td></tr>';
    }
}

// Refresh 15-day summary
async function refresh15DaySummary() {
    await load15DaySummary();
    showToast('15-day summary refreshed', 'success');
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initDashboard);

// Also call initDashboard immediately in case DOMContentLoaded already fired
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initDashboard();
}
