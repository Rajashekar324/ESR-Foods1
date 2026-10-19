/**
 * Expenses Page Functions for ESR Foods
 */

let allExpenses = [];

// Initialize expenses page
async function initExpensesPage() {
    if (!requireAuth()) return;
    
    try {
        // Load expenses
        await loadExpenses();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Expenses page initialization error:', error);
        showToast('Failed to load expenses', 'error');
    }
}

// Load expenses
async function loadExpenses() {
    try {
        const category = document.getElementById('categoryFilter').value;
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const params = {};
        if (category) params.category = category;
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        
        allExpenses = await expensesAPI.getAll(params);
        renderExpensesTable();
    } catch (error) {
        console.error('Error loading expenses:', error);
        document.getElementById('expensesTable').innerHTML = '<tr><td colspan="7" style="color: var(--danger-color);">Failed to load expenses</td></tr>';
    }
}

// Render expenses table
function renderExpensesTable() {
    const tbody = document.getElementById('expensesTable');
    
    if (!allExpenses || allExpenses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="empty-state-icon">💸</div><div class="empty-state-text">No expenses found</div></td></tr>';
        return;
    }
    
    tbody.innerHTML = allExpenses.map(expense => `
        <tr>
            <td><strong>${expense.expense_code}</strong></td>
            <td><span class="badge badge-info">${expense.category}</span></td>
            <td>${expense.description}</td>
            <td>${formatDate(expense.date)}</td>
            <td style="font-weight: 600; color: var(--danger-color);">${formatCurrency(expense.amount)}</td>
            <td><span class="badge badge-info">${expense.payment_method.replace(/_/g, ' ')}</span></td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewExpense(${expense.id})">View</button>
                <button class="btn btn-sm btn-secondary" onclick="editExpense(${expense.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteExpense(${expense.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Filters
    document.getElementById('categoryFilter').addEventListener('change', loadExpenses);
    document.getElementById('startDate').addEventListener('change', loadExpenses);
    document.getElementById('endDate').addEventListener('change', loadExpenses);
    
    // Expense form
    document.getElementById('expenseForm').addEventListener('submit', handleExpenseSubmit);
}

// Open expense modal
function openExpenseModal(expense = null) {
    const modal = document.getElementById('expenseModal');
    const title = document.getElementById('expenseModalTitle');
    const form = document.getElementById('expenseForm');
    
    // Reset form
    form.reset();
    document.getElementById('expenseId').value = '';
    
    // Set default date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('expenseDate').value = today;
    
    if (expense) {
        title.textContent = 'Edit Expense';
        
        // Populate form with expense data
        document.getElementById('expenseId').value = expense.id;
        document.getElementById('expenseCode').value = expense.expense_code;
        document.getElementById('expenseCategory').value = expense.category;
        document.getElementById('expenseDescription').value = expense.description;
        document.getElementById('expenseDate').value = expense.date.split('T')[0];
        document.getElementById('expenseAmount').value = expense.amount;
        document.getElementById('expensePaymentMethod').value = expense.payment_method;
        document.getElementById('expenseReference').value = expense.reference_number || '';
        document.getElementById('expenseNotes').value = expense.notes || '';
    } else {
        title.textContent = 'Add Expense';
    }
    
    modal.classList.add('show');
}

// Close expense modal
function closeExpenseModal() {
    document.getElementById('expenseModal').classList.remove('show');
}

// View expense
async function viewExpense(id) {
    try {
        const expense = await expensesAPI.getById(id);
        if (expense) {
            openExpenseModal(expense);
        }
    } catch (error) {
        console.error('Error loading expense:', error);
        showToast('Failed to load expense details', 'error');
    }
}

// Edit expense
async function editExpense(id) {
    try {
        const expense = await expensesAPI.getById(id);
        if (expense) {
            openExpenseModal(expense);
        }
    } catch (error) {
        console.error('Error loading expense:', error);
        showToast('Failed to load expense details', 'error');
    }
}

// Delete expense
async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) {
        return;
    }
    
    try {
        await expensesAPI.delete(id);
        showToast('Expense deleted successfully', 'success');
        await loadExpenses();
    } catch (error) {
        console.error('Error deleting expense:', error);
        showToast('Failed to delete expense', 'error');
    }
}

// Handle expense form submission
async function handleExpenseSubmit(event) {
    event.preventDefault();
    
    const expenseId = document.getElementById('expenseId').value;
    
    const expenseData = {
        expense_code: document.getElementById('expenseCode').value,
        category: document.getElementById('expenseCategory').value,
        description: document.getElementById('expenseDescription').value,
        date: document.getElementById('expenseDate').value,
        amount: parseFloat(document.getElementById('expenseAmount').value),
        payment_method: document.getElementById('expensePaymentMethod').value,
        reference_number: document.getElementById('expenseReference').value,
        notes: document.getElementById('expenseNotes').value
    };
    
    try {
        if (expenseId) {
            // Update existing expense
            await expensesAPI.update(parseInt(expenseId), expenseData);
            showToast('Expense updated successfully', 'success');
        } else {
            // Create new expense
            await expensesAPI.create(expenseData);
            showToast('Expense created successfully', 'success');
        }
        
        closeExpenseModal();
        await loadExpenses();
    } catch (error) {
        console.error('Error saving expense:', error);
        showToast('Failed to save expense', 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initExpensesPage);
