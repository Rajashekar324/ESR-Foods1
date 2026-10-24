/**
 * Payments Page Functions for ESR Foods
 */

let allVendors = [];
let allRestaurants = [];
let allCustomers = [];
let allInvoices = [];
let allPurchases = [];
let selectedVendorId = null;

// Initialize payments page
async function initPaymentsPage() {
    if (!requireAuth()) return;
    
    try {
        await Promise.all([loadVendorsForDropdown(), loadRestaurantsForDropdown(), loadCustomersForDropdown(), loadPurchasesForDropdown(), loadInvoicesForDropdown()]);
        
        // Load payments
        await loadPayments();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Payments page initialization error:', error);
        showToast('Failed to load payments', 'error');
    }
}

// Load restaurants for dropdown
// Load vendors for dropdown
async function loadVendorsForDropdown() {
    allVendors = await vendorsAPI.getAll({ status: true });
    const options = '<option value="">Select Vendor</option>' + allVendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
    document.getElementById('vendorFilter').innerHTML = '<option value="">All Vendors</option>' + allVendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
    document.getElementById('paymentVendor').innerHTML = options;
}

async function loadRestaurantsForDropdown() {
    allRestaurants = await restaurantsAPI.getAll({ status: true });
    const options = '<option value="">Select Restaurant</option>' + allRestaurants.map(r => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join('');
    document.getElementById('restaurantFilter').innerHTML = '<option value="">All Restaurants</option>' + allRestaurants.map(r => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join('');
    document.getElementById('paymentRestaurant').innerHTML = options;
}

async function loadCustomersForDropdown() {
    allCustomers = await customersAPI.getAll({ status: true, limit: 500 });
    const options = '<option value="">Select Customer</option>' + allCustomers.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    document.getElementById('customerFilter').innerHTML = '<option value="">All Customers</option>' + allCustomers.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    document.getElementById('paymentCustomer').innerHTML = options;
}

async function loadPurchasesForDropdown() {
    allPurchases = await purchasesAPI.getAll({ limit: 500 });
    document.getElementById('paymentPurchase').innerHTML = '<option value="">Select Purchase (Optional)</option>' + allPurchases.map(p => `<option value="${p.id}">${escapeHtml(p.purchase_code)} - ${formatCurrency(p.total)}</option>`).join('');
}

// Load invoices for dropdown
async function loadInvoicesForDropdown() {
    try {
        allInvoices = await invoicesAPI.getAll({ is_finalized: true });
        
        const paymentInvoice = document.getElementById('paymentInvoice');
        
        const options = '<option value="">Select Invoice (Optional)</option>' +
            allInvoices.filter(i => i.balance_due > 0).map(i => `<option value="${i.id}" data-restaurant-id="${i.restaurant_id}">${escapeHtml(i.invoice_number)} · ${formatCurrency(i.balance_due)} due</option>`).join('');
        
        if (paymentInvoice) paymentInvoice.innerHTML = options;
    } catch (error) {
        console.error('Error loading invoices:', error);
    }
}

// Load payments
async function loadPayments() {
    try {
        const paymentType = document.getElementById('paymentTypeFilter').value;
        const paymentStatus = document.getElementById('paymentStatusFilter') ? document.getElementById('paymentStatusFilter').value : '';
        const vendorId = document.getElementById('vendorFilter').value;
        const restaurantId = document.getElementById('restaurantFilter').value;
        const customerId = document.getElementById('customerFilter').value;
        const paymentMethod = document.getElementById('paymentMethodFilter').value;
        const source = document.getElementById('paymentToFilter').value;
        
        const params = {};
        if (paymentType) params.payment_type = paymentType;
        if (paymentStatus) params.status = paymentStatus;
        if (vendorId) params.vendor_id = parseInt(vendorId);
        if (restaurantId) params.restaurant_id = parseInt(restaurantId);
        if (customerId) params.customer_id = parseInt(customerId);
        if (paymentMethod) params.payment_method = paymentMethod;
        if (source) params.payment_source = source;
        const payments = await paymentsAPI.getAll(params);
        renderPaymentsTable(payments);
    } catch (error) {
        console.error('Error loading payments:', error);
        document.getElementById('paymentsTable').innerHTML = '<tr><td colspan="9" style="color: var(--danger-color); text-align: center;">Failed to load payments</td></tr>';
    }
}

// Render payments table
function renderPaymentsTable(payments) {
    const tbody = document.getElementById('paymentsTable');
    
    if (!payments || payments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><div class="empty-state-icon">💰</div><div class="empty-state-text">No payments found</div></td></tr>';
        return;
    }
    
    const vendorNames = Object.fromEntries(allVendors.map(v => [v.id, v.name]));
    const restaurantNames = Object.fromEntries(allRestaurants.map(r => [r.id, r.name]));
    const customerNames = Object.fromEntries(allCustomers.map(c => [c.id, c.name]));
    
    tbody.innerHTML = payments.map(payment => {
        let entityName = '—';
        if (payment.restaurant_id) entityName = `🍽️ ${restaurantNames[payment.restaurant_id] || 'Restaurant #' + payment.restaurant_id}`;
        else if (payment.customer_id) entityName = `👤 ${customerNames[payment.customer_id] || 'Customer #' + payment.customer_id}`;
        else if (payment.vendor_id) entityName = `🏭 ${vendorNames[payment.vendor_id] || 'Vendor #' + payment.vendor_id}`;
        else entityName = `💸 ${payment.paid_to || payment.notes || 'Operations'}`;
        
        const currentStatus = payment.status || 'completed';
        
        return `
            <tr>
                <td><strong>${escapeHtml(payment.payment_code)}</strong></td>
                <td><span class="badge ${payment.payment_type === 'receipt' ? 'badge-success' : 'badge-warning'}">${payment.payment_type.replace(/_/g, ' ')}</span></td>
                <td>${formatDate(payment.date)}</td>
                <td>${escapeHtml(entityName)}</td>
                <td style="font-weight: 600; color: ${payment.payment_type === 'receipt' ? 'var(--success-color)' : 'var(--danger-color)'};">
                    ${formatCurrency(payment.amount)}
                </td>
                <td><span class="badge badge-info">${escapeHtml(payment.payment_method.replace(/_/g, ' '))}</span></td>
                <td>
                    <select class="form-select" style="width: auto; padding: 2px 8px; font-size: 0.85rem; border-radius: 4px;" onchange="changePaymentStatus(${payment.id}, this.value)">
                        <option value="completed" ${currentStatus === 'completed' ? 'selected' : ''}>Completed</option>
                        <option value="pending" ${currentStatus === 'pending' ? 'selected' : ''}>Pending</option>
                        <option value="reversed" ${currentStatus === 'reversed' ? 'selected' : ''}>Reversed</option>
                        <option value="cancelled" ${currentStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </td>
                <td>${escapeHtml(payment.transaction_reference || '-')}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="reversePayment(${payment.id})">Reverse</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Quick change payment status
async function changePaymentStatus(id, newStatus) {
    try {
        await paymentsAPI.updateStatus(id, newStatus);
        showToast(`Payment status updated to ${newStatus.toUpperCase()}`, 'success');
        await loadInvoicesForDropdown();
        await loadPayments();
    } catch (error) {
        console.error('Error updating status:', error);
        showToast('Failed to update payment status: ' + (error.message || ''), 'error');
        await loadPayments();
    }
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('paymentTypeFilter').addEventListener('change', loadPayments);
    if (document.getElementById('paymentStatusFilter')) {
        document.getElementById('paymentStatusFilter').addEventListener('change', loadPayments);
    }
    document.getElementById('paymentToFilter').addEventListener('change', loadPayments);
    document.getElementById('vendorFilter').addEventListener('change', loadPayments);
    document.getElementById('vendorFilter').addEventListener('change', event => event.target.value ? loadVendorLedger(event.target.value) : hideVendorLedger());
    document.getElementById('restaurantFilter').addEventListener('change', loadPayments);
    document.getElementById('customerFilter').addEventListener('change', loadPayments);
    document.getElementById('paymentMethodFilter').addEventListener('change', loadPayments);
    
    document.getElementById('paymentForm').addEventListener('submit', handlePaymentSubmit);
    document.getElementById('paymentPurchase').addEventListener('change', event => {
        const purchase = allPurchases.find(item => item.id === parseInt(event.target.value));
        if (purchase) document.getElementById('paymentVendor').value = purchase.vendor_id;
    });
    document.getElementById('paymentRestaurant').addEventListener('change', () => {
        updateInvoiceOptions();
        loadSelectedRestaurantBalance();
    });
    document.getElementById('paymentInvoice').addEventListener('change', updateInvoiceBalanceLimit);
}

// Update form fields for received receipts and outgoing payments.
function handlePaymentToChange() {
    const isReceipt = document.getElementById('paymentDirection').value === 'receipt';
    const sourceSelect = document.getElementById('paymentSource');
    const previousSource = sourceSelect.value;
    const sources = isReceipt
        ? [['restaurant', 'Restaurant'], ['vendor', 'Vendor'], ['customer', 'Customer']]
        : [['vendor', 'Vendor'], ['operations', 'Operations']];
    sourceSelect.innerHTML = sources.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    if (sources.some(([value]) => value === previousSource)) sourceSelect.value = previousSource;

    const source = sourceSelect.value;
    document.getElementById('paymentSourceLabel').textContent = isReceipt ? 'Received From' : 'Payment To';
    document.getElementById('paymentDateField').style.display = 'block';
    document.getElementById('paymentRestaurantField').style.display = isReceipt && source === 'restaurant' ? 'block' : 'none';
    document.getElementById('paymentCustomerField').style.display = isReceipt && source === 'customer' ? 'block' : 'none';
    document.getElementById('vendorField').style.display = source === 'vendor' ? 'block' : 'none';
    document.getElementById('vendorFieldLabel').textContent = isReceipt ? 'Vendor' : 'Pay Vendor';
    document.getElementById('operationsFields').style.display = !isReceipt && source === 'operations' ? 'block' : 'none';
    document.getElementById('paymentPurchaseField').style.display = !isReceipt && source === 'vendor' ? 'block' : 'none';
    document.getElementById('paymentInvoiceSelectField').style.display = isReceipt && source === 'restaurant' ? 'block' : 'none';
    document.getElementById('paymentVendor').required = source === 'vendor';
    document.getElementById('paymentRestaurant').required = isReceipt && source === 'restaurant';
    document.getElementById('paymentCustomer').required = isReceipt && source === 'customer';
    document.getElementById('paymentInvoice').required = isReceipt && source === 'restaurant';
    document.getElementById('paymentPaidTo').required = !isReceipt && source === 'operations';
    document.getElementById('paymentPurchase').value = '';
    document.getElementById('paymentInvoice').value = '';
    document.getElementById('savePaymentButton').textContent = isReceipt ? 'Save Receipt' : 'Save Payment';
    updateInvoiceOptions();
    if (isReceipt && source === 'restaurant') loadSelectedRestaurantBalance();
    else document.getElementById('paymentRestaurantBalance').textContent = '';
}

function updateInvoiceOptions() {
    const restaurantId = document.getElementById('paymentRestaurant').value;
    const options = ['<option value="">Select Invoice</option>', ...allInvoices
        .filter(invoice => invoice.balance_due > 0 && (!restaurantId || invoice.restaurant_id === parseInt(restaurantId)))
        .map(invoice => `<option value="${invoice.id}">${escapeHtml(invoice.invoice_number)} · ${formatCurrency(invoice.balance_due)} due</option>`)
    ];
    document.getElementById('paymentInvoice').innerHTML = options.join('');
    updateInvoiceBalanceLimit();
}

function updateInvoiceBalanceLimit() {
    const amountInput = document.getElementById('paymentAmount');
    const isRestaurantReceipt = document.getElementById('paymentDirection').value === 'receipt'
        && document.getElementById('paymentSource').value === 'restaurant';
    const invoiceId = parseInt(document.getElementById('paymentInvoice').value, 10);
    const invoice = allInvoices.find(item => item.id === invoiceId);
    if (isRestaurantReceipt && invoice) {
        amountInput.max = String(invoice.balance_due);
        document.getElementById('paymentInvoiceBalanceHint').textContent = `Invoice balance due: ${formatCurrency(invoice.balance_due)}. A completed receipt reduces this and the restaurant's outstanding balance.`;
    } else {
        amountInput.removeAttribute('max');
        document.getElementById('paymentInvoiceBalanceHint').textContent = 'The receipt reduces the selected invoice and restaurant outstanding balance.';
    }
}

async function loadSelectedRestaurantBalance() {
    const restaurantId = parseInt(document.getElementById('paymentRestaurant').value, 10);
    const balanceLabel = document.getElementById('paymentRestaurantBalance');
    if (!restaurantId) {
        balanceLabel.textContent = 'Select a restaurant to see its current outstanding balance.';
        return;
    }
    try {
        const summary = await restaurantsAPI.getSummary(restaurantId);
        balanceLabel.textContent = `Current outstanding balance: ${formatCurrency(summary.outstanding)}.`;
    } catch (error) {
        console.error('Could not load restaurant balance:', error);
        balanceLabel.textContent = 'Could not load the current restaurant balance.';
    }
}

// Open payment modal
function openPaymentModal(direction = 'payment', source = '') {
    const modal = document.getElementById('paymentModal');
    const title = document.getElementById('paymentModalTitle');
    const form = document.getElementById('paymentForm');
    
    // Reset form
    form.reset();
    document.getElementById('paymentId').value = '';
    
    // Set default date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('paymentDate').value = today;
    document.getElementById('paymentStatus').value = 'completed';
    
    const isReceipt = direction === 'receipt';
    title.textContent = isReceipt ? 'Record Received Payment' : 'Record Outgoing Payment';
    document.getElementById('paymentDirection').value = isReceipt ? 'receipt' : 'payment';
    handlePaymentToChange();
    if (source && [...document.getElementById('paymentSource').options].some(option => option.value === source)) {
        document.getElementById('paymentSource').value = source;
        handlePaymentToChange();
    }
    document.getElementById('paymentCode').value = `${isReceipt ? 'REC' : 'PAY'}-${Date.now()}`;
    document.getElementById('paymentAmount').removeAttribute('max');
    
    modal.classList.add('show');
}

// Close payment modal
function closePaymentModal() {
    document.getElementById('paymentModal').classList.remove('show');
}

async function reversePayment(id) {
    if (!confirm('Reverse this payment? The original ledger record will be retained.')) {
        return;
    }

    try {
        await paymentsAPI.delete(id);
        showToast('Payment reversed and retained in history', 'success');
        await loadPayments();
    } catch (error) {
        console.error('Error deleting payment:', error);
        showToast('Failed to delete payment: ' + (error.message || ''), 'error');
    }
}

// Handle payment form submission
async function handlePaymentSubmit(event) {
    event.preventDefault();
    
    const isReceipt = document.getElementById('paymentDirection').value === 'receipt';
    const source = document.getElementById('paymentSource').value;
    const amount = parseFloat(document.getElementById('paymentAmount').value);
    if (!Number.isFinite(amount) || amount <= 0) {
        showToast('Enter an amount greater than zero.', 'error');
        return;
    }
    
    const paymentData = {
        payment_code: document.getElementById('paymentCode').value,
        payment_type: isReceipt ? 'receipt' : 'payment',
        date: toIsoDateTime(document.getElementById('paymentDate').value),
        status: document.getElementById('paymentStatus').value,
        invoice_id: isReceipt && source === 'restaurant' && document.getElementById('paymentInvoice').value ? parseInt(document.getElementById('paymentInvoice').value) : null,
        purchase_id: !isReceipt && source === 'vendor' && document.getElementById('paymentPurchase').value ? parseInt(document.getElementById('paymentPurchase').value) : null,
        restaurant_id: isReceipt && source === 'restaurant' ? parseInt(document.getElementById('paymentRestaurant').value) : null,
        customer_id: isReceipt && source === 'customer' ? parseInt(document.getElementById('paymentCustomer').value) : null,
        vendor_id: source === 'vendor' && document.getElementById('paymentVendor').value ? parseInt(document.getElementById('paymentVendor').value) : null,
        amount,
        payment_method: document.getElementById('paymentMethod').value,
        transaction_reference: document.getElementById('paymentReference').value,
        notes: document.getElementById('paymentNotes').value,
        category: !isReceipt && source === 'operations' ? document.getElementById('paymentCategory').value : null,
        paid_to: !isReceipt && source === 'operations' ? document.getElementById('paymentPaidTo').value : null
    };
    
    try {
        await paymentsAPI.create(paymentData);
        closePaymentModal();
        if (isReceipt && source === 'restaurant') {
            try {
                const summary = await restaurantsAPI.getSummary(paymentData.restaurant_id);
                showToast(`Receipt recorded. Restaurant balance is now ${formatCurrency(summary.outstanding)}.`, 'success');
            } catch (balanceError) {
                console.error('Receipt saved but balance refresh failed:', balanceError);
                showToast('Receipt recorded successfully. Refresh the restaurant page to view its latest balance.', 'success');
            }
        } else {
            showToast(isReceipt ? 'Receipt recorded successfully' : 'Payment saved successfully', 'success');
        }
        await loadInvoicesForDropdown();
        await loadPayments();
    } catch (error) {
        console.error('Error saving payment:', error);
        showToast('Failed to save payment: ' + (error.message || ''), 'error');
    }
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

async function loadVendorLedger(vendorId) {
    selectedVendorId = parseInt(vendorId);
    const startInput = document.getElementById('vendorStatementStart');
    const endInput = document.getElementById('vendorStatementEnd');
    if (!startInput.value || !endInput.value) {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 60);
        startInput.value = start.toISOString().split('T')[0];
        endInput.value = end.toISOString().split('T')[0];
    }
    const ledger = await paymentsAPI.getVendorLedger(selectedVendorId, { start_date: startInput.value, end_date: endInput.value });
    document.getElementById('vendorLedgerPanel').style.display = 'block';
    document.getElementById('vendorLedgerTitle').textContent = `${ledger.vendor_name} Ledger`;
    document.getElementById('vendorLedgerSummary').innerHTML = [['Total purchases', ledger.total_purchases], ['Payments made', ledger.total_payments], ['Refunds received', ledger.refunds_received], ['Credits / adjustments', ledger.credit_adjustments], ['Current pending amount', ledger.pending_amount], ['Vendor credit', ledger.vendor_credit || 0]].map(([label, value]) => `<div class="card"><strong>${label}</strong><div style="font-size:1.35rem">${formatCurrency(value)}</div></div>`).join('');
    document.getElementById('vendorPaymentHistory').innerHTML = ledger.payments.length ? ledger.payments.map(p => `<tr><td>${escapeHtml(p.payment_code)}</td><td>${p.payment_type === 'receipt' ? 'Received' : 'Paid'}</td><td>${formatDate(p.date)}</td><td>${formatCurrency(p.amount)}</td><td>${escapeHtml(p.payment_method)}</td><td>${escapeHtml(p.transaction_reference || '-')}</td><td>${p.purchase_id || '-'}</td><td>${escapeHtml(p.status)}</td><td>${escapeHtml(p.notes || '-')}</td></tr>`).join('') : '<tr><td colspan="9">No vendor payment records</td></tr>';
    document.getElementById('vendorStatementSummary').innerHTML = `<p><strong>Opening balance:</strong> ${formatCurrency(ledger.statement.opening_balance)} &nbsp; <strong>Purchases:</strong> ${formatCurrency(ledger.statement.period_purchases)} &nbsp; <strong>Payments made:</strong> ${formatCurrency(ledger.statement.period_payments)} &nbsp; <strong>Refunds received:</strong> ${formatCurrency(ledger.statement.period_refunds)} &nbsp; <strong>Closing outstanding:</strong> ${formatCurrency(ledger.statement.closing_balance)}</p>`;
    document.getElementById('vendorPurchaseStatement').innerHTML = ledger.statement.purchases.length ? ledger.statement.purchases.map(p => `<tr><td>${formatDate(p.purchase_date)}</td><td>${p.purchase_code}</td><td>${p.vendor_invoice_number || '-'}</td><td>${formatCurrency(p.total)}</td></tr>`).join('') : '<tr><td colspan="4">No purchases in this period</td></tr>';
    document.getElementById('vendorPaymentStatement').innerHTML = ledger.statement.payments.length ? ledger.statement.payments.map(p => `<tr><td>${formatDate(p.date)}</td><td>${escapeHtml(p.payment_code)}</td><td>${p.payment_type === 'receipt' ? 'Received' : 'Paid'}</td><td>${escapeHtml(p.payment_method)}</td><td>${formatCurrency(p.amount)}</td><td>${escapeHtml(p.status)}</td></tr>`).join('') : '<tr><td colspan="6">No payment transactions in this period</td></tr>';
}

async function loadSelectedVendorStatement() {
    if (!selectedVendorId) {
        showToast('Select a vendor first', 'error');
        return;
    }
    await loadVendorLedger(selectedVendorId);
}

function hideVendorLedger() { document.getElementById('vendorLedgerPanel').style.display = 'none'; }

// Bind the primary transaction actions before asynchronous page initialization.
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('receivePaymentButton')?.addEventListener('click', () => openPaymentModal('receipt'));
    document.getElementById('sendPaymentButton')?.addEventListener('click', () => openPaymentModal('payment'));
    initPaymentsPage();
});
