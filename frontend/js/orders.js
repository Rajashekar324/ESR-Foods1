/**
 * Orders Page Functions for ESR Foods
 */

let allRestaurants = [];
let allCustomers = [];
let allProducts = [];
let orderItemCount = 0;

// Initialize orders page
async function initOrdersPage() {
    if (!requireAuth()) return;
    
    try {
        // Load restaurants for dropdown
        await loadRestaurantsForDropdown();
        
        // Load customers for dropdown
        await loadCustomersForDropdown();
        
        // Load products for dropdown
        await loadProductsForDropdown();
        
        // Load orders
        await loadOrders();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Orders page initialization error:', error);
        showToast('Failed to load orders', 'error');
    }
}

// Load restaurants for dropdown
async function loadRestaurantsForDropdown() {
    try {
        allRestaurants = await restaurantsAPI.getAll({ status: true });
        
        const restaurantFilter = document.getElementById('restaurantFilter');
        const orderRestaurant = document.getElementById('orderRestaurant');
        
        const options = '<option value="">All Restaurants</option>' +
            allRestaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        
        if (restaurantFilter) restaurantFilter.innerHTML = options;
        
        const orderOptions = '<option value="">Select Restaurant</option>' +
            allRestaurants.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        
        if (orderRestaurant) orderRestaurant.innerHTML = orderOptions;
    } catch (error) {
        console.error('Error loading restaurants:', error);
    }
}

// Load customers for dropdown
async function loadCustomersForDropdown() {
    try {
        allCustomers = await customersAPI.getAll({ status: true });
        
        const orderCustomer = document.getElementById('orderCustomer');
        
        const options = '<option value="">Select Customer</option>' +
            allCustomers.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        
        if (orderCustomer) orderCustomer.innerHTML = options;
    } catch (error) {
        console.error('Error loading customers:', error);
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

// Load orders
async function loadOrders() {
    try {
        const customerType = document.getElementById('customerTypeFilter').value;
        const restaurantId = document.getElementById('restaurantFilter').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (customerType) params.customer_type = customerType;
        if (restaurantId) params.restaurant_id = parseInt(restaurantId);
        if (status) params.order_status = status;
        
        const orders = await ordersAPI.getAll(params);
        renderOrdersTable(orders);
    } catch (error) {
        console.error('Error loading orders:', error);
        document.getElementById('ordersTable').innerHTML = '<tr><td colspan="8" style="color: var(--danger-color);">Failed to load orders</td></tr>';
    }
}

// Render orders table
function renderOrdersTable(orders) {
    const tbody = document.getElementById('ordersTable');
    
    if (!orders || orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No orders found</div></td></tr>';
        return;
    }
    
    const restaurantNames = {};
    allRestaurants.forEach(r => restaurantNames[r.id] = r.name);
    
    const customerNames = {};
    allCustomers.forEach(c => customerNames[c.id] = c.name);
    
    tbody.innerHTML = orders.map(order => {
        const customerName = order.customer_type === 'restaurant' 
            ? restaurantNames[order.restaurant_id] || 'Unknown'
            : customerNames[order.customer_id] || 'Unknown';
        
        return `
            <tr>
                <td><strong>${order.order_code}</strong></td>
                <td><span class="badge badge-info">${order.customer_type}</span></td>
                <td>${customerName}</td>
                <td>${formatDate(order.order_date)}</td>
                <td>${formatCurrency(order.total)}</td>
                <td>
                    <span class="badge ${order.order_status === 'delivered' ? 'badge-success' : order.order_status === 'cancelled' ? 'badge-danger' : 'badge-warning'}">
                        ${order.order_status.replace(/_/g, ' ')}
                    </span>
                </td>
                <td>
                    <span class="badge badge-info">${order.delivery_status.replace(/_/g, ' ')}</span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewOrder(${order.id})">View</button>
                    <button class="btn btn-sm btn-primary" onclick="downloadOrderBill(${order.id})">Get bill PDF</button>
                    ${order.order_status === 'confirmed' || order.order_status === 'processing' || order.order_status === 'packed' ? `
                        <button class="btn btn-sm btn-accent" onclick="completeOrder(${order.id})">Complete</button>
                    ` : ''}
                    ${order.order_status !== 'cancelled' && order.order_status !== 'delivered' ? `
                        <button class="btn btn-sm btn-secondary" onclick="cancelOrder(${order.id})">Cancel</button>
                    ` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteOrder(${order.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('customerTypeFilter').addEventListener('change', loadOrders);
    document.getElementById('restaurantFilter').addEventListener('change', loadOrders);
    document.getElementById('statusFilter').addEventListener('change', loadOrders);
    
    // Order form
    document.getElementById('orderForm').addEventListener('submit', handleOrderSubmit);
}

// Handle customer type change
function handleCustomerTypeChange() {
    const customerType = document.getElementById('orderCustomerType').value;
    const restaurantField = document.getElementById('restaurantField');
    const customerField = document.getElementById('customerField');
    
    if (customerType === 'restaurant') {
        restaurantField.style.display = 'block';
        customerField.style.display = 'none';
        document.getElementById('orderRestaurant').required = true;
        document.getElementById('orderCustomer').required = false;
    } else {
        restaurantField.style.display = 'none';
        customerField.style.display = 'block';
        document.getElementById('orderCustomer').required = true;
        document.getElementById('orderRestaurant').required = false;
    }
}

// Open order modal
function openOrderModal(order = null) {
    const modal = document.getElementById('orderModal');
    const title = document.getElementById('orderModalTitle');
    const form = document.getElementById('orderForm');
    
    // Reset form
    form.reset();
    document.getElementById('orderId').value = '';
    document.getElementById('orderItems').innerHTML = '';
    orderItemCount = 0;
    
    // Set default date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('orderDate').value = today;
    
    // Reset customer type display
    handleCustomerTypeChange();
    
    if (order) {
        title.textContent = 'Edit Order';
        
        // Populate form with order data
        document.getElementById('orderId').value = order.id;
        document.getElementById('orderCode').value = order.order_code;
        document.getElementById('orderCustomerType').value = order.customer_type;
        handleCustomerTypeChange();
        
        if (order.customer_type === 'restaurant') {
            document.getElementById('orderRestaurant').value = order.restaurant_id || '';
        } else {
            document.getElementById('orderCustomer').value = order.customer_id || '';
        }
        
        document.getElementById('orderDate').value = order.order_date.split('T')[0];
        document.getElementById('orderDeliveryDate').value = order.delivery_date ? order.delivery_date.split('T')[0] : '';
        document.getElementById('orderDiscount').value = order.discount;
        document.getElementById('orderTax').value = order.tax;
        document.getElementById('orderNotes').value = order.notes || '';
        
        // Add existing items
        if (order.items && order.items.length > 0) {
            order.items.forEach(item => {
                addOrderItem(item);
            });
        }
    } else {
        title.textContent = 'New Order';
        // Auto generate order code
        const dateStr = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 17);
        const uniqueSuffix = Math.random().toString(36).slice(2, 7).toUpperCase();
        document.getElementById('orderCode').value = `SO-${dateStr}-${uniqueSuffix}`;
        // Add one empty item row
        addOrderItem();
    }
    
    modal.classList.add('show');
}

// Download a printable bill for an order
function downloadOrderBill(id) {
    const link = document.createElement('a');
    link.href = `/api/orders/${id}/bill.pdf`;
    link.download = `bill-order-${id}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
}

// Close order modal
function closeOrderModal() {
    document.getElementById('orderModal').classList.remove('show');
}

// Add order item row
function addOrderItem(itemData = null) {
    orderItemCount++;
    const itemIndex = orderItemCount;
    
    const itemHtml = `
        <div class="order-item" data-index="${itemIndex}" style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr auto; gap: 10px; margin-bottom: 10px; align-items: end;">
            <div>
                <label class="form-label">Product</label>
                <select class="form-select item-product" required>
                    <option value="">Select Product</option>
                    ${allProducts.map(p => `<option value="${p.id}">${p.name} (${p.product_code})</option>`).join('')}
                </select>
            </div>
            <div>
                <label class="form-label">Quantity</label>
                <input type="number" class="form-input item-quantity" step="0.1" min="0.1" required placeholder="0.0">
            </div>
            <div>
                <label class="form-label">Unit</label>
                <input type="text" class="form-input item-unit" required placeholder="kg">
            </div>
            <div>
                <label class="form-label">Selling Price</label>
                <input type="number" class="form-input item-selling-price" step="0.01" min="0.01" required placeholder="0.00">
            </div>
            <div>
                <label class="form-label">Total</label>
                <input type="number" class="form-input item-total" step="0.01" readonly placeholder="0.00">
            </div>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeOrderItem(${itemIndex})">×</button>
        </div>
    `;
    
    document.getElementById('orderItems').insertAdjacentHTML('beforeend', itemHtml);
    
    const itemRow = document.querySelector(`[data-index="${itemIndex}"]`);
    const productSelect = itemRow.querySelector('.item-product');
    const quantityInput = itemRow.querySelector('.item-quantity');
    const unitInput = itemRow.querySelector('.item-unit');
    const priceInput = itemRow.querySelector('.item-selling-price');
    const totalInput = itemRow.querySelector('.item-total');

    if (itemData) {
        productSelect.value = itemData.product_id;
        quantityInput.value = itemData.quantity;
        unitInput.value = itemData.unit;
        priceInput.value = itemData.selling_price;
        totalInput.value = itemData.total;
    }

    // Auto populate unit and price when selecting product
    productSelect.addEventListener('change', () => {
        const selectedId = parseInt(productSelect.value);
        const prod = allProducts.find(p => p.id === selectedId);
        if (prod) {
            unitInput.value = prod.unit || 'kg';
            priceInput.value = prod.wholesale_price || prod.retail_price || 0;
            calculateTotal();
        }
    });

    const calculateTotal = () => {
        const quantity = parseFloat(quantityInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        totalInput.value = (quantity * price).toFixed(2);
    };

    quantityInput.addEventListener('input', calculateTotal);
    priceInput.addEventListener('input', calculateTotal);
}

// Remove order item
function removeOrderItem(index) {
    const itemRow = document.querySelector(`[data-index="${index}"]`);
    if (itemRow) {
        itemRow.remove();
    }
}

// View order
async function viewOrder(id) {
    try {
        const order = await ordersAPI.getById(id);
        if (order) {
            openOrderModal(order);
        }
    } catch (error) {
        console.error('Error loading order:', error);
        showToast('Failed to load order details', 'error');
    }
}

// Complete order
async function completeOrder(id) {
    if (!confirm('Are you sure you want to complete this order? This will deduct stock.')) {
        return;
    }
    
    try {
        await ordersAPI.complete(id);
        showToast('Order completed successfully, stock deducted', 'success');
        await loadOrders();
    } catch (error) {
        console.error('Error completing order:', error);
        showToast('Failed to complete order: ' + (error.message || ''), 'error');
    }
}

// Cancel order
async function cancelOrder(id) {
    if (!confirm('Are you sure you want to cancel this order? Stock will be restored if already deducted.')) {
        return;
    }
    
    try {
        await ordersAPI.cancel(id);
        showToast('Order cancelled successfully', 'success');
        await loadOrders();
    } catch (error) {
        console.error('Error cancelling order:', error);
        showToast('Failed to cancel order: ' + (error.message || ''), 'error');
    }
}

// Delete order
async function deleteOrder(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this order? This action cannot be undone.')) {
        return;
    }

    try {
        await ordersAPI.delete(id);
        showToast('Order deleted successfully!', 'success');
        await loadOrders();
    } catch (error) {
        console.error('Error deleting order:', error);
        showToast('Failed to delete order: ' + (error.message || ''), 'error');
    }
}

// Handle order form submission
async function handleOrderSubmit(event) {
    event.preventDefault();
    
    const orderId = document.getElementById('orderId').value;
    const customerType = document.getElementById('orderCustomerType').value;
    
    let restaurant_id = null;
    let customer_id = null;

    if (customerType === 'restaurant') {
        const val = document.getElementById('orderRestaurant').value;
        if (!val) {
            showToast('Please select a restaurant', 'error');
            return;
        }
        restaurant_id = parseInt(val);
    } else {
        const val = document.getElementById('orderCustomer').value;
        if (!val) {
            showToast('Please select a retail customer', 'error');
            return;
        }
        customer_id = parseInt(val);
    }

    // Collect items
    const items = [];
    document.querySelectorAll('.order-item').forEach(itemRow => {
        const product_id = parseInt(itemRow.querySelector('.item-product').value);
        const quantity = parseFloat(itemRow.querySelector('.item-quantity').value);
        const unit = itemRow.querySelector('.item-unit').value;
        const selling_price = parseFloat(itemRow.querySelector('.item-selling-price').value);
        const total = parseFloat(itemRow.querySelector('.item-total').value);
        
        if (!product_id || !Number.isFinite(quantity) || quantity <= 0 || !unit.trim() ||
            !Number.isFinite(selling_price) || selling_price <= 0 || !Number.isFinite(total)) {
            return;
        }
        items.push({ product_id, quantity, unit: unit.trim(), selling_price, discount: 0, tax: 0, total });
    });
    
    if (items.length === 0 || items.length !== document.querySelectorAll('.order-item').length) {
        showToast('Complete every order item with a product, positive quantity, unit, and price', 'error');
        return;
    }
    
    const orderData = {
        order_code: document.getElementById('orderCode').value,
        customer_type: customerType,
        restaurant_id: restaurant_id,
        customer_id: customer_id,
        order_date: document.getElementById('orderDate').value,
        delivery_date: document.getElementById('orderDeliveryDate').value || null,
        discount: parseFloat(document.getElementById('orderDiscount').value) || 0,
        tax: parseFloat(document.getElementById('orderTax').value) || 0,
        notes: document.getElementById('orderNotes').value,
        items: items
    };
    
    const submitButton = document.querySelector('#orderForm button[type="submit"]');
    submitButton.disabled = true;
    try {
        if (orderId) {
            // Update existing order
            await ordersAPI.update(parseInt(orderId), orderData);
            showToast('Order updated successfully', 'success');
        } else {
            // Create new order
            await ordersAPI.create(orderData);
            showToast(customerType === 'restaurant'
                ? 'Order placed successfully. Restaurant invoice generated; PDF bill is available in the order list.'
                : 'Order placed successfully. PDF bill is available in the order list.', 'success');
        }
        
        closeOrderModal();
        await loadOrders();
    } catch (error) {
        console.error('Error saving order:', error);
        showToast('Failed to save order: ' + (error.message || 'Server error'), 'error');
    } finally {
        submitButton.disabled = false;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initOrdersPage);
