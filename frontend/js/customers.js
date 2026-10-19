/**
 * Customers Page Functions for ESR Foods
 */

let allCustomers = [];

// Initialize customers page
async function initCustomersPage() {
    if (!requireAuth()) return;
    
    try {
        // Load customers
        await loadCustomers();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Customers page initialization error:', error);
        showToast('Failed to load customers', 'error');
    }
}

// Load customers
async function loadCustomers() {
    try {
        const search = document.getElementById('searchInput').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (search) params.search = search;
        if (status) params.status = status === 'true';
        
        allCustomers = await customersAPI.getAll(params);
        renderCustomersTable();
    } catch (error) {
        console.error('Error loading customers:', error);
        document.getElementById('customersTable').innerHTML = '<tr><td colspan="8" style="color: var(--danger-color);">Failed to load customers</td></tr>';
    }
}

// Render customers table
function renderCustomersTable() {
    const tbody = document.getElementById('customersTable');
    
    if (!allCustomers || allCustomers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-state-icon">👥</div><div class="empty-state-text">No customers found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = allCustomers.map(customer => `
        <tr>
            <td><strong>${customer.customer_code}</strong></td>
            <td>${customer.name}</td>
            <td>${customer.phone || '-'}</td>
            <td>${customer.email || '-'}</td>
            <td>${formatCurrency(customer.total_purchases)}</td>
            <td>${customer.last_purchase_date ? formatDate(customer.last_purchase_date) : '-'}</td>
            <td>
                <span class="badge ${customer.status ? 'badge-success' : 'badge-danger'}">
                    ${customer.status ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewCustomer(${customer.id})">View</button>
                <button class="btn btn-sm btn-secondary" onclick="editCustomer(${customer.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${customer.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(loadCustomers, 300));
    
    // Status filter
    document.getElementById('statusFilter').addEventListener('change', loadCustomers);
    
    // Customer form
    document.getElementById('customerForm').addEventListener('submit', handleCustomerSubmit);
}

// Open customer modal
function openCustomerModal(customer = null) {
    const modal = document.getElementById('customerModal');
    const title = document.getElementById('customerModalTitle');
    const form = document.getElementById('customerForm');
    
    // Reset form
    form.reset();
    document.getElementById('customerId').value = '';
    
    if (customer) {
        title.textContent = 'Edit Customer';
        
        // Populate form with customer data
        document.getElementById('customerId').value = customer.id;
        document.getElementById('customerCode').value = customer.customer_code;
        document.getElementById('customerName').value = customer.name;
        document.getElementById('customerPhone').value = customer.phone || '';
        document.getElementById('customerEmail').value = customer.email || '';
        document.getElementById('customerAddress').value = customer.address || '';
    } else {
        title.textContent = 'Add Customer';
    }
    
    modal.classList.add('show');
}

// Close customer modal
function closeCustomerModal() {
    document.getElementById('customerModal').classList.remove('show');
}

// View customer
async function viewCustomer(id) {
    try {
        const customer = await customersAPI.getById(id);
        if (customer) {
            openCustomerModal(customer);
        }
    } catch (error) {
        console.error('Error loading customer:', error);
        showToast('Failed to load customer details', 'error');
    }
}

// Edit customer
async function editCustomer(id) {
    try {
        const customer = await customersAPI.getById(id);
        if (customer) {
            openCustomerModal(customer);
        }
    } catch (error) {
        console.error('Error loading customer:', error);
        showToast('Failed to load customer details', 'error');
    }
}

// Handle customer form submission
async function handleCustomerSubmit(event) {
    event.preventDefault();
    
    const customerId = document.getElementById('customerId').value;
    
    const customerData = {
        customer_code: document.getElementById('customerCode').value,
        name: document.getElementById('customerName').value,
        phone: document.getElementById('customerPhone').value,
        email: document.getElementById('customerEmail').value,
        address: document.getElementById('customerAddress').value
    };
    
    try {
        if (customerId) {
            // Update existing customer
            await customersAPI.update(parseInt(customerId), customerData);
            showToast('Customer updated successfully', 'success');
        } else {
            // Create new customer
            await customersAPI.create(customerData);
            showToast('Customer created successfully', 'success');
        }
        
        closeCustomerModal();
        await loadCustomers();
    } catch (error) {
        console.error('Error saving customer:', error);
        showToast('Failed to save customer: ' + (error.message || ''), 'error');
    }
}

// Delete customer
async function deleteCustomer(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this customer? This action cannot be undone.')) {
        return;
    }

    try {
        await customersAPI.delete(id);
        showToast('Customer deleted successfully!', 'success');
        await loadCustomers();
    } catch (error) {
        console.error('Error deleting customer:', error);
        showToast('Failed to delete customer: ' + (error.message || ''), 'error');
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
document.addEventListener('DOMContentLoaded', initCustomersPage);
