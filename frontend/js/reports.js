/**
 * Reports Page Functions for ESR Foods
 */

let allRestaurants = [];
let allVendors = [];

// Initialize reports page
async function initReportsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load restaurants for dropdowns
        await loadRestaurantsForDropdown();
        
        // Load vendors for dropdowns
        await loadVendorsForDropdown();
        
        // Set default dates
        setDefaultDates();
        
    } catch (error) {
        console.error('Reports page initialization error:', error);
        showToast('Failed to initialize reports', 'error');
    }
}

// Load restaurants for dropdown
async function loadRestaurantsForDropdown() {
    try {
        allRestaurants = await restaurantsAPI.getAll({ status: true });
        
        const salesRestaurantFilter = document.getElementById('salesRestaurantFilter');
        
        const options = '<option value="">All Restaurants</option>' +
            allRestaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        
        if (salesRestaurantFilter) salesRestaurantFilter.innerHTML = options;
    } catch (error) {
        console.error('Error loading restaurants:', error);
    }
}

// Load vendors for dropdown
async function loadVendorsForDropdown() {
    try {
        allVendors = await vendorsAPI.getAll({ status: true });
        
        const purchasesVendorFilter = document.getElementById('purchasesVendorFilter');
        
        const options = '<option value="">All Vendors</option>' +
            allVendors.map(v => `<option value="${v.id}">${v.name}</option>`).join('');
        
        if (purchasesVendorFilter) purchasesVendorFilter.innerHTML = options;
    } catch (error) {
        console.error('Error loading vendors:', error);
    }
}

// Set default dates for reports
function setDefaultDates() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    // Sales report dates
    document.getElementById('salesStartDate').value = firstDayOfMonth.toISOString().split('T')[0];
    document.getElementById('salesEndDate').value = today.toISOString().split('T')[0];
    
    // Purchases report dates
    document.getElementById('purchasesStartDate').value = firstDayOfMonth.toISOString().split('T')[0];
    document.getElementById('purchasesEndDate').value = today.toISOString().split('T')[0];
    
    // 15-day report dates
    if (today.getDate() <= 15) {
        document.getElementById('15DayStartDate').value = firstDayOfMonth.toISOString().split('T')[0];
        document.getElementById('15DayEndDate').value = new Date(today.getFullYear(), today.getMonth(), 15).toISOString().split('T')[0];
    } else {
        document.getElementById('15DayStartDate').value = new Date(today.getFullYear(), today.getMonth(), 16).toISOString().split('T')[0];
        document.getElementById('15DayEndDate').value = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
    }
    
    // Profit report dates
    document.getElementById('profitStartDate').value = firstDayOfMonth.toISOString().split('T')[0];
    document.getElementById('profitEndDate').value = today.toISOString().split('T')[0];
}

// Show sales report section
function showSalesReport() {
    hideAllReportSections();
    document.getElementById('salesReportSection').style.display = 'block';
}

// Show purchases report section
function showPurchasesReport() {
    hideAllReportSections();
    document.getElementById('purchasesReportSection').style.display = 'block';
}

// Show inventory report section
function showInventoryReport() {
    hideAllReportSections();
    document.getElementById('inventoryReportSection').style.display = 'block';
}

// Show restaurants report section
function showRestaurantsReport() {
    hideAllReportSections();
    document.getElementById('restaurantsReportSection').style.display = 'block';
}

// Show 15-day report section
function show15DayReport() {
    hideAllReportSections();
    document.getElementById('15DayReportSection').style.display = 'block';
}

// Show profit report section
function showProfitReport() {
    hideAllReportSections();
    document.getElementById('profitReportSection').style.display = 'block';
}

// Hide all report sections
function hideAllReportSections() {
    document.getElementById('salesReportSection').style.display = 'none';
    document.getElementById('purchasesReportSection').style.display = 'none';
    document.getElementById('inventoryReportSection').style.display = 'none';
    document.getElementById('restaurantsReportSection').style.display = 'none';
    document.getElementById('15DayReportSection').style.display = 'none';
    document.getElementById('profitReportSection').style.display = 'none';
}

// Generate sales report
async function generateSalesReport() {
    const startDate = document.getElementById('salesStartDate').value;
    const endDate = document.getElementById('salesEndDate').value;
    const restaurantId = document.getElementById('salesRestaurantFilter').value;
    
    const content = document.getElementById('salesReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.getSalesReport(startDate, endDate, restaurantId || null);
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary);">Total Sales</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">${formatCurrency(report.total_sales)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Collected</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--info-color);">${formatCurrency(report.total_collected)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Outstanding</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger-color);">${formatCurrency(report.outstanding)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Invoice Count</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${report.invoice_count}</div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Invoice Number</th>
                                <th>Restaurant</th>
                                <th>Date</th>
                                <th>Total</th>
                                <th>Paid</th>
                                <th>Balance</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${report.invoices.map(inv => `
                                <tr>
                                    <td>${inv.invoice_number}</td>
                                    <td>${inv.restaurant_id}</td>
                                    <td>${formatDate(inv.invoice_date)}</td>
                                    <td>${formatCurrency(inv.grand_total)}</td>
                                    <td>${formatCurrency(inv.amount_paid)}</td>
                                    <td>${formatCurrency(inv.balance_due)}</td>
                                    <td><span class="badge badge-info">${inv.payment_status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating sales report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate sales report</p>';
    }
}

// Generate purchases report
async function generatePurchasesReport() {
    const startDate = document.getElementById('purchasesStartDate').value;
    const endDate = document.getElementById('purchasesEndDate').value;
    const vendorId = document.getElementById('purchasesVendorFilter').value;
    
    const content = document.getElementById('purchasesReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.getPurchasesReport(startDate, endDate, vendorId || null);
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary);">Total Purchases</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${formatCurrency(report.total_purchases)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Purchase Count</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${report.purchase_count}</div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Purchase Code</th>
                                <th>Vendor</th>
                                <th>Date</th>
                                <th>Total</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${report.purchases.map(pur => `
                                <tr>
                                    <td>${pur.purchase_code}</td>
                                    <td>${pur.vendor_id}</td>
                                    <td>${formatDate(pur.purchase_date)}</td>
                                    <td>${formatCurrency(pur.total)}</td>
                                    <td><span class="badge badge-info">${pur.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating purchases report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate purchases report</p>';
    }
}

// Generate inventory report
async function generateInventoryReport() {
    const content = document.getElementById('inventoryReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.getInventoryReport();
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary);">Total Products</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${report.total_products}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Stock Value</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${formatCurrency(report.total_stock_value)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Low Stock Items</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--warning-color);">${report.low_stock_count}</div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Stock</th>
                                <th>Unit</th>
                                <th>Purchase Price</th>
                                <th>Selling Price</th>
                                <th>Stock Value</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${report.products.map(prod => `
                                <tr>
                                    <td>${prod.name}</td>
                                    <td style="color: ${prod.is_low_stock ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">${prod.current_stock}</td>
                                    <td>${prod.unit}</td>
                                    <td>${formatCurrency(prod.purchase_price)}</td>
                                    <td>${formatCurrency(prod.selling_price)}</td>
                                    <td>${formatCurrency(prod.stock_value)}</td>
                                    <td>
                                        ${prod.is_low_stock ? '<span class="badge badge-warning">Low Stock</span>' : '<span class="badge badge-success">Normal</span>'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating inventory report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate inventory report</p>';
    }
}

// Generate restaurants report
async function generateRestaurantsReport() {
    const content = document.getElementById('restaurantsReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.getRestaurantsReport();
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="margin-bottom: 20px;">
                    <div style="color: var(--text-secondary);">Total Restaurants</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">${report.total_restaurants}</div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Restaurant</th>
                                <th>Area</th>
                                <th>Credit Limit</th>
                                <th>Total Sales</th>
                                <th>Total Payments</th>
                                <th>Outstanding</th>
                                <th>Credit Usage</th>
                                <th>Orders</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${report.restaurants.map(r => `
                                <tr>
                                    <td>${r.restaurant_name}</td>
                                    <td>${r.area}</td>
                                    <td>${formatCurrency(r.credit_limit)}</td>
                                    <td>${formatCurrency(r.total_sales)}</td>
                                    <td>${formatCurrency(r.total_payments)}</td>
                                    <td style="color: ${r.outstanding > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">${formatCurrency(r.outstanding)}</td>
                                    <td>${r.credit_usage_percent.toFixed(1)}%</td>
                                    <td>${r.order_count}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating restaurants report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate restaurants report</p>';
    }
}

// Generate 15-day report
async function generate15DayReport() {
    const startDate = document.getElementById('15DayStartDate').value;
    const endDate = document.getElementById('15DayEndDate').value;
    
    const content = document.getElementById('15DayReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.get15DaySummary(startDate, endDate);
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary);">Period</div>
                        <div style="font-weight: 600;">${formatDate(report.period_start)} - ${formatDate(report.period_end)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Sales</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">${formatCurrency(report.total_sales)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Collected</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--info-color);">${formatCurrency(report.total_collected)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Outstanding</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger-color);">${formatCurrency(report.total_outstanding)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Collection Rate</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${report.collection_rate.toFixed(1)}%</div>
                    </div>
                </div>
                
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
                            ${report.restaurants.map(r => `
                                <tr>
                                    <td>${r.restaurant_name}</td>
                                    <td>${r.orders}</td>
                                    <td>${formatCurrency(r.sales)}</td>
                                    <td>${formatCurrency(r.collected)}</td>
                                    <td style="color: ${r.outstanding > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">${formatCurrency(r.outstanding)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating 15-day report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate 15-day report</p>';
    }
}

// Generate profit report
async function generateProfitReport() {
    const startDate = document.getElementById('profitStartDate').value;
    const endDate = document.getElementById('profitEndDate').value;
    
    const content = document.getElementById('profitReportContent');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const report = await reportsAPI.getProfitReport(startDate, endDate);
        
        content.innerHTML = `
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <div style="color: var(--text-secondary);">Period</div>
                        <div style="font-weight: 600;">${formatDate(report.period_start)} - ${formatDate(report.period_end)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Revenue</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">${formatCurrency(report.total_revenue)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Purchases (COGS)</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger-color);">${formatCurrency(report.total_purchases)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Total Expenses</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger-color);">${formatCurrency(report.total_expenses)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Gross Profit</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: ${report.gross_profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)'};">${formatCurrency(report.gross_profit)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Net Profit</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: ${report.net_profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)'};">${formatCurrency(report.net_profit)}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary);">Gross Margin</div>
                        <div style="font-size: 1.5rem; font-weight: 700;">${report.gross_margin.toFixed(1)}%</div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error generating profit report:', error);
        content.innerHTML = '<p style="color: var(--danger-color);">Failed to generate profit report</p>';
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initReportsPage);
