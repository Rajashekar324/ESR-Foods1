/**
 * Invoices Page Functions for ESR Foods
 */

let allRestaurants = [];
let allOrders = [];
let allProducts = [];
let invoiceItemCount = 0;

// Initialize invoices page
async function initInvoicesPage() {
    if (!requireAuth()) return;
    
    try {
        // Load restaurants for dropdown
        await loadRestaurantsForDropdown();
        
        // Load orders for dropdown
        await loadOrdersForDropdown();
        
        // Load products for dropdown
        await loadProductsForDropdown();
        
        // Load invoices
        await loadInvoices();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Invoices page initialization error:', error);
        showToast('Failed to load invoices', 'error');
    }
}

// Load restaurants for dropdown
async function loadRestaurantsForDropdown() {
    try {
        allRestaurants = await restaurantsAPI.getAll({ status: true });
        
        const restaurantFilter = document.getElementById('restaurantFilter');
        const invoiceRestaurant = document.getElementById('invoiceRestaurant');
        
        const options = '<option value="">All Restaurants</option>' +
            allRestaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        
        if (restaurantFilter) restaurantFilter.innerHTML = options;
        
        const invoiceOptions = '<option value="">Select Restaurant</option>' +
            allRestaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        
        if (invoiceRestaurant) invoiceRestaurant.innerHTML = invoiceOptions;
    } catch (error) {
        console.error('Error loading restaurants:', error);
    }
}

// Load orders for dropdown
async function loadOrdersForDropdown() {
    try {
        allOrders = await ordersAPI.getAll({ order_status: 'delivered' });
        
        const invoiceOrder = document.getElementById('invoiceOrder');
        
        const options = '<option value="">Select Order (Optional)</option>' +
            allOrders.map(o => `<option value="${o.id}">${o.order_code}</option>`).join('');
        
        if (invoiceOrder) invoiceOrder.innerHTML = options;
    } catch (error) {
        console.error('Error loading orders:', error);
    }
}

// Load products for dropdown
async function loadProductsForDropdown() {
    try {
        allProducts = await productsAPI.getAll({ status: true });
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

// Load invoices
async function loadInvoices() {
    try {
        const restaurantId = document.getElementById('restaurantFilter').value;
        const paymentStatus = document.getElementById('paymentStatusFilter').value;
        const finalized = document.getElementById('finalizedFilter').value;
        
        const params = {};
        if (restaurantId) params.restaurant_id = parseInt(restaurantId);
        if (paymentStatus) params.payment_status = paymentStatus;
        if (finalized) params.is_finalized = finalized === 'true';
        
        const invoices = await invoicesAPI.getAll(params);
        renderInvoicesTable(invoices);
    } catch (error) {
        console.error('Error loading invoices:', error);
        document.getElementById('invoicesTable').innerHTML = '<tr><td colspan="10" style="color: var(--danger-color);">Failed to load invoices</td></tr>';
    }
}

// Render invoices table
function renderInvoicesTable(invoices) {
    const tbody = document.getElementById('invoicesTable');
    
    if (!invoices || invoices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-state"><div class="empty-state-icon">🧾</div><div class="empty-state-text">No invoices found</div></td></tr>';
        return;
    }
    
    const restaurantNames = {};
    allRestaurants.forEach(r => restaurantNames[r.id] = r.name);
    
    tbody.innerHTML = invoices.map(invoice => `
        <tr>
            <td><strong>${invoice.invoice_number}</strong></td>
            <td>${restaurantNames[invoice.restaurant_id] || 'Unknown'}</td>
            <td>${formatDate(invoice.invoice_date)}</td>
            <td>${formatDate(invoice.due_date)}</td>
            <td>${formatCurrency(invoice.grand_total)}</td>
            <td>${formatCurrency(invoice.amount_paid)}</td>
            <td style="color: ${invoice.balance_due > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">
                ${formatCurrency(invoice.balance_due)}
            </td>
            <td><span class="badge badge-info">${invoice.payment_status.replace(/_/g, ' ')}</span></td>
            <td>
                <span class="badge ${invoice.is_finalized ? 'badge-success' : 'badge-warning'}">
                    ${invoice.is_finalized ? 'Finalized' : 'Draft'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="downloadInvoicePdf(${invoice.id})">PDF</button>
                <button class="btn btn-sm btn-outline" onclick="viewInvoice(${invoice.id})">View</button>
                ${!invoice.is_finalized ? `
                    <button class="btn btn-sm btn-secondary" onclick="editInvoice(${invoice.id})">Edit</button>
                    <button class="btn btn-sm btn-accent" onclick="finalizeInvoice(${invoice.id})">Finalize</button>
                ` : ''}
                ${!invoice.is_finalized ? `<button class="btn btn-sm btn-danger" onclick="deleteInvoice(${invoice.id})">Delete Draft</button>` : ''}
            </td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('restaurantFilter').addEventListener('change', loadInvoices);
    document.getElementById('paymentStatusFilter').addEventListener('change', loadInvoices);
    document.getElementById('finalizedFilter').addEventListener('change', loadInvoices);
    
    // Invoice form
    document.getElementById('invoiceForm').addEventListener('submit', handleInvoiceSubmit);
}

// Open invoice modal
function openInvoiceModal(invoice = null, readOnly = false) {
    const modal = document.getElementById('invoiceModal');
    const title = document.getElementById('invoiceModalTitle');
    const form = document.getElementById('invoiceForm');
    
    // Reset form
    form.reset();
    form.querySelectorAll('input, select, textarea, button').forEach(control => {
        control.disabled = false;
        control.hidden = false;
    });
    document.getElementById('invoiceId').value = '';
    document.getElementById('invoiceItems').innerHTML = '';
    invoiceItemCount = 0;
    
    // Set default date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('invoiceDate').value = today;
    
    if (invoice) {
        title.textContent = readOnly ? 'Invoice Details' : 'Edit Draft Invoice';
        
        // Populate form with invoice data
        document.getElementById('invoiceId').value = invoice.id;
        document.getElementById('invoiceNumber').value = invoice.invoice_number;
        document.getElementById('invoiceOrder').value = invoice.order_id || '';
        document.getElementById('invoiceRestaurant').value = invoice.restaurant_id;
        document.getElementById('invoiceDate').value = invoice.invoice_date.split('T')[0];
        document.getElementById('invoiceDueDate').value = invoice.due_date ? invoice.due_date.split('T')[0] : '';
        document.getElementById('invoiceDiscount').value = invoice.discount;
        document.getElementById('invoiceTax').value = invoice.tax;
        document.getElementById('invoiceNotes').value = invoice.notes || '';
        
        // Add existing items
        if (invoice.items && invoice.items.length > 0) {
            invoice.items.forEach(item => {
                addInvoiceItem(item);
            });
        }
        document.getElementById('invoiceNumber').disabled = true;
        if (readOnly) {
            form.querySelectorAll('input, select, textarea, button[type="submit"]').forEach(control => { control.disabled = true; });
            form.querySelectorAll('button[onclick^="removeInvoiceItem"], button[onclick="addInvoiceItem()"]').forEach(control => { control.hidden = true; });
        }
    } else {
        title.textContent = 'New Invoice';
        // Add one empty item row
        addInvoiceItem();
    }

        if (!invoice) document.getElementById('invoiceNumber').disabled = false;
    
    modal.classList.add('show');
}

// Close invoice modal
function closeInvoiceModal() {
    document.getElementById('invoiceModal').classList.remove('show');
}

// Add invoice item row
function addInvoiceItem(itemData = null) {
    invoiceItemCount++;
    const itemIndex = invoiceItemCount;
    
    const itemHtml = `
        <div class="invoice-item" data-index="${itemIndex}">
            <div>
                <label class="form-label">Product</label>
                <select class="form-select item-product" required>
                    <option value="">Select Product</option>
                    ${allProducts.map(p => `<option value="${p.id}">${p.name} (${p.product_code})</option>`).join('')}
                </select>
            </div>
            <div>
                <label class="form-label">Quantity</label>
                <input type="number" class="form-input item-quantity" step="0.01" min="0.01" required>
            </div>
            <div>
                <label class="form-label">Unit</label>
                <input type="text" class="form-input item-unit" required>
            </div>
            <div>
                <label class="form-label">Rate</label>
                <input type="number" class="form-input item-rate" step="0.01" min="0.01" required>
            </div>
            <div>
                <label class="form-label">Discount</label>
                <input type="number" class="form-input item-discount" step="0.01" min="0" value="0">
            </div>
            <div>
                <label class="form-label">Tax</label>
                <input type="number" class="form-input item-tax" step="0.01" min="0" value="0">
            </div>
            <div>
                <label class="form-label">Line Total</label>
                <input type="number" class="form-input item-amount" step="0.01" readonly>
            </div>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeInvoiceItem(${itemIndex})">×</button>
        </div>
    `;
    
    document.getElementById('invoiceItems').insertAdjacentHTML('beforeend', itemHtml);
    
    const itemRow = document.querySelector(`[data-index="${itemIndex}"]`);
    
    if (itemData) {
        itemRow.querySelector('.item-product').value = itemData.product_id;
        itemRow.querySelector('.item-quantity').value = itemData.quantity;
        itemRow.querySelector('.item-unit').value = itemData.unit;
        itemRow.querySelector('.item-rate').value = itemData.rate;
        itemRow.querySelector('.item-discount').value = itemData.discount || 0;
        itemRow.querySelector('.item-tax').value = itemData.tax || 0;
        itemRow.querySelector('.item-amount').value = itemData.amount;
    }
    
    // Add event listeners for auto-calculation
    const quantityInput = itemRow.querySelector('.item-quantity');
    const rateInput = itemRow.querySelector('.item-rate');
    const discountInput = itemRow.querySelector('.item-discount');
    const taxInput = itemRow.querySelector('.item-tax');
    const amountInput = itemRow.querySelector('.item-amount');
    
    const calculateAmount = () => {
        const quantity = parseFloat(quantityInput.value) || 0;
        const rate = parseFloat(rateInput.value) || 0;
        const discount = parseFloat(discountInput.value) || 0;
        const tax = parseFloat(taxInput.value) || 0;
        amountInput.value = (quantity * rate - discount + tax).toFixed(2);
    };
    
    quantityInput.addEventListener('input', calculateAmount);
    rateInput.addEventListener('input', calculateAmount);
    discountInput.addEventListener('input', calculateAmount);
    taxInput.addEventListener('input', calculateAmount);
}

// Remove invoice item
function removeInvoiceItem(index) {
    const itemRow = document.querySelector(`[data-index="${index}"]`);
    if (itemRow) {
        itemRow.remove();
    }
}

// View invoice
async function viewInvoice(id) {
    try {
        const invoice = await invoicesAPI.getById(id);
        if (invoice) {
            openInvoiceModal(invoice, true);
        }
    } catch (error) {
        console.error('Error loading invoice:', error);
        showToast('Failed to load invoice details', 'error');
    }
}

function downloadInvoicePdf(id) {
    window.location.href = `/api/invoices/${id}/pdf`;
}

// Edit invoice
async function editInvoice(id) {
    try {
        const invoice = await invoicesAPI.getById(id);
        if (invoice) {
            openInvoiceModal(invoice);
        }
    } catch (error) {
        console.error('Error loading invoice:', error);
        showToast('Failed to load invoice details', 'error');
    }
}

// Finalize invoice
async function finalizeInvoice(id) {
    if (!confirm('Are you sure you want to finalize this invoice? It cannot be edited after finalization.')) {
        return;
    }
    
    try {
        await invoicesAPI.finalize(id);
        showToast('Invoice finalized successfully', 'success');
        await loadInvoices();
    } catch (error) {
        console.error('Error finalizing invoice:', error);
        showToast('Failed to finalize invoice', 'error');
    }
}

// Handle invoice form submission
async function handleInvoiceSubmit(event) {
    event.preventDefault();
    
    const invoiceId = document.getElementById('invoiceId').value;
    
    // Collect items
    const items = [];
    document.querySelectorAll('.invoice-item').forEach(itemRow => {
        const product_id = parseInt(itemRow.querySelector('.item-product').value);
        const quantity = parseFloat(itemRow.querySelector('.item-quantity').value);
        const unit = itemRow.querySelector('.item-unit').value;
        const rate = parseFloat(itemRow.querySelector('.item-rate').value);
        const discount = parseFloat(itemRow.querySelector('.item-discount').value) || 0;
        const tax = parseFloat(itemRow.querySelector('.item-tax').value) || 0;
        if (product_id && quantity && unit && rate) {
            items.push({
                product_id,
                quantity,
                unit,
                rate,
                discount,
                tax
            });
        }
    });
    
    if (items.length === 0) {
        showToast('Please add at least one item', 'error');
        return;
    }
    
    const invoiceData = {
        invoice_number: document.getElementById('invoiceNumber').value.trim() || null,
        order_id: document.getElementById('invoiceOrder').value ? parseInt(document.getElementById('invoiceOrder').value) : null,
        restaurant_id: parseInt(document.getElementById('invoiceRestaurant').value),
        invoice_date: toIsoDateTime(document.getElementById('invoiceDate').value),
        due_date: toIsoDateTime(document.getElementById('invoiceDueDate').value || null),
        discount: parseFloat(document.getElementById('invoiceDiscount').value),
        tax: parseFloat(document.getElementById('invoiceTax').value),
        notes: document.getElementById('invoiceNotes').value,
        items: items
    };
    
    try {
        if (invoiceId) {
            // Update existing invoice
            await invoicesAPI.update(parseInt(invoiceId), invoiceData);
            showToast('Invoice updated successfully', 'success');
        } else {
            // Create new invoice
            await invoicesAPI.create(invoiceData);
            showToast('Invoice created successfully', 'success');
        }
        
        closeInvoiceModal();
        await loadInvoices();
    } catch (error) {
        console.error('Error saving invoice:', error);
        showToast('Failed to save invoice: ' + (error.message || ''), 'error');
    }
}

// Delete invoice
async function deleteInvoice(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this invoice? This action cannot be undone.')) {
        return;
    }

    try {
        await invoicesAPI.delete(id);
        showToast('Invoice deleted successfully', 'success');
        await loadInvoices();
    } catch (error) {
        console.error('Error deleting invoice:', error);
        showToast('Failed to delete invoice: ' + (error.message || ''), 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initInvoicesPage);
