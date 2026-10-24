/**
 * Purchases Page Functions for ESR Foods
 */

let allVendors = [];
let allProducts = [];
let purchaseItemCount = 0;
let presetVendorId = null;

// Initialize purchases page
async function initPurchasesPage() {
    if (!requireAuth()) return;
    
    try {
        // Load vendors for dropdown
        await loadVendorsForDropdown();
        
        // Load products for dropdown
        await loadProductsForDropdown();

        const pageParams = new URLSearchParams(window.location.search);
        presetVendorId = parseInt(pageParams.get('vendor_id'), 10) || null;
        if (presetVendorId) {
            document.getElementById('vendorFilter').value = String(presetVendorId);
            document.getElementById('purchaseVendor').value = String(presetVendorId);
        }
        
        // Load purchases
        await loadPurchases();
        
        // Setup event listeners
        setupEventListeners();

        if (presetVendorId && pageParams.get('new') === '1') {
            openPurchaseModal();
        }
        
    } catch (error) {
        console.error('Purchases page initialization error:', error);
        showToast('Failed to load purchases', 'error');
    }
}

// Load vendors for dropdown
async function loadVendorsForDropdown() {
    try {
        allVendors = await vendorsAPI.getAll({ status: true });
        
        const vendorFilter = document.getElementById('vendorFilter');
        const purchaseVendor = document.getElementById('purchaseVendor');
        
        const options = '<option value="">All Vendors</option>' +
            allVendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
        
        if (vendorFilter) vendorFilter.innerHTML = options;
        
        const purchaseOptions = '<option value="">Select Vendor</option>' +
            allVendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
        
        if (purchaseVendor) purchaseVendor.innerHTML = purchaseOptions;
    } catch (error) {
        console.error('Error loading vendors:', error);
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

// Load purchases
async function loadPurchases() {
    try {
        const vendorId = document.getElementById('vendorFilter').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (vendorId) params.vendor_id = parseInt(vendorId);
        if (status) params.status = status;
        
        const purchases = await purchasesAPI.getAll(params);
        renderPurchasesTable(purchases);
    } catch (error) {
        console.error('Error loading purchases:', error);
        document.getElementById('purchasesTable').innerHTML = '<tr><td colspan="7" style="color: var(--danger-color);">Failed to load purchases</td></tr>';
    }
}

// Render purchases table
function renderPurchasesTable(purchases) {
    const tbody = document.getElementById('purchasesTable');
    
    if (!purchases || purchases.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="empty-state-icon">🛒</div><div class="empty-state-text">No purchases found</div></td></tr>';
        return;
    }
    
    const vendorNames = {};
    allVendors.forEach(v => vendorNames[v.id] = v.name);
    
    tbody.innerHTML = purchases.map(purchase => `
        <tr>
            <td><strong>${purchase.purchase_code}</strong></td>
            <td>${vendorNames[purchase.vendor_id] || 'Unknown'}</td>
            <td>${formatDate(purchase.purchase_date)}</td>
            <td>${formatCurrency(purchase.total)}</td>
            <td><span class="badge badge-info">${purchase.payment_status}</span></td>
            <td>
                <span class="badge ${purchase.status === 'received' ? 'badge-success' : purchase.status === 'cancelled' ? 'badge-danger' : 'badge-warning'}">
                    ${purchase.status.replace(/_/g, ' ')}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewPurchase(${purchase.id})">View</button>
                ${purchase.status === 'draft' || purchase.status === 'ordered' ? `
                    <button class="btn btn-sm btn-secondary" onclick="editPurchase(${purchase.id})">Edit</button>
                ` : ''}
                ${purchase.status === 'ordered' || purchase.status === 'partially_received' ? `
                    <button class="btn btn-sm btn-accent" onclick="receivePurchase(${purchase.id})">Receive</button>
                ` : ''}
                ${purchase.status !== 'cancelled' ? `<button class="btn btn-sm btn-danger" onclick="deletePurchase(${purchase.id})">Cancel</button>` : ''}
            </td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('vendorFilter').addEventListener('change', loadPurchases);
    document.getElementById('statusFilter').addEventListener('change', loadPurchases);
    
    // Purchase form
    document.getElementById('purchaseForm').addEventListener('submit', handlePurchaseSubmit);
}

// Open purchase modal
function openPurchaseModal(purchase = null) {
    const modal = document.getElementById('purchaseModal');
    const title = document.getElementById('purchaseModalTitle');
    const form = document.getElementById('purchaseForm');
    
    // Reset form
    form.reset();
    document.getElementById('purchaseId').value = '';
    document.getElementById('purchaseItems').innerHTML = '';
    purchaseItemCount = 0;
    
    // Set default date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('purchaseDate').value = today;
    document.getElementById('purchaseCode').value = `PO-${Date.now()}`;
    
    if (purchase) {
        title.textContent = 'Edit Purchase';
        
        // Populate form with purchase data
        document.getElementById('purchaseId').value = purchase.id;
        document.getElementById('purchaseCode').value = purchase.purchase_code;
        document.getElementById('purchaseVendor').value = purchase.vendor_id;
        document.getElementById('purchaseVendorInvoice').value = purchase.vendor_invoice_number || '';
        document.getElementById('purchaseDate').value = purchase.purchase_date.split('T')[0];
        document.getElementById('purchaseExpectedDate').value = purchase.expected_date ? purchase.expected_date.split('T')[0] : '';
        document.getElementById('purchaseDiscount').value = purchase.discount;
        document.getElementById('purchaseTax').value = purchase.tax;
        document.getElementById('purchaseNotes').value = purchase.notes || '';
        
        // Add existing items
        if (purchase.items && purchase.items.length > 0) {
            purchase.items.forEach(item => {
                addPurchaseItem(item);
            });
        }
    } else {
        title.textContent = 'New Purchase';
        if (presetVendorId) document.getElementById('purchaseVendor').value = String(presetVendorId);
        else if (document.getElementById('vendorFilter').value) document.getElementById('purchaseVendor').value = document.getElementById('vendorFilter').value;
        // Add one empty item row
        addPurchaseItem();
    }
    
    modal.classList.add('show');
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

// Close purchase modal
function closePurchaseModal() {
    document.getElementById('purchaseModal').classList.remove('show');
}

// Add purchase item row
function addPurchaseItem(itemData = null) {
    purchaseItemCount++;
    const itemIndex = purchaseItemCount;
    
    const itemHtml = `
        <div class="purchase-item" data-index="${itemIndex}"${itemData?.id ? ` data-item-id="${itemData.id}"` : ''} style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr auto; gap: 10px; margin-bottom: 10px; align-items: end;">
            <div>
                <label class="form-label">Product</label>
                <select class="form-select item-product" required>
                    <option value="">Select Product</option>
                    ${allProducts.map(p => `<option value="${p.id}">${p.name} (${p.product_code})</option>`).join('')}
                </select>
            </div>
            <div>
                <label class="form-label">Quantity</label>
                <input type="number" class="form-input item-quantity" step="0.1" required>
            </div>
            <div>
                <label class="form-label">Unit</label>
                <input type="text" class="form-input item-unit" required>
            </div>
            <div>
                <label class="form-label">Rate</label>
                <input type="number" class="form-input item-rate" step="0.01" required>
            </div>
            <div>
                <label class="form-label">Total</label>
                <input type="number" class="form-input item-total" step="0.01" readonly>
            </div>
            <button type="button" class="btn btn-sm btn-danger" onclick="removePurchaseItem(${itemIndex})">×</button>
        </div>
    `;
    
    document.getElementById('purchaseItems').insertAdjacentHTML('beforeend', itemHtml);
    
    const itemRow = document.querySelector(`[data-index="${itemIndex}"]`);
    
    if (itemData) {
        itemRow.querySelector('.item-product').value = String(itemData.product_id);
        itemRow.querySelector('.item-quantity').value = itemData.quantity;
        itemRow.querySelector('.item-unit').value = itemData.unit;
        itemRow.querySelector('.item-rate').value = itemData.rate;
    }
    
    // Add event listeners for auto-calculation
    const quantityInput = itemRow.querySelector('.item-quantity');
    const rateInput = itemRow.querySelector('.item-rate');
    const totalInput = itemRow.querySelector('.item-total');
    
    const calculateTotal = () => {
        const quantity = parseFloat(quantityInput.value) || 0;
        const rate = parseFloat(rateInput.value) || 0;
        totalInput.value = (quantity * rate).toFixed(2);
        updatePurchaseTotals();
    };
    
    quantityInput.addEventListener('input', calculateTotal);
    rateInput.addEventListener('input', calculateTotal);
    calculateTotal();
}

function updatePurchaseTotals() {
    const subtotal = Array.from(document.querySelectorAll('.purchase-item')).reduce((sum, row) => {
        const quantity = parseFloat(row.querySelector('.item-quantity').value) || 0;
        const rate = parseFloat(row.querySelector('.item-rate').value) || 0;
        return sum + quantity * rate;
    }, 0);
    const discount = parseFloat(document.getElementById('purchaseDiscount').value) || 0;
    const tax = parseFloat(document.getElementById('purchaseTax').value) || 0;
    return { subtotal, total: subtotal - discount + tax };
}

// Remove purchase item
function removePurchaseItem(index) {
    const itemRow = document.querySelector(`[data-index="${index}"]`);
    if (itemRow) {
        itemRow.remove();
    }
}

// View purchase
async function viewPurchase(id) {
    try {
        const purchase = await purchasesAPI.getById(id);
        if (purchase) {
            openPurchaseModal(purchase);
        }
    } catch (error) {
        console.error('Error loading purchase:', error);
        showToast('Failed to load purchase details', 'error');
    }
}

// Edit purchase
async function editPurchase(id) {
    try {
        const purchase = await purchasesAPI.getById(id);
        if (purchase) {
            openPurchaseModal(purchase);
        }
    } catch (error) {
        console.error('Error loading purchase:', error);
        showToast('Failed to load purchase details', 'error');
    }
}

// Receive purchase
async function receivePurchase(id) {
    if (!confirm('Are you sure you want to receive this purchase? This will update inventory.')) {
        return;
    }
    
    try {
        await purchasesAPI.receive(id);
        showToast('Purchase received successfully, inventory updated', 'success');
        await loadPurchases();
    } catch (error) {
        console.error('Error receiving purchase:', error);
        showToast('Failed to receive purchase', 'error');
    }
}

// Handle purchase form submission
async function handlePurchaseSubmit(event) {
    event.preventDefault();
    
    const purchaseId = document.getElementById('purchaseId').value;
    
    // Collect items
    const items = [];
    document.querySelectorAll('.purchase-item').forEach(itemRow => {
        const product_id = parseInt(itemRow.querySelector('.item-product').value);
        const quantity = parseFloat(itemRow.querySelector('.item-quantity').value);
        const unit = itemRow.querySelector('.item-unit').value;
        const rate = parseFloat(itemRow.querySelector('.item-rate').value);
        const total = parseFloat(itemRow.querySelector('.item-total').value);
        
        if (product_id && quantity && unit && rate) {
            items.push({
                ...(itemRow.dataset.itemId ? { id: parseInt(itemRow.dataset.itemId, 10) } : {}),
                product_id,
                quantity,
                unit,
                rate,
                discount: 0,
                tax: 0,
                total
            });
        }
    });
    
    if (items.length === 0) {
        showToast('Please add at least one item', 'error');
        return;
    }
    
    const totals = updatePurchaseTotals();
    const purchaseData = {
        purchase_code: document.getElementById('purchaseCode').value,
        vendor_id: parseInt(document.getElementById('purchaseVendor').value),
        vendor_invoice_number: document.getElementById('purchaseVendorInvoice').value,
        purchase_date: toIsoDateTime(document.getElementById('purchaseDate').value),
        expected_date: toIsoDateTime(document.getElementById('purchaseExpectedDate').value || null),
        discount: parseFloat(document.getElementById('purchaseDiscount').value),
        tax: parseFloat(document.getElementById('purchaseTax').value),
        subtotal: totals.subtotal,
        total: totals.total,
        notes: document.getElementById('purchaseNotes').value,
        items
    };
    
    try {
        if (purchaseId) {
            // Update existing purchase
            await purchasesAPI.update(parseInt(purchaseId), purchaseData);
            showToast('Purchase updated successfully', 'success');
        } else {
            // Create new purchase
            await purchasesAPI.create(purchaseData);
            showToast('Purchase created successfully', 'success');
        }
        
        closePurchaseModal();
        await loadPurchases();
    } catch (error) {
        console.error('Error saving purchase:', error);
        showToast('Failed to save purchase', 'error');
    }
}

// Delete purchase
async function deletePurchase(id) {
    if (!confirm('Cancel this purchase? Its record will be retained and its pending payable will be removed. Received or paid purchases cannot be cancelled.')) {
        return;
    }

    try {
        if (typeof purchasesAPI !== 'undefined' && typeof purchasesAPI.delete === 'function') {
            await purchasesAPI.delete(id);
        } else {
            await apiRequest(`/purchases/${id}`, { method: 'DELETE' });
        }
        showToast('Purchase cancelled; its history was retained.', 'success');
        await loadPurchases();
    } catch (error) {
        console.error('Error deleting purchase:', error);
        showToast('Failed to delete purchase: ' + (error.message || ''), 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initPurchasesPage);
