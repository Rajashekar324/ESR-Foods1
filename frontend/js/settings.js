/**
 * Settings Page Functions for ESR Foods
 */

let allSettings = {};

// Initialize settings page
async function initSettingsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load all settings
        await loadAllSettings();
        
    } catch (error) {
        console.error('Settings page initialization error:', error);
        showToast('Failed to load settings', 'error');
    }
}

// Load all settings
async function loadAllSettings() {
    try {
        const settings = await settingsAPI.getAll();
        
        // Convert to key-value object
        allSettings = {};
        settings.forEach(setting => {
            allSettings[setting.key] = setting.value;
        });
        
        // Populate form fields
        document.getElementById('settingCompanyName').value = allSettings['company_name'] || '';
        document.getElementById('settingCompanyAddress').value = allSettings['company_address'] || '';
        document.getElementById('settingCompanyPhone').value = allSettings['company_phone'] || '';
        document.getElementById('settingCompanyEmail').value = allSettings['company_email'] || '';
        document.getElementById('settingGstNumber').value = allSettings['gst_number'] || '';
        document.getElementById('settingInvoicePrefix').value = allSettings['invoice_prefix'] || '';
        document.getElementById('settingBillingCycle').value = allSettings['billing_cycle'] || '15';
        document.getElementById('settingTaxRate').value = allSettings['tax_rate'] || '18';
        document.getElementById('settingLowStockThreshold').value = allSettings['low_stock_threshold'] || '20';
        document.getElementById('settingExpiryWarningDays').value = allSettings['expiry_warning_days'] || '7';
        document.getElementById('settingCurrency').value = allSettings['currency'] || 'INR';
        
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Save company settings
async function saveCompanySettings() {
    try {
        await settingsAPI.update('company_name', document.getElementById('settingCompanyName').value);
        await settingsAPI.update('company_address', document.getElementById('settingCompanyAddress').value);
        await settingsAPI.update('company_phone', document.getElementById('settingCompanyPhone').value);
        await settingsAPI.update('company_email', document.getElementById('settingCompanyEmail').value);
        await settingsAPI.update('gst_number', document.getElementById('settingGstNumber').value);
        
        showToast('Company settings saved successfully', 'success');
    } catch (error) {
        console.error('Error saving company settings:', error);
        showToast('Failed to save company settings', 'error');
    }
}

// Save invoice settings
async function saveInvoiceSettings() {
    try {
        await settingsAPI.update('invoice_prefix', document.getElementById('settingInvoicePrefix').value);
        await settingsAPI.update('billing_cycle', document.getElementById('settingBillingCycle').value);
        await settingsAPI.update('tax_rate', document.getElementById('settingTaxRate').value);
        
        showToast('Invoice settings saved successfully', 'success');
    } catch (error) {
        console.error('Error saving invoice settings:', error);
        showToast('Failed to save invoice settings', 'error');
    }
}

// Save inventory settings
async function saveInventorySettings() {
    try {
        await settingsAPI.update('low_stock_threshold', document.getElementById('settingLowStockThreshold').value);
        await settingsAPI.update('expiry_warning_days', document.getElementById('settingExpiryWarningDays').value);
        
        showToast('Inventory settings saved successfully', 'success');
    } catch (error) {
        console.error('Error saving inventory settings:', error);
        showToast('Failed to save inventory settings', 'error');
    }
}

// Save system settings
async function saveSystemSettings() {
    try {
        await settingsAPI.update('currency', document.getElementById('settingCurrency').value);
        
        showToast('System settings saved successfully', 'success');
    } catch (error) {
        console.error('Error saving system settings:', error);
        showToast('Failed to save system settings', 'error');
    }
}

// Clear all system data
async function clearAllData() {
    if (!confirm('⚠️ Are you sure you want to CLEAR ALL SYSTEM DATA?\n\nThis will remove all products, orders, purchases, vendors, restaurants, customers, and payments. Default admin user and categories will be reseeded.')) {
        return;
    }
    
    try {
        const result = await settingsAPI.resetDatabase();
        showToast(result.message || 'All system data cleared successfully!', 'success');
    } catch (error) {
        console.error('Error clearing system data:', error);
        showToast('Failed to clear system data: ' + (error.message || 'Server error'), 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initSettingsPage);
