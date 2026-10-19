/**
 * Users Page Functions for ESR Foods
 */

let allUsers = [];
let availableRoles = [];

// Initialize users page
async function initUsersPage() {
    if (!requireAuth()) return;
    
    try {
        const currentUser = await authAPI.getCurrentUser();
        setCurrentUser(currentUser);
        if (currentUser?.role?.name !== 'admin') {
            window.location.replace('dashboard.html');
            return;
        }
        availableRoles = await authAPI.getRoles();
        populateRoleSelects();
        // Load users
        await loadUsers();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Users page initialization error:', error);
        showToast('Failed to load users', 'error');
    }
}

// Load users
async function loadUsers() {
    try {
        const roleId = document.getElementById('roleFilter').value;
        const approvalStatus = document.getElementById('statusFilter').value;
        
        const params = {};
        if (roleId) params.role_id = parseInt(roleId);
        if (approvalStatus) params.approval_status = approvalStatus;
        
        allUsers = await usersAPI.getAll(params);
        renderUsersTable();
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('usersTable').innerHTML = '<tr><td colspan="7" style="color: var(--danger-color);">Failed to load users</td></tr>';
    }
}

// Render users table
function renderUsersTable() {
    const tbody = document.getElementById('usersTable');
    
    if (!allUsers || allUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="empty-state-icon">👤</div><div class="empty-state-text">No users found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = allUsers.map(user => {
        const state = user.approval_status || (user.is_active ? 'approved' : 'disabled');
        const stateClass = { pending: 'badge-warning', approved: 'badge-success', rejected: 'badge-danger', disabled: 'badge-danger' }[state] || 'badge-info';
        let actions = '';
        if (state === 'pending' || state === 'rejected') {
            actions = `<button class="btn btn-sm btn-success" onclick="approveUser(${user.id})">Approve</button> `;
            if (state === 'pending') actions += `<button class="btn btn-sm btn-danger" onclick="rejectUser(${user.id})">Reject</button>`;
        } else if (state === 'approved') {
            actions = `<button class="btn btn-sm btn-danger" onclick="deactivateUser(${user.id})">Disable</button>`;
        } else {
            actions = `<button class="btn btn-sm btn-success" onclick="activateUser(${user.id})">Enable</button>`;
        }
        return `<tr>
            <td><strong>${escapeHtml(user.full_name || user.username)}</strong><br><small>${escapeHtml(user.username)}</small></td>
            <td>${escapeHtml(user.email)}</td>
            <td><span class="badge badge-info">${escapeHtml(user.role?.name || 'Unknown')}</span></td>
            <td>${formatDate(user.created_at)}</td>
            <td><span class="badge ${stateClass}">${escapeHtml(state.charAt(0).toUpperCase() + state.slice(1))}</span></td>
            <td>${formatDate(user.last_login)}</td>
            <td>${actions}</td>
        </tr>`;
    }).join('');
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function formatDate(value) {
    if (!value) return '<span class="text-muted">Never</span>';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : escapeHtml(date.toLocaleString());
}

function populateRoleSelects() {
    const filter = document.getElementById('roleFilter');
    const select = document.getElementById('userRole');
    availableRoles.forEach(role => {
        const label = role.name.charAt(0).toUpperCase() + role.name.slice(1);
        filter.add(new Option(label, role.id));
        select.add(new Option(label, role.id));
    });
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('roleFilter').addEventListener('change', loadUsers);
    document.getElementById('statusFilter').addEventListener('change', loadUsers);
    
    // User form
    document.getElementById('userForm').addEventListener('submit', handleUserSubmit);
}

// Open user modal
function openUserModal() {
    const modal = document.getElementById('userModal');
    const title = document.getElementById('userModalTitle');
    const form = document.getElementById('userForm');
    
    // Reset form
    form.reset();
    
    title.textContent = 'Add User';
    
    modal.classList.add('show');
}

// Close user modal
function closeUserModal() {
    document.getElementById('userModal').classList.remove('show');
}

// Deactivate user
async function deactivateUser(id) {
    if (!confirm('Are you sure you want to deactivate this user?')) {
        return;
    }
    
    try {
        await usersAPI.deactivate(id);
        showToast('User deactivated successfully', 'success');
        await loadUsers();
    } catch (error) {
        console.error('Error deactivating user:', error);
        showToast(error.message || 'Failed to disable user', 'error');
    }
}

// Activate user
async function activateUser(id) {
    try {
        await usersAPI.activate(id);
        showToast('User access enabled', 'success');
        await loadUsers();
    } catch (error) {
        console.error('Error activating user:', error);
        showToast(error.message || 'Failed to enable user', 'error');
    }
}

async function approveUser(id) {
    try {
        await usersAPI.approve(id);
        showToast('User approved. Access is now enabled.', 'success');
        await loadUsers();
    } catch (error) {
        showToast(error.message || 'Failed to approve user', 'error');
    }
}

async function rejectUser(id) {
    if (!confirm('Reject this registration? The user will not be able to access the application.')) return;
    try {
        await usersAPI.reject(id);
        showToast('Registration rejected', 'success');
        await loadUsers();
    } catch (error) {
        showToast(error.message || 'Failed to reject user', 'error');
    }
}

// Handle user form submission
async function handleUserSubmit(event) {
    event.preventDefault();
    
    const userData = {
        username: document.getElementById('userUsername').value,
        email: document.getElementById('userEmail').value,
        password: document.getElementById('userPassword').value,
        full_name: document.getElementById('userFullName').value,
        phone: document.getElementById('userPhone').value,
        role_id: parseInt(document.getElementById('userRole').value)
    };

    if (userData.password.length < 12 || !/[a-z]/.test(userData.password) || !/[A-Z]/.test(userData.password) || !/[0-9]/.test(userData.password)) {
        showToast('Use 12+ characters with uppercase, lowercase, and a number.', 'error');
        return;
    }
    
    try {
        await usersAPI.create(userData);
        showToast('User created successfully', 'success');
        closeUserModal();
        await loadUsers();
    } catch (error) {
        console.error('Error creating user:', error);
        showToast(error.message || 'Failed to create user', 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initUsersPage);
