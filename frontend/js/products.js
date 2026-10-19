/**
 * Products Page Functions for ESR Foods
 */

let allProducts = [];
let allCategories = [];

// Initialize products page
async function initProductsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load categories
        await loadCategories();
        
        // Load products
        await loadProducts();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Products page initialization error:', error);
        showToast('Failed to load products', 'error');
    }
}

// Load categories
async function loadCategories() {
    try {
        allCategories = await productsAPI.getCategories();
        
        // Populate category dropdowns
        const categorySelect = document.getElementById('productCategory');
        const categoryFilter = document.getElementById('categoryFilter');
        
        if (categorySelect) {
            categorySelect.innerHTML = '<option value="">Select Category</option>' +
                allCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        }
        
        if (categoryFilter) {
            categoryFilter.innerHTML = '<option value="">All Categories</option>' +
                allCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Load products
async function loadProducts() {
    try {
        const search = document.getElementById('searchInput').value;
        const categoryId = document.getElementById('categoryFilter').value;
        const seafoodType = document.getElementById('seafoodTypeFilter').value;
        const status = document.getElementById('statusFilter').value;
        
        const params = {};
        if (search) params.search = search;
        if (categoryId) params.category_id = categoryId;
        if (seafoodType) params.seafood_type = seafoodType;
        if (status) params.status = status === 'true';
        
        allProducts = await productsAPI.getAll(params);
        renderProductsTable();
    } catch (error) {
        console.error('Error loading products:', error);
        document.getElementById('productsTable').innerHTML = '<tr><td colspan="9" style="color: var(--danger-color);">Failed to load products</td></tr>';
    }
}

// Render products table
function renderProductsTable() {
    const tbody = document.getElementById('productsTable');
    
    if (!allProducts || allProducts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><div class="empty-state-icon">🐟</div><div class="empty-state-text">No products found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = allProducts.map(product => {
        const category = allCategories.find(c => c.id === product.category_id);
        const isLowStock = product.current_stock <= product.reorder_level;
        
        return `
            <tr>
                <td><strong>${product.product_code}</strong></td>
                <td>${product.name}</td>
                <td>${category ? category.name : '-'}</td>
                <td><span class="badge badge-info">${product.seafood_type}</span></td>
                <td style="color: ${isLowStock ? 'var(--danger-color)' : 'var(--success-color)'}; font-weight: 600;">
                    ${product.current_stock} ${product.unit}
                </td>
                <td>${formatCurrency(product.purchase_price)}</td>
                <td>${formatCurrency(product.selling_price)}</td>
                <td>
                    <span class="badge ${product.is_active ? 'badge-success' : 'badge-danger'}">
                        ${product.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewProduct(${product.id})">View</button>
                    <button class="btn btn-sm btn-secondary" onclick="editProduct(${product.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProduct(${product.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(loadProducts, 300));
    
    // Filter dropdowns
    document.getElementById('categoryFilter').addEventListener('change', loadProducts);
    document.getElementById('seafoodTypeFilter').addEventListener('change', loadProducts);
    document.getElementById('statusFilter').addEventListener('change', loadProducts);
    
    // Product form
    document.getElementById('productForm').addEventListener('submit', handleProductSubmit);

    // Category form
    const categoryForm = document.getElementById('categoryForm');
    if (categoryForm) {
        categoryForm.addEventListener('submit', handleCategorySubmit);
    }
}

// Category modal functions
function openCategoryModal() {
    const modal = document.getElementById('categoryModal');
    const form = document.getElementById('categoryForm');
    if (form) form.reset();
    if (modal) modal.classList.add('show');
}

function closeCategoryModal() {
    const modal = document.getElementById('categoryModal');
    if (modal) modal.classList.remove('show');
}

async function handleCategorySubmit(event) {
    event.preventDefault();
    const name = document.getElementById('categoryName').value.trim();
    const description = document.getElementById('categoryDescription').value.trim();

    if (!name) return;

    try {
        const newCat = await productsAPI.createCategory({ name, description });
        showToast('Category created successfully!', 'success');
        closeCategoryModal();
        await loadCategories();
        
        // Select the newly created category in the product dropdown
        const categorySelect = document.getElementById('productCategory');
        if (categorySelect && newCat && newCat.id) {
            categorySelect.value = newCat.id;
        }
    } catch (error) {
        console.error('Error creating category:', error);
        showToast('Failed to create category: ' + (error.message || 'Error'), 'error');
    }
}

// Open product modal
function openProductModal(product = null) {
    const modal = document.getElementById('productModal');
    const title = document.getElementById('productModalTitle');
    const form = document.getElementById('productForm');
    
    // Reset form
    form.reset();
    document.getElementById('productId').value = '';
    
    if (product) {
        title.textContent = 'Edit Product';
        
        // Populate form with product data
        document.getElementById('productId').value = product.id;
        document.getElementById('productCode').value = product.product_code;
        document.getElementById('productName').value = product.name;
        document.getElementById('productCategory').value = product.category_id || '';
        document.getElementById('productSeafoodType').value = product.seafood_type;
        document.getElementById('productVariety').value = product.variety || '';
        document.getElementById('productBrand').value = product.brand || '';
        document.getElementById('productGrade').value = product.grade || '';
        document.getElementById('productSize').value = product.size || '';
        document.getElementById('productUnit').value = product.unit;
        document.getElementById('productWeightPerPacket').value = product.weight_per_packet || '';
        document.getElementById('productPackagingType').value = product.packaging_type || '';
        document.getElementById('productIsFrozen').value = product.is_frozen.toString();
        document.getElementById('productPurchasePrice').value = product.purchase_price;
        document.getElementById('productSellingPrice').value = product.selling_price;
        document.getElementById('productWholesalePrice').value = product.wholesale_price || '';
        document.getElementById('productRetailPrice').value = product.retail_price || '';
        document.getElementById('productMinimumStock').value = product.minimum_stock;
        document.getElementById('productMaximumStock').value = product.maximum_stock || '';
        document.getElementById('productReorderLevel').value = product.reorder_level;
        document.getElementById('productStorageLocation').value = product.storage_location || '';
        document.getElementById('productDescription').value = product.description || '';
    } else {
        title.textContent = 'Add Product';
    }
    
    modal.classList.add('show');
}

// Close product modal
function closeProductModal() {
    document.getElementById('productModal').classList.remove('show');
}

// View product
async function viewProduct(id) {
    try {
        const product = await productsAPI.getById(id);
        if (product) {
            openProductModal(product);
        }
    } catch (error) {
        console.error('Error loading product:', error);
        showToast('Failed to load product details', 'error');
    }
}

// Edit product
async function editProduct(id) {
    try {
        const product = await productsAPI.getById(id);
        if (product) {
            openProductModal(product);
        }
    } catch (error) {
        console.error('Error loading product:', error);
        showToast('Failed to load product details', 'error');
    }
}

// Handle product form submission
async function handleProductSubmit(event) {
    event.preventDefault();
    
    const productId = document.getElementById('productId').value;
    
    const productData = {
        product_code: document.getElementById('productCode').value,
        name: document.getElementById('productName').value,
        category_id: document.getElementById('productCategory').value ? parseInt(document.getElementById('productCategory').value) : null,
        seafood_type: document.getElementById('productSeafoodType').value,
        variety: document.getElementById('productVariety').value,
        brand: document.getElementById('productBrand').value,
        grade: document.getElementById('productGrade').value,
        size: document.getElementById('productSize').value,
        unit: document.getElementById('productUnit').value,
        weight_per_packet: document.getElementById('productWeightPerPacket').value ? parseFloat(document.getElementById('productWeightPerPacket').value) : null,
        packaging_type: document.getElementById('productPackagingType').value,
        is_frozen: document.getElementById('productIsFrozen').value === 'true',
        purchase_price: parseFloat(document.getElementById('productPurchasePrice').value),
        selling_price: parseFloat(document.getElementById('productSellingPrice').value),
        wholesale_price: document.getElementById('productWholesalePrice').value ? parseFloat(document.getElementById('productWholesalePrice').value) : null,
        retail_price: document.getElementById('productRetailPrice').value ? parseFloat(document.getElementById('productRetailPrice').value) : null,
        minimum_stock: parseFloat(document.getElementById('productMinimumStock').value),
        maximum_stock: document.getElementById('productMaximumStock').value ? parseFloat(document.getElementById('productMaximumStock').value) : null,
        reorder_level: parseFloat(document.getElementById('productReorderLevel').value),
        storage_location: document.getElementById('productStorageLocation').value,
        description: document.getElementById('productDescription').value
    };
    
    try {
        if (productId) {
            // Update existing product
            await productsAPI.update(parseInt(productId), productData);
            showToast('Product updated successfully', 'success');
        } else {
            // Create new product
            await productsAPI.create(productData);
            showToast('Product created successfully', 'success');
        }
        
        closeProductModal();
        await loadProducts();
    } catch (error) {
        console.error('Error saving product:', error);
        showToast('Failed to save product: ' + (error.message || ''), 'error');
    }
}

// Delete product
async function deleteProduct(id) {
    if (!confirm('⚠️ Are you sure you want to DELETE this product? This action cannot be undone.')) {
        return;
    }

    try {
        await productsAPI.delete(id);
        showToast('Product deleted successfully', 'success');
        await loadProducts();
    } catch (error) {
        console.error('Error deleting product:', error);
        showToast('Failed to delete product: ' + (error.message || ''), 'error');
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
document.addEventListener('DOMContentLoaded', initProductsPage);
