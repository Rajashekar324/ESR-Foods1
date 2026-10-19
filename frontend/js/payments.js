/**
 * Payments Page Functions for ESR Foods
 */

let allVendors = [];
let allInvoices = [];
let allPurchases = [];
let selectedVendorId = null;

// Initialize payments page
async function initPaymentsPage() {
    if (!requireAuth()) return;
    
    try {
        await Promise.all([loadVendorsForDropdown(), loadPurchasesForDropdown(), loadInvoicesForDropdown()]);
        
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
    const options = '<option value="">Select Vendor</option>' + allVendors.map(v => `<option value="${v.id}">${v.name}</option>`).join('');
    document.getElementById('vendorFilter').innerHTML = '<option value="">All Vendors</option>' + allVendors.map(v => `<option value="${v.id}">${v.name}</option>`).join('');
    document.getElementById('paymentVendor').innerHTML = options;
}

async function loadPurchasesForDropdown() {
    allPurchases = await purchasesAPI.getAll({ limit: 500 });
    document.getElementById('paymentPurchase').innerHTML = '<option value="">Select Purchase (Optional)</option>' + allPurchases.map(p => `<option value="${p.id}">${p.purchase_code} - ${formatCurrency(p.total)}</option>`).join('');
}

// Load invoices for dropdown
async function loadInvoicesForDropdown() {
    try {
        allInvoices = await invoicesAPI.getAll({ is_finalized: true });
        
        const paymentInvoice = document.getElementById('paymentInvoice');
        
        const options = '<option value="">Select Invoice (Optional)</option>' +
            allInvoices.map(i => `<option value="${i.id}">${i.invoice_number}</option>`).join('');
        
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
        const paymentMethod = document.getElementById('paymentMethodFilter').value;
        
        const params = {};
        if (paymentType) params.payment_type = paymentType;
        if (paymentStatus) params.status = paymentStatus;
        if (vendorId) params.vendor_id = parseInt(vendorId);
        if (paymentMethod) params.payment_method = paymentMethod;
        
        if (document.getElementById('paymentToFilter').value === 'operations') params.payment_type = 'payment';
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
    
    const vendorNames = {};
    allVendors.forEach(v => vendorNames[v.id] = v.name);
    
    tbody.innerHTML = payments.map(payment => {
        let entityName = '-';
        entityName = payment.vendor_id ? `🏭 ${vendorNames[payment.vendor_id] || 'Vendor #' + payment.vendor_id}` : `💸 ${payment.paid_to || payment.notes || 'Operations'}`;
        
        const currentStatus = payment.status || 'completed';
        
        return `
            <tr>
                <td><strong>${payment.payment_code}</strong></td>
                <td><span class="badge ${payment.payment_type === 'receipt' ? 'badge-success' : 'badge-warning'}">${payment.payment_type.replace(/_/g, ' ')}</span></td>
                <td>${formatDate(payment.date)}</td>
                <td>${entityName}</td>
                <td style="font-weight: 600; color: ${payment.payment_type === 'receipt' ? 'var(--success-color)' : 'var(--danger-color)'};">
                    ${formatCurrency(payment.amount)}
                </td>
                <td><span class="badge badge-info">${payment.payment_method.replace(/_/g, ' ')}</span></td>
                <td>
                    <select class="form-select" style="width: auto; padding: 2px 8px; font-size: 0.85rem; border-radius: 4px;" onchange="changePaymentStatus(${payment.id}, this.value)">
                        <option value="completed" ${currentStatus === 'completed' ? 'selected' : ''}>Completed</option>
                        <option value="pending" ${currentStatus === 'pending' ? 'selected' : ''}>Pending</option>
                        <option value="reversed" ${currentStatus === 'reversed' ? 'selected' : ''}>Reversed</option>
                        <option value="cancelled" ${currentStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </td>
                <td>${payment.transaction_reference || '-'}</td>
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
    document.getElementById('paymentMethodFilter').addEventListener('change', loadPayments);
    
    document.getElementById('paymentForm').addEventListener('submit', handlePaymentSubmit);
    document.getElementById('paymentPurchase').addEventListener('change', event => {
        const purchase = allPurchases.find(item => item.id === parseInt(event.target.value));
        if (purchase) document.getElementById('paymentVendor').value = purchase.vendor_id;
    });
}

// Handle payment type change
function handlePaymentToChange() {
    const isVendor = document.getElementById('paymentTo').value === 'vendor';
    const vendorField = document.getElementById('vendorField');
    vendorField.style.display = isVendor ? 'block' : 'none';
    document.getElementById('operationsFields').style.display = isVendor ? 'none' : 'block';
    document.getElementById('paymentVendor').required = isVendor;
    document.getElementById('paymentPaidTo').required = !isVendor;
    document.getElementById('paymentPurchaseField').style.display = isVendor ? 'block' : 'none';
    document.getElementById('paymentInvoiceField').style.display = isVendor ? 'block' : 'none';
}

// Open payment modal
function openPaymentModal(destination = 'vendor') {
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
    
    title.textContent = 'Record Payment';
    document.getElementById('paymentTo').value = destination === 'operations' ? 'operations' : 'vendor';
    document.getElementById('paymentCode').value = `PAY-${Date.now()}`;
    handlePaymentToChange();
    
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
    
    const isVendor = document.getElementById('paymentTo').value === 'vendor';
    
    const paymentData = {
        payment_code: document.getElementById('paymentCode').value,
        payment_type: 'payment',
        date: document.getElementById('paymentDate').value,
        status: document.getElementById('paymentStatus').value,
        invoice_id: isVendor && document.getElementById('paymentInvoice').value ? parseInt(document.getElementById('paymentInvoice').value) : null,
        purchase_id: isVendor && document.getElementById('paymentPurchase').value ? parseInt(document.getElementById('paymentPurchase').value) : null,
        vendor_id: isVendor && document.getElementById('paymentVendor').value ? parseInt(document.getElementById('paymentVendor').value) : null,
        amount: parseFloat(document.getElementById('paymentAmount').value),
        payment_method: document.getElementById('paymentMethod').value,
        transaction_reference: document.getElementById('paymentReference').value,
        notes: document.getElementById('paymentNotes').value
        ,category: isVendor ? null : document.getElementById('paymentCategory').value
        ,paid_to: isVendor ? null : document.getElementById('paymentPaidTo').value
    };
    
    try {
        await paymentsAPI.create(paymentData);
        showToast('Payment saved successfully', 'success');
        closePaymentModal();
        await loadPayments();
    } catch (error) {
        console.error('Error saving payment:', error);
        showToast('Failed to save payment: ' + (error.message || ''), 'error');
    }
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
    document.getElementById('vendorLedgerSummary').innerHTML = [['Total purchases', ledger.total_purchases], ['Payments made', ledger.total_payments], ['Credits / adjustments', ledger.credit_adjustments], ['Current pending amount', ledger.pending_amount]].map(([label, value]) => `<div class="card"><strong>${label}</strong><div style="font-size:1.35rem">${formatCurrency(value)}</div></div>`).join('');
    document.getElementById('vendorPaymentHistory').innerHTML = ledger.payments.length ? ledger.payments.map(p => `<tr><td>${p.payment_code}</td><td>${formatDate(p.date)}</td><td>${formatCurrency(p.amount)}</td><td>${p.payment_method}</td><td>${p.transaction_reference || '-'}</td><td>${p.purchase_id || p.invoice_id || '-'}</td><td>${p.status}</td><td>${p.notes || '-'}</td></tr>`).join('') : '<tr><td colspan="8">No vendor payments recorded</td></tr>';
    document.getElementById('vendorStatementSummary').innerHTML = `<p><strong>Opening balance:</strong> ${formatCurrency(ledger.statement.opening_balance)} &nbsp; <strong>Purchases:</strong> ${formatCurrency(ledger.statement.period_purchases)} &nbsp; <strong>Payments:</strong> ${formatCurrency(ledger.statement.period_payments)} &nbsp; <strong>Closing outstanding:</strong> ${formatCurrency(ledger.statement.closing_balance)}</p>`;
    document.getElementById('vendorPurchaseStatement').innerHTML = ledger.statement.purchases.length ? ledger.statement.purchases.map(p => `<tr><td>${formatDate(p.purchase_date)}</td><td>${p.purchase_code}</td><td>${p.vendor_invoice_number || '-'}</td><td>${formatCurrency(p.total)}</td></tr>`).join('') : '<tr><td colspan="4">No purchases in this period</td></tr>';
    document.getElementById('vendorPaymentStatement').innerHTML = ledger.statement.payments.length ? ledger.statement.payments.map(p => `<tr><td>${formatDate(p.date)}</td><td>${p.payment_code}</td><td>${p.payment_method}</td><td>${formatCurrency(p.amount)}</td><td>${p.status}</td></tr>`).join('') : '<tr><td colspan="5">No payments in this period</td></tr>';
}

async function loadSelectedVendorStatement() {
    if (!selectedVendorId) {
        showToast('Select a vendor first', 'error');
        return;
    }
    await loadVendorLedger(selectedVendorId);
}

function hideVendorLedger() { document.getElementById('vendorLedgerPanel').style.display = 'none'; }

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initPaymentsPage);
