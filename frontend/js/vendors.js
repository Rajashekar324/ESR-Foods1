/**
 * Vendors Page Functions for ESR Foods
 */

let allVendors = [];
let selectedStatementVendorId = null;

// Initialize vendors page
async function initVendorsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load vendors
        await loadVendors();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Vendors page initialization error:', error);
        showToast('Failed to load vendors', 'error');
    }
}

// Load vendors
async function loadVendors() {
    try {
        const search = document.getElementById('searchInput').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (search) params.search = search;
        if (status) params.status = status === 'true';
        
        allVendors = await vendorsAPI.getAll(params);
        renderVendorsTable();
    } catch (error) {
        console.error('Error loading vendors:', error);
        document.getElementById('vendorsTable').innerHTML = '<tr><td colspan="8" style="color: var(--danger-color);">Failed to load vendors</td></tr>';
    }
}

// Render vendors table
function renderVendorsTable() {
    const tbody = document.getElementById('vendorsTable');
    
    if (!allVendors || allVendors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-state-icon">🏭</div><div class="empty-state-text">No vendors found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = allVendors.map(vendor => `
        <tr>
            <td><strong>${escapeHtml(vendor.vendor_code)}</strong></td>
                <td>${escapeHtml(vendor.name)}</td>
                <td>${escapeHtml(vendor.company_name || '-')}</td>
                <td>${escapeHtml(vendor.contact_person || '-')}</td>
                <td>${escapeHtml(vendor.phone || '-')}</td>
                <td>${escapeHtml(vendor.email || '-')}</td>
            <td>
                <span class="badge ${vendor.status ? 'badge-success' : 'badge-danger'}">
                    ${vendor.status ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewVendor(${vendor.id})">View</button>
                <button class="btn btn-sm btn-primary" onclick="showVendorStatement(${vendor.id})">Statement</button>
                ${vendor.status ? `<button class="btn btn-sm btn-accent" onclick="startVendorPurchase(${vendor.id})">New Purchase</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="editVendor(${vendor.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteVendor(${vendor.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

async function showVendorStatement(vendorId) {
    selectedStatementVendorId = vendorId;
    const panel = document.getElementById('vendorStatementPanel');
    const vendor = allVendors.find(item => item.id === vendorId);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 60);
    document.getElementById('vendorStatementStart').value = startDate.toISOString().slice(0, 10);
    document.getElementById('vendorStatementEnd').value = endDate.toISOString().slice(0, 10);
    panel.style.display = 'block';
    document.getElementById('vendorStatementTitle').textContent = `${vendor?.name || 'Vendor'} Statement`;
    document.getElementById('vendorStatementIdentity').textContent = vendor ? `${vendor.vendor_code}${vendor.company_name ? ` · ${vendor.company_name}` : ''}` : '';
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    await loadVendorStatement();
}

async function loadVendorStatement() {
    if (!selectedStatementVendorId) return;
    const startDate = document.getElementById('vendorStatementStart').value;
    const endDate = document.getElementById('vendorStatementEnd').value;
    if (!startDate || !endDate || startDate > endDate) {
        showToast('Choose a valid statement date range.', 'error');
        return;
    }
    const summary = document.getElementById('vendorStatementSummary');
    summary.innerHTML = '<div class="card">Loading vendor balance and statement…</div>';
    try {
        const ledger = await paymentsAPI.getVendorLedger(selectedStatementVendorId, { start_date: startDate, end_date: endDate });
        const cards = [
            ['Lifetime purchases', ledger.total_purchases],
            ['Payments made', ledger.total_payments],
            ['Refunds received', ledger.refunds_received || 0],
            ['Credit adjustments', ledger.credit_adjustments],
            ['Current balance due', ledger.pending_amount],
            ['Vendor credit', ledger.vendor_credit || 0],
            ['Closing balance for period', ledger.statement.closing_balance]
        ];
        summary.innerHTML = cards.map(([label, amount]) => `<div class="card"><strong>${label}</strong><div style="font-size:1.35rem;font-weight:700;margin-top:.4rem;">${formatCurrency(amount)}</div></div>`).join('');
        document.getElementById('vendorStatementPurchases').innerHTML = ledger.statement.purchases.length
            ? ledger.statement.purchases.map(purchase => `<tr><td>${formatDate(purchase.purchase_date)}</td><td>${escapeHtml(purchase.purchase_code)}</td><td>${escapeHtml(purchase.vendor_invoice_number || '—')}</td><td>${escapeHtml(String(purchase.status).replace(/_/g, ' '))}</td><td>${escapeHtml(purchase.payment_status || 'unpaid')}</td><td>${formatCurrency(purchase.total)}</td></tr>`).join('')
            : '<tr><td colspan="6">No purchases in this date range.</td></tr>';
        document.getElementById('vendorStatementPayments').innerHTML = ledger.statement.payments.length
            ? ledger.statement.payments.map(payment => `<tr><td>${formatDate(payment.date)}</td><td>${escapeHtml(payment.payment_code)}</td><td>${payment.payment_type === 'receipt' ? 'Refund received' : 'Payment sent'}</td><td>${escapeHtml(String(payment.payment_method).replace(/_/g, ' '))}</td><td>${escapeHtml(payment.status)}</td><td>${formatCurrency(payment.amount)}</td></tr>`).join('')
            : '<tr><td colspan="6">No payment transactions in this date range.</td></tr>';
    } catch (error) {
        console.error('Failed loading vendor statement:', error);
        summary.innerHTML = `<div class="card" style="color:var(--danger-color);">${escapeHtml(error.message || 'Failed to load vendor statement.')}</div>`;
    }
}

function closeVendorStatement() {
    document.getElementById('vendorStatementPanel').style.display = 'none';
    selectedStatementVendorId = null;
}

function startVendorPurchase(vendorId) {
    window.location.href = `purchases.html?vendor_id=${encodeURIComponent(vendorId)}&new=1`;
}

function openVendorPurchase() {
    if (selectedStatementVendorId) startVendorPurchase(selectedStatementVendorId);
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(loadVendors, 300));
    
    // Status filter
    document.getElementById('statusFilter').addEventListener('change', loadVendors);
    
    // Vendor form
    document.getElementById('vendorForm').addEventListener('submit', handleVendorSubmit);
}

// Open vendor modal
function openVendorModal(vendor = null) {
    const modal = document.getElementById('vendorModal');
    const title = document.getElementById('vendorModalTitle');
    const form = document.getElementById('vendorForm');
    
    // Reset form
    form.reset();
    document.getElementById('vendorId').value = '';
    document.getElementById('vendorStatusField').style.display = vendor ? 'block' : 'none';
    
    if (vendor) {
        title.textContent = 'Edit Vendor';
        
        // Populate form with vendor data
        document.getElementById('vendorId').value = vendor.id;
        document.getElementById('vendorCode').value = vendor.vendor_code;
        document.getElementById('vendorName').value = vendor.name;
        document.getElementById('vendorCompanyName').value = vendor.company_name || '';
        document.getElementById('vendorContactPerson').value = vendor.contact_person || '';
        document.getElementById('vendorPhone').value = vendor.phone || '';
        document.getElementById('vendorEmail').value = vendor.email || '';
        document.getElementById('vendorAddress').value = vendor.address || '';
        document.getElementById('vendorGstNumber').value = vendor.gst_number || '';
        document.getElementById('vendorPaymentTerms').value = vendor.payment_terms || '';
        document.getElementById('vendorStatus').value = String(vendor.status);
        document.getElementById('vendorBankDetails').value = vendor.bank_details || '';
        document.getElementById('vendorNotes').value = vendor.notes || '';
    } else {
        title.textContent = 'Add Vendor';
    }
    
    modal.classList.add('show');
}

// Close vendor modal
function closeVendorModal() {
    document.getElementById('vendorModal').classList.remove('show');
}

// View vendor
async function viewVendor(id) {
    try {
        const vendor = await vendorsAPI.getById(id);
        if (vendor) {
            openVendorModal(vendor);
        }
    } catch (error) {
        console.error('Error loading vendor:', error);
        showToast('Failed to load vendor details', 'error');
    }
}

// Edit vendor
async function editVendor(id) {
    try {
        const vendor = await vendorsAPI.getById(id);
        if (vendor) {
            openVendorModal(vendor);
        }
    } catch (error) {
        console.error('Error loading vendor:', error);
        showToast('Failed to load vendor details', 'error');
    }
}

// Handle vendor form submission
async function handleVendorSubmit(event) {
    event.preventDefault();
    
    const vendorId = document.getElementById('vendorId').value;
    
    const vendorData = {
        vendor_code: document.getElementById('vendorCode').value,
        name: document.getElementById('vendorName').value,
        company_name: document.getElementById('vendorCompanyName').value,
        contact_person: document.getElementById('vendorContactPerson').value,
        phone: document.getElementById('vendorPhone').value,
        email: document.getElementById('vendorEmail').value,
        address: document.getElementById('vendorAddress').value,
        gst_number: document.getElementById('vendorGstNumber').value,
        payment_terms: document.getElementById('vendorPaymentTerms').value,
        bank_details: document.getElementById('vendorBankDetails').value,
        notes: document.getElementById('vendorNotes').value,
        ...(vendorId ? { status: document.getElementById('vendorStatus').value === 'true' } : {})
    };
    
    try {
        if (vendorId) {
            // Update existing vendor
            await vendorsAPI.update(parseInt(vendorId), vendorData);
            showToast('Vendor updated successfully', 'success');
        } else {
            // Create new vendor
            await vendorsAPI.create(vendorData);
            showToast('Vendor created successfully', 'success');
        }
        
        closeVendorModal();
        await loadVendors();
    } catch (error) {
        console.error('Error saving vendor:', error);
        showToast('Failed to save vendor: ' + (error.message || ''), 'error');
    }
}

// Delete vendor
async function deleteVendor(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this vendor? This action cannot be undone.')) {
        return;
    }

    try {
        await vendorsAPI.delete(id);
        showToast('Vendor deleted successfully!', 'success');
        await loadVendors();
    } catch (error) {
        console.error('Error deleting vendor:', error);
        showToast('Failed to delete vendor: ' + (error.message || ''), 'error');
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
document.addEventListener('DOMContentLoaded', initVendorsPage);
