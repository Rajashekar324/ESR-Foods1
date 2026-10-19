/**
 * Restaurants Page Functions for ESR Foods
 */

let allRestaurants = [];
let allAreas = [];

// Initialize restaurants page
async function initRestaurantsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load restaurants
        await loadRestaurants();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Restaurants page initialization error:', error);
        showToast('Failed to load restaurants', 'error');
    }
}

// Load restaurants
async function loadRestaurants() {
    try {
        const search = document.getElementById('searchInput').value;
        const area = document.getElementById('areaFilter').value;
        const type = document.getElementById('typeFilter').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (search) params.search = search;
        if (area) params.area = area;
        if (type) params.restaurant_type = type;
        if (status) params.status = status === 'true';
        
        allRestaurants = await restaurantsAPI.getAll(params);
        
        // Extract unique areas for filter
        allAreas = [...new Set(allRestaurants.filter(r => r.area).map(r => r.area))];
        
        // Update area filter
        const areaFilter = document.getElementById('areaFilter');
        const currentArea = areaFilter.value;
        areaFilter.innerHTML = '<option value="">All Areas</option>' +
            allAreas.map(a => `<option value="${a}">${a}</option>`).join('');
        areaFilter.value = currentArea;
        
        renderRestaurantsTable();
    } catch (error) {
        console.error('Error loading restaurants:', error);
        document.getElementById('restaurantsTable').innerHTML = '<tr><td colspan="9" style="color: var(--danger-color);">Failed to load restaurants</td></tr>';
    }
}

// Render restaurants table
async function renderRestaurantsTable() {
    const tbody = document.getElementById('restaurantsTable');
    
    if (!allRestaurants || allRestaurants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><div class="empty-state-icon">🍽️</div><div class="empty-state-text">No restaurants found</div></td></tr>';
        return;
    }
    
    // Get summary for each restaurant
    const restaurantData = await Promise.all(allRestaurants.map(async (restaurant) => {
        try {
            const summary = await restaurantsAPI.getSummary(restaurant.id);
            return { ...restaurant, summary };
        } catch (error) {
            console.error('Error loading restaurant summary:', error);
            return { ...restaurant, summary: null };
        }
    }));
    
    tbody.innerHTML = restaurantData.map(data => {
        const creditUsage = data.summary ? (data.summary.credit_usage_percent || 0).toFixed(1) : 0;
        const outstanding = data.summary ? data.summary.outstanding : 0;
        
        return `
            <tr>
                <td><strong>${data.restaurant_code}</strong></td>
                <td>${data.name}</td>
                <td><span class="badge badge-info">${data.restaurant_type.replace(/_/g, ' ')}</span></td>
                <td>${data.area || '-'}</td>
                <td>${data.phone}</td>
                <td>${formatCurrency(data.credit_limit)}</td>
                <td style="color: ${outstanding > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">
                    ${formatCurrency(outstanding)}
                </td>
                <td>
                    <span class="badge ${data.status ? 'badge-success' : 'badge-danger'}">
                        ${data.status ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewRestaurant(${data.id})">View</button>
                    <button class="btn btn-sm btn-secondary" onclick="editRestaurant(${data.id})">Edit</button>
                    <button class="btn btn-sm btn-accent" onclick="viewStatement(${data.id})">Statement</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteRestaurant(${data.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(loadRestaurants, 300));
    
    // Filters
    document.getElementById('areaFilter').addEventListener('change', loadRestaurants);
    document.getElementById('typeFilter').addEventListener('change', loadRestaurants);
    document.getElementById('statusFilter').addEventListener('change', loadRestaurants);
    
    // Restaurant form
    document.getElementById('restaurantForm').addEventListener('submit', handleRestaurantSubmit);
}

// Open restaurant modal
function openRestaurantModal(restaurant = null) {
    const modal = document.getElementById('restaurantModal');
    const title = document.getElementById('restaurantModalTitle');
    const form = document.getElementById('restaurantForm');
    
    // Reset form
    form.reset();
    document.getElementById('restaurantId').value = '';
    
    if (restaurant) {
        title.textContent = 'Edit Restaurant';
        
        // Populate form with restaurant data
        document.getElementById('restaurantId').value = restaurant.id;
        document.getElementById('restaurantCode').value = restaurant.restaurant_code;
        document.getElementById('restaurantName').value = restaurant.name;
        document.getElementById('restaurantType').value = restaurant.restaurant_type;
        document.getElementById('restaurantOwnerName').value = restaurant.owner_name || '';
        document.getElementById('restaurantContactPerson').value = restaurant.contact_person || '';
        document.getElementById('restaurantPhone').value = restaurant.phone;
        document.getElementById('restaurantWhatsapp').value = restaurant.whatsapp || '';
        document.getElementById('restaurantEmail').value = restaurant.email || '';
        document.getElementById('restaurantAddress').value = restaurant.address || '';
        document.getElementById('restaurantArea').value = restaurant.area || '';
        document.getElementById('restaurantGstNumber').value = restaurant.gst_number || '';
        document.getElementById('restaurantCreditLimit').value = restaurant.credit_limit;
        document.getElementById('restaurantPaymentTerms').value = restaurant.payment_terms || '';
        document.getElementById('restaurantSalesperson').value = restaurant.assigned_salesperson || '';
        document.getElementById('restaurantNotes').value = restaurant.notes || '';
    } else {
        title.textContent = 'Add Restaurant';
    }
    
    modal.classList.add('show');
}

// Close restaurant modal
function closeRestaurantModal() {
    document.getElementById('restaurantModal').classList.remove('show');
}

// View restaurant
async function viewRestaurant(id) {
    try {
        const restaurant = await restaurantsAPI.getById(id);
        if (restaurant) {
            openRestaurantModal(restaurant);
        }
    } catch (error) {
        console.error('Error loading restaurant:', error);
        showToast('Failed to load restaurant details', 'error');
    }
}

let currentStatementRestaurantId = null;

// Edit restaurant
async function editRestaurant(id) {
    try {
        const restaurant = await restaurantsAPI.getById(id);
        if (restaurant) {
            openRestaurantModal(restaurant);
        }
    } catch (error) {
        console.error('Error loading restaurant:', error);
        showToast('Failed to load restaurant details', 'error');
    }
}

// View statement
async function viewStatement(id) {
    currentStatementRestaurantId = id;
    const modal = document.getElementById('statementModal');
    const title = document.getElementById('statementModalTitle');
    
    try {
        const restaurant = await restaurantsAPI.getById(id);
        if (!restaurant) {
            showToast('Restaurant not found', 'error');
            return;
        }
        title.textContent = `Statement - ${restaurant.name}`;
        
        // Set default date range (1st of current month to today)
        const today = new Date();
        const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        
        document.getElementById('stmtStartDate').value = firstDayOfMonth.toISOString().split('T')[0];
        document.getElementById('stmtEndDate').value = today.toISOString().split('T')[0];
        
        modal.classList.add('show');
        await loadRestaurantStatement();
    } catch (error) {
        console.error('Error viewing statement:', error);
        showToast('Failed to open statement modal', 'error');
    }
}

// Close statement modal
function closeStatementModal() {
    document.getElementById('statementModal').classList.remove('show');
    currentStatementRestaurantId = null;
}

// Load statement data for selected date range
async function loadRestaurantStatement() {
    if (!currentStatementRestaurantId) return;
    
    const startDate = document.getElementById('stmtStartDate').value;
    const endDate = document.getElementById('stmtEndDate').value;
    const contentDiv = document.getElementById('statementContent');
    
    if (!startDate || !endDate) {
        showToast('Please select both start and end dates', 'warning');
        return;
    }
    
    contentDiv.innerHTML = '<div class="loading" style="text-align: center; padding: 40px;"><div class="spinner"></div><p style="margin-top: 10px;">Generating statement report...</p></div>';
    
    try {
        const statement = await restaurantsAPI.getStatement(
            currentStatementRestaurantId,
            startDate,
            endDate
        );
        
        const invoicesHtml = statement.invoices && statement.invoices.length > 0
            ? statement.invoices.map(inv => `
                <tr>
                    <td><strong>${inv.invoice_number}</strong></td>
                    <td>${formatDate(inv.date)}</td>
                    <td style="font-weight: 600;">${formatCurrency(inv.amount)}</td>
                    <td style="color: var(--success-color);">${formatCurrency(inv.amount_paid)}</td>
                    <td style="color: ${inv.balance_due > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">${formatCurrency(inv.balance_due)}</td>
                    <td>
                        <span class="badge ${inv.payment_status === 'paid' ? 'badge-success' : inv.payment_status === 'partial' ? 'badge-warning' : 'badge-danger'}">
                            ${(inv.payment_status || 'unpaid').toUpperCase()}
                        </span>
                    </td>
                </tr>
            `).join('')
            : '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No bills/invoices found in this range</td></tr>';

        const paymentsHtml = statement.payments && statement.payments.length > 0
            ? statement.payments.map(pay => `
                <tr>
                    <td><strong>${pay.payment_code || '-'}</strong></td>
                    <td>${formatDate(pay.date)}</td>
                    <td><span class="badge badge-info">${(pay.method || 'cash').toUpperCase()}</span></td>
                    <td>
                        <span class="badge ${pay.status === 'completed' ? 'badge-success' : pay.status === 'pending' ? 'badge-warning' : 'badge-danger'}">
                            ${(pay.status || 'completed').toUpperCase()}
                        </span>
                    </td>
                    <td>${pay.transaction_reference || '-'}</td>
                    <td style="font-weight: 600; color: var(--success-color);">${formatCurrency(pay.amount)}</td>
                </tr>
            `).join('')
            : '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No payments/receipts found in this range</td></tr>';

        contentDiv.innerHTML = `
            <!-- Statement Header Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;">
                <div style="background: var(--bg-tertiary, #f1f5f9); padding: 15px; border-radius: 8px; border-left: 4px solid #64748b;">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Opening Balance</div>
                    <div style="font-size: 1.3rem; font-weight: 700;">${formatCurrency(statement.opening_balance)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #f1f5f9); padding: 15px; border-radius: 8px; border-left: 4px solid var(--primary-color);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Total Sales (Billed)</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: var(--primary-color);">${formatCurrency(statement.total_sales)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #f1f5f9); padding: 15px; border-radius: 8px; border-left: 4px solid var(--success-color);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Total Payments Received</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: var(--success-color);">${formatCurrency(statement.total_payments)}</div>
                </div>
                <div style="background: var(--bg-tertiary, #f1f5f9); padding: 15px; border-radius: 8px; border-left: 4px solid var(--danger-color);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Closing Outstanding</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: ${statement.closing_balance > 0 ? 'var(--danger-color)' : 'var(--success-color)'};">${formatCurrency(statement.closing_balance)}</div>
                </div>
            </div>

            <!-- Invoices / Bills Section -->
            <h4 style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">🧾 Bills & Invoices (${statement.invoices ? statement.invoices.length : 0})</h4>
            <div class="table-container" style="margin-bottom: 25px;">
                <table>
                    <thead>
                        <tr>
                            <th>Invoice #</th>
                            <th>Date</th>
                            <th>Grand Total</th>
                            <th>Amount Paid</th>
                            <th>Balance Due</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${invoicesHtml}
                    </tbody>
                </table>
            </div>

            <!-- Payments Received Section -->
            <h4 style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">💰 Payments Received (${statement.payments ? statement.payments.length : 0})</h4>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Payment Code</th>
                            <th>Date</th>
                            <th>Method</th>
                            <th>Status</th>
                            <th>Reference</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${paymentsHtml}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        console.error('Error generating statement:', error);
        contentDiv.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--danger-color);">Failed to load statement: ${error.message || ''}</div>`;
        showToast('Failed to load statement', 'error');
    }
}

// Handle restaurant form submission
async function handleRestaurantSubmit(event) {
    event.preventDefault();
    
    const restaurantId = document.getElementById('restaurantId').value;
    
    const restaurantData = {
        restaurant_code: document.getElementById('restaurantCode').value,
        name: document.getElementById('restaurantName').value,
        restaurant_type: document.getElementById('restaurantType').value,
        owner_name: document.getElementById('restaurantOwnerName').value,
        contact_person: document.getElementById('restaurantContactPerson').value,
        phone: document.getElementById('restaurantPhone').value,
        whatsapp: document.getElementById('restaurantWhatsapp').value,
        email: document.getElementById('restaurantEmail').value,
        address: document.getElementById('restaurantAddress').value,
        area: document.getElementById('restaurantArea').value,
        gst_number: document.getElementById('restaurantGstNumber').value,
        credit_limit: parseFloat(document.getElementById('restaurantCreditLimit').value),
        payment_terms: document.getElementById('restaurantPaymentTerms').value,
        assigned_salesperson: document.getElementById('restaurantSalesperson').value,
        notes: document.getElementById('restaurantNotes').value
    };
    
    try {
        if (restaurantId) {
            // Update existing restaurant
            await restaurantsAPI.update(parseInt(restaurantId), restaurantData);
            showToast('Restaurant updated successfully', 'success');
        } else {
            // Create new restaurant
            await restaurantsAPI.create(restaurantData);
            showToast('Restaurant created successfully', 'success');
        }
        
        closeRestaurantModal();
        await loadRestaurants();
    } catch (error) {
        console.error('Error saving restaurant:', error);
        showToast('Failed to save restaurant: ' + (error.message || ''), 'error');
    }
}

// Delete restaurant
async function deleteRestaurant(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this restaurant record? This action cannot be undone.')) {
        return;
    }

    try {
        await restaurantsAPI.delete(id);
        showToast('Restaurant deleted successfully!', 'success');
        await loadRestaurants();
    } catch (error) {
        console.error('Error deleting restaurant:', error);
        showToast('Failed to delete restaurant: ' + (error.message || ''), 'error');
    }
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initRestaurantsPage);
