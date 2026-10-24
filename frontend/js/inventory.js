/**
 * Inventory Page Functions for ESR Foods
 */

let allProducts = [];
let allVendors = [];

// Initialize inventory page
async function initInventoryPage() {
    if (!requireAuth()) return;
    
    try {
        // Load summary stats
        await loadInventorySummary();
        
        // Load products for dropdowns
        await loadProductsForDropdowns();
        
        // Load vendors for dropdowns
        await loadVendorsForDropdowns();
        
        // Load inventory data
        await loadInventory();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Inventory page initialization error:', error);
        showToast('Failed to load inventory', 'error');
    }
}

// Load inventory summary
async function loadInventorySummary() {
    try {
        const summary = await inventoryAPI.getSummary();
        
        if (summary) {
            document.getElementById('totalProducts').textContent = summary.total_products;
            document.getElementById('totalStockValue').textContent = formatCurrency(summary.total_stock_value);
            document.getElementById('lowStockItems').textContent = summary.low_stock_products;
            document.getElementById('expiringSoon').textContent = summary.expiring_products;
        }
    } catch (error) {
        console.error('Error loading inventory summary:', error);
    }
}

// Load products for dropdowns
async function loadProductsForDropdowns() {
    try {
        allProducts = await productsAPI.getAll({ status: true });
        
        const adjustmentProduct = document.getElementById('adjustmentProduct');
        const batchProduct = document.getElementById('batchProduct');
        
        const options = '<option value="">Select Product</option>' +
            allProducts.map(p => `<option value="${p.id}">${p.name} (${p.product_code})</option>`).join('');
        
        if (adjustmentProduct) adjustmentProduct.innerHTML = options;
        if (batchProduct) batchProduct.innerHTML = options;
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

// Load vendors for dropdowns
async function loadVendorsForDropdowns() {
    try {
        allVendors = await vendorsAPI.getAll({ status: true });
        
        const batchVendor = document.getElementById('batchVendor');
        
        const options = '<option value="">Select Vendor</option>' +
            allVendors.map(v => `<option value="${v.id}">${v.name}</option>`).join('');
        
        if (batchVendor) batchVendor.innerHTML = options;
    } catch (error) {
        console.error('Error loading vendors:', error);
    }
}

// Load inventory
async function loadInventory() {
    try {
        const lowStockOnly = document.getElementById('lowStockOnly').checked;
        const expiringOnly = document.getElementById('expiringOnly').checked;
        
        const params = {};
        if (lowStockOnly) params.low_stock_only = true;
        if (expiringOnly) params.expiring_only = true;
        
        const inventory = await inventoryAPI.getAll(params);
        renderInventoryTable(inventory);
    } catch (error) {
        console.error('Error loading inventory:', error);
        document.getElementById('inventoryTable').innerHTML = '<tr><td colspan="7" style="color: var(--danger-color);">Failed to load inventory</td></tr>';
    }
}

// Render inventory table
function renderInventoryTable(inventory) {
    const tbody = document.getElementById('inventoryTable');
    
    if (!inventory || inventory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-text">No inventory items found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = inventory.map(item => `
        <tr>
            <td><strong>${item.name}</strong><br><small>${item.product_code}</small></td>
            <td style="color: ${item.is_low_stock ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">
                ${item.current_stock}
            </td>
            <td>${item.unit}</td>
            <td>${formatCurrency(item.purchase_price)}</td>
            <td>${formatCurrency(item.selling_price)}</td>
            <td>${formatCurrency(item.stock_value)}</td>
            <td>
                ${item.is_critical ? '<span class="badge badge-danger">Critical</span>' : 
                  item.is_low_stock ? '<span class="badge badge-warning">Low Stock</span>' : 
                  '<span class="badge badge-success">Normal</span>'}
            </td>
        </tr>
    `).join('');
}

// Load stock movements
async function loadMovements() {
    try {
        const movementType = document.getElementById('movementTypeFilter').value;
        
        const params = {};
        if (movementType) params.movement_type = movementType;
        
        const movements = await inventoryAPI.getMovements(params);
        renderMovementsTable(movements);
    } catch (error) {
        console.error('Error loading movements:', error);
        document.getElementById('movementsTable').innerHTML = '<tr><td colspan="6" style="color: var(--danger-color);">Failed to load movements</td></tr>';
    }
}

// Render movements table
function renderMovementsTable(movements) {
    const tbody = document.getElementById('movementsTable');
    
    if (!movements || movements.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No movements found</div></td></tr>';
        return;
    }
    
    const productNames = {};
    allProducts.forEach(p => productNames[p.id] = p.name);
    
    tbody.innerHTML = movements.map(m => `
        <tr>
            <td>${formatDateTime(m.created_at)}</td>
            <td>${productNames[m.product_id] || 'Unknown'}</td>
            <td><span class="badge badge-info">${m.movement_type.replace(/_/g, ' ')}</span></td>
            <td>${m.quantity} ${m.unit}</td>
            <td>${m.balance_after}</td>
            <td><small>${m.notes || '-'}</small></td>
        </tr>
    `).join('');
}

// Load batches
async function loadBatches() {
    try {
        const status = document.getElementById('batchStatusFilter').value;
        
        const params = {};
        if (status) params.status = status;
        
        const batches = await inventoryAPI.getBatches(params);
        renderBatchesTable(batches);
    } catch (error) {
        console.error('Error loading batches:', error);
        document.getElementById('batchesTable').innerHTML = '<tr><td colspan="8" style="color: var(--danger-color);">Failed to load batches</td></tr>';
    }
}

// Render batches table
function renderBatchesTable(batches) {
    const tbody = document.getElementById('batchesTable');
    
    if (!batches || batches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-text">No batches found</div></td></tr>';
        return;
    }
    
    const productNames = {};
    allProducts.forEach(p => productNames[p.id] = p.name);
    
    const vendorNames = {};
    allVendors.forEach(v => vendorNames[v.id] = v.name);
    
    tbody.innerHTML = batches.map(b => `
        <tr>
            <td><strong>${b.batch_number}</strong></td>
            <td>${productNames[b.product_id] || 'Unknown'}</td>
            <td>${vendorNames[b.vendor_id] || 'Unknown'}</td>
            <td>${formatDate(b.received_date)}</td>
            <td>${b.quantity}</td>
            <td style="color: ${b.remaining_quantity <= 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">
                ${b.remaining_quantity}
            </td>
            <td>${b.expiry_date ? formatDate(b.expiry_date) : '-'}</td>
            <td>
                <span class="badge ${b.status === 'normal' ? 'badge-success' : b.status === 'expiring_soon' ? 'badge-warning' : 'badge-danger'}">
                    ${b.status.replace(/_/g, ' ')}
                </span>
            </td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Inventory filters
    document.getElementById('lowStockOnly').addEventListener('change', loadInventory);
    document.getElementById('expiringOnly').addEventListener('change', loadInventory);
    
    // Movement filter
    document.getElementById('movementTypeFilter').addEventListener('change', loadMovements);
    
    // Batch filter
    document.getElementById('batchStatusFilter').addEventListener('change', loadBatches);
    
    // Adjustment form
    document.getElementById('adjustmentForm').addEventListener('submit', handleAdjustmentSubmit);
    
    // Batch form
    document.getElementById('batchForm').addEventListener('submit', handleBatchSubmit);
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    // Load data for the active tab
    if (tabName === 'inventory') {
        loadInventory();
    } else if (tabName === 'movements') {
        loadMovements();
    } else if (tabName === 'batches') {
        loadBatches();
    }
}

// Open adjustment modal
function openAdjustmentModal() {
    document.getElementById('adjustmentModal').classList.add('show');
    document.getElementById('adjustmentForm').reset();
}

// Close adjustment modal
function closeAdjustmentModal() {
    document.getElementById('adjustmentModal').classList.remove('show');
}

// Handle adjustment form submission
async function handleAdjustmentSubmit(event) {
    event.preventDefault();
    
    const adjustmentData = {
        product_id: parseInt(document.getElementById('adjustmentProduct').value),
        movement_type: document.getElementById('adjustmentType').value,
        quantity: parseFloat(document.getElementById('adjustmentQuantity').value),
        unit: document.getElementById('adjustmentUnit').value,
        rate: document.getElementById('adjustmentRate').value ? parseFloat(document.getElementById('adjustmentRate').value) : null,
        notes: document.getElementById('adjustmentNotes').value
    };
    
    try {
        await inventoryAPI.createAdjustment(adjustmentData);
        showToast('Stock adjustment saved successfully', 'success');
        closeAdjustmentModal();
        await loadInventorySummary();
        await loadInventory();
    } catch (error) {
        console.error('Error saving adjustment:', error);
        showToast('Failed to save adjustment', 'error');
    }
}

// Open batch modal
function openBatchModal() {
    document.getElementById('batchModal').classList.add('show');
    document.getElementById('batchForm').reset();
    
    // Set default dates
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('batchPurchaseDate').value = today;
    document.getElementById('batchReceivedDate').value = today;
}

// Close batch modal
function closeBatchModal() {
    document.getElementById('batchModal').classList.remove('show');
}

// Handle batch form submission
async function handleBatchSubmit(event) {
    event.preventDefault();
    
    const batchData = {
        batch_number: document.getElementById('batchNumber').value,
        product_id: parseInt(document.getElementById('batchProduct').value),
        vendor_id: parseInt(document.getElementById('batchVendor').value),
        purchase_date: toIsoDateTime(document.getElementById('batchPurchaseDate').value),
        received_date: toIsoDateTime(document.getElementById('batchReceivedDate').value),
        quantity: parseFloat(document.getElementById('batchQuantity').value),
        purchase_rate: parseFloat(document.getElementById('batchPurchaseRate').value),
        manufacturing_date: toIsoDateTime(document.getElementById('batchManufacturingDate').value || null),
        expiry_date: toIsoDateTime(document.getElementById('batchExpiryDate').value || null),
        storage_location: document.getElementById('batchStorageLocation').value
    };
    
    try {
        await inventoryAPI.createBatch(batchData);
        showToast('Batch created successfully', 'success');
        closeBatchModal();
        await loadBatches();
    } catch (error) {
        console.error('Error creating batch:', error);
        showToast('Failed to create batch', 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initInventoryPage);
