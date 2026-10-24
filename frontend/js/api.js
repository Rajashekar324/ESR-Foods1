/**
 * API Utility Functions for ESR Foods
 */

const API_BASE_URL = '/api';

// Convert HTML date-input values only; preserve empty/null and existing datetimes.
function toIsoDateTime(value) {
    if (!value || typeof value !== 'string') return value;
    return /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value;
}

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('authToken');
}

// Set auth token
function setAuthToken(token) {
    localStorage.setItem('authToken', token);
}

// Remove auth token
function removeAuthToken() {
    localStorage.removeItem('authToken');
}

// Get current user
function getCurrentUser() {
    const userStr = localStorage.getItem('currentUser');
    return userStr ? JSON.parse(userStr) : null;
}

// Set current user
function setCurrentUser(user) {
    localStorage.setItem('currentUser', JSON.stringify(user));
}

// Remove current user
function removeCurrentUser() {
    localStorage.removeItem('currentUser');
}

// Generic API request function
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    const config = {
        ...options,
        headers,
        credentials: 'same-origin'
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        
        if (response.status === 401 || response.status === 303) {
            // Unauthorized - redirect to login
            removeAuthToken();
            removeCurrentUser();
            localStorage.removeItem('sessionExpiresAt');
            if (!window.location.pathname.endsWith('login.html')) {
                window.location.href = 'login.html';
            }
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.detail || 'Please sign in again.');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Authentication API
const authAPI = {
    login: async (username, password) => {
        return apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },
    
    register: async (userData) => {
        return apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    },
    
    getRoles: async () => {
        return apiRequest('/auth/roles', {
            method: 'GET'
        });
    },
    
    logout: async () => {
        return apiRequest('/auth/logout', {
            method: 'POST'
        });
    },
    
    getCurrentUser: async () => {
        return apiRequest('/auth/me', {
            method: 'GET'
        });
    }
};

// Products API
const productsAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/products/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/products/${id}`);
    },

    create: async (data) => {
        return apiRequest('/products/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/products/${id}`, {
            method: 'DELETE'
        });
    },

    getCategories: async () => {
        return apiRequest('/products/categories/');
    },

    createCategory: async (data) => {
        return apiRequest('/products/categories/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Inventory API
const inventoryAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/inventory/?${queryString}`);
    },

    getMovements: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/inventory/movements?${queryString}`);
    },

    createAdjustment: async (data) => {
        return apiRequest('/inventory/adjustment', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    getBatches: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/inventory/batches?${queryString}`);
    },

    createBatch: async (data) => {
        return apiRequest('/inventory/batches', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    getSummary: async () => {
        return apiRequest('/inventory/summary');
    }
};

// Vendors API
const vendorsAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/vendors/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/vendors/${id}`);
    },

    create: async (data) => {
        return apiRequest('/vendors/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/vendors/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/vendors/${id}`, {
            method: 'DELETE'
        });
    },

    getPurchases: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/vendors/${id}/purchases?${queryString}`);
    },

    getPayments: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/vendors/${id}/payments?${queryString}`);
    },

    getSummary: async (id) => {
        return apiRequest(`/vendors/${id}/summary`);
    }
};

// Purchases API
const purchasesAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/purchases/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/purchases/${id}`);
    },

    create: async (data) => {
        return apiRequest('/purchases/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/purchases/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/purchases/${id}`, {
            method: 'DELETE'
        });
    },

    receive: async (id) => {
        return apiRequest(`/purchases/${id}/receive`, {
            method: 'POST'
        });
    }
};

// Restaurants API
const restaurantsAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/restaurants/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/restaurants/${id}`);
    },

    create: async (data) => {
        return apiRequest('/restaurants/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/restaurants/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/restaurants/${id}`, {
            method: 'DELETE'
        });
    },

    getOrders: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/restaurants/${id}/orders?${queryString}`);
    },

    getInvoices: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/restaurants/${id}/invoices?${queryString}`);
    },

    getPayments: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/restaurants/${id}/payments?${queryString}`);
    },

    getSummary: async (id) => {
        return apiRequest(`/restaurants/${id}/summary`);
    },

    createNote: async (id, data) => {
        return apiRequest(`/restaurants/${id}/notes`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    getNotes: async (id) => {
        return apiRequest(`/restaurants/${id}/notes`);
    },

    getStatement: async (id, startDate, endDate) => {
        return apiRequest(`/restaurants/${id}/statement?start_date=${startDate}&end_date=${endDate}`);
    }
};

// Customers API
const customersAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/customers/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/customers/${id}`);
    },

    create: async (data) => {
        return apiRequest('/customers/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/customers/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/customers/${id}`, {
            method: 'DELETE'
        });
    },

    getOrders: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/customers/${id}/orders?${queryString}`);
    },

    getPayments: async (id, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/customers/${id}/payments?${queryString}`);
    }
};

// Orders API
const ordersAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/orders/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/orders/${id}`);
    },

    create: async (data) => {
        return apiRequest('/orders/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/orders/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/orders/${id}`, {
            method: 'DELETE'
        });
    },

    complete: async (id) => {
        return apiRequest(`/orders/${id}/complete`, {
            method: 'POST'
        });
    },

    cancel: async (id) => {
        return apiRequest(`/orders/${id}/cancel`, {
            method: 'POST'
        });
    }
};

// Invoices API
const invoicesAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/invoices/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/invoices/${id}`);
    },

    create: async (data) => {
        return apiRequest('/invoices/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/invoices/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/invoices/${id}`, {
            method: 'DELETE'
        });
    },

    finalize: async (id) => {
        return apiRequest(`/invoices/${id}/finalize`, {
            method: 'POST'
        });
    },

    getPayments: async (id) => {
        return apiRequest(`/invoices/${id}/payments`);
    }
};

// Payments API
const paymentsAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/payments/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/payments/${id}`);
    },

    create: async (data) => {
        return apiRequest('/payments/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/payments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    updateStatus: async (id, status) => {
        return apiRequest(`/payments/${id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    },

    delete: async (id) => {
        return apiRequest(`/payments/${id}`, {
            method: 'DELETE'
        });
    },

    getSummary: async (startDate, endDate) => {
        return apiRequest(`/payments/summary?start_date=${startDate}&end_date=${endDate}`);
    },

    getVendorLedger: async (vendorId, params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/payments/vendor/${vendorId}/ledger?${queryString}`);
    }
};

// Expenses API
const expensesAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/expenses/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/expenses/${id}`);
    },

    create: async (data) => {
        return apiRequest('/expenses/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id, data) => {
        return apiRequest(`/expenses/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: async (id) => {
        return apiRequest(`/expenses/${id}`, {
            method: 'DELETE'
        });
    },

    getSummary: async (startDate, endDate) => {
        return apiRequest(`/expenses/summary?start_date=${startDate}&end_date=${endDate}`);
    }
};

// Reports API
const reportsAPI = {
    getSalesReport: async (startDate, endDate, restaurantId = null) => {
        let url = `/reports/sales?start_date=${toIsoDateTime(startDate)}&end_date=${toIsoDateTime(endDate)}`;
        if (restaurantId) url += `&restaurant_id=${restaurantId}`;
        return apiRequest(url);
    },

    getPurchasesReport: async (startDate, endDate, vendorId = null) => {
        let url = `/reports/purchases?start_date=${toIsoDateTime(startDate)}&end_date=${toIsoDateTime(endDate)}`;
        if (vendorId) url += `&vendor_id=${vendorId}`;
        return apiRequest(url);
    },

    getInventoryReport: async () => {
        return apiRequest('/reports/inventory');
    },

    getRestaurantsReport: async () => {
        return apiRequest('/reports/restaurants');
    },

    get15DaySummary: async (startDate, endDate) => {
        return apiRequest(`/reports/restaurants/15-day-summary?start_date=${toIsoDateTime(startDate)}&end_date=${toIsoDateTime(endDate)}`);
    },

    getProfitReport: async (startDate, endDate) => {
        return apiRequest(`/reports/profit?start_date=${toIsoDateTime(startDate)}&end_date=${toIsoDateTime(endDate)}`);
    }
};

// Dashboard API
const dashboardAPI = {
    getSummary: async () => {
        return apiRequest('/dashboard/summary');
    },

    getCharts: async () => {
        return apiRequest('/dashboard/charts');
    },

    get15DaySummary: async () => {
        return apiRequest('/dashboard/15-day-summary');
    }
};

// Users API
const usersAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/users/?${queryString}`);
    },

    getById: async (id) => {
        return apiRequest(`/users/${id}`);
    },

    create: async (data) => {
        return apiRequest('/users/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    approve: async (id, roleId) => {
        return apiRequest(`/users/${id}/approve`, {
            method: 'PUT',
            body: roleId ? JSON.stringify({ role_id: roleId }) : undefined
        });
    },

    updateRole: async (id, roleId) => {
        return apiRequest(`/users/${id}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role_id: roleId })
        });
    },

    reject: async (id) => {
        return apiRequest(`/users/${id}/reject`, { method: 'PUT' });
    },

    deactivate: async (id) => {
        return apiRequest(`/users/${id}/deactivate`, {
            method: 'PUT'
        });
    },

    activate: async (id) => {
        return apiRequest(`/users/${id}/activate`, {
            method: 'PUT'
        });
    }
};

// Notifications API
const notificationsAPI = {
    getAll: async (params = {}) => {
        const queryString = new URLSearchParams(params).toString();
        return apiRequest(`/notifications/?${queryString}`);
    },

    create: async (data) => {
        return apiRequest('/notifications/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    markRead: async (id) => {
        return apiRequest(`/notifications/${id}/read`, {
            method: 'PUT'
        });
    },

    markAllRead: async () => {
        return apiRequest('/notifications/read-all', {
            method: 'PUT'
        });
    },

    getUnreadCount: async () => {
        return apiRequest('/notifications/unread-count');
    }
};

// Settings API
const settingsAPI = {
    getAll: async () => {
        return apiRequest('/settings/');
    },

    get: async (key) => {
        return apiRequest(`/settings/${key}`);
    },

    create: async (data) => {
        return apiRequest('/settings/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (key, value) => {
        return apiRequest(`/settings/${key}?value=${value}`, {
            method: 'PUT'
        });
    },

    resetDatabase: async () => {
        return apiRequest('/settings/reset-database', {
            method: 'POST'
        });
    }
};

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Explicitly attach API objects to window
window.purchasesAPI = purchasesAPI;
window.paymentsAPI = paymentsAPI;
window.restaurantsAPI = restaurantsAPI;
window.vendorsAPI = vendorsAPI;
window.productsAPI = productsAPI;
window.inventoryAPI = inventoryAPI;
window.customersAPI = customersAPI;
window.ordersAPI = ordersAPI;
window.invoicesAPI = invoicesAPI;
window.expensesAPI = expensesAPI;
window.reportsAPI = reportsAPI;
window.authAPI = authAPI;

