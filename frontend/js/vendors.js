/**
 * Vendors Page Functions for ESR Foods
 */

let allVendors = [];

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
            <td><strong>${vendor.vendor_code}</strong></td>
            <td>${vendor.name}</td>
            <td>${vendor.company_name || '-'}</td>
            <td>${vendor.contact_person || '-'}</td>
            <td>${vendor.phone || '-'}</td>
            <td>${vendor.email || '-'}</td>
            <td>
                <span class="badge ${vendor.status ? 'badge-success' : 'badge-danger'}">
                    ${vendor.status ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewVendor(${vendor.id})">View</button>
                <button class="btn btn-sm btn-secondary" onclick="editVendor(${vendor.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteVendor(${vendor.id})">Delete</button>
            </td>
        </tr>
    `).join('');
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
        notes: document.getElementById('vendorNotes').value
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
