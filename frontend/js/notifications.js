/**
 * Notifications Page Functions for ESR Foods
 */

let allNotifications = [];

// Initialize notifications page
async function initNotificationsPage() {
    if (!requireAuth()) return;
    
    try {
        // Load unread count
        await loadUnreadCount();
        
        // Load notifications
        await loadNotifications();
        
        // Setup event listeners
        setupEventListeners();
        
    } catch (error) {
        console.error('Notifications page initialization error:', error);
        showToast('Failed to load notifications', 'error');
    }
}

// Load unread count
async function loadUnreadCount() {
    try {
        const count = await notificationsAPI.getUnreadCount();
        document.getElementById('unreadCount').textContent = `${count.unread_count} unread`;
    } catch (error) {
        console.error('Error loading unread count:', error);
    }
}

// Load notifications
async function loadNotifications() {
    try {
        const unreadOnly = document.getElementById('unreadOnly').checked;
        
        const params = {};
        if (unreadOnly) params.unread_only = true;
        
        allNotifications = await notificationsAPI.getAll(params);
        renderNotificationsList();
    } catch (error) {
        console.error('Error loading notifications:', error);
        document.getElementById('notificationsList').innerHTML = '<p style="color: var(--danger-color);">Failed to load notifications</p>';
    }
}

// Render notifications list
function renderNotificationsList() {
    const container = document.getElementById('notificationsList');
    
    if (!allNotifications || allNotifications.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔔</div><div class="empty-state-text">No notifications found</div></div>';
        return;
    }
    
    container.innerHTML = allNotifications.map(notification => `
        <div style="padding: 16px; border-bottom: 1px solid #f0f0f0; ${!notification.is_read ? 'background: #f8f9fa;' : ''}">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                <h4 style="margin: 0; font-weight: 600; color: var(--primary-color);">${notification.title}</h4>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${!notification.is_read ? '<span class="badge badge-warning">Unread</span>' : ''}
                    <small style="color: var(--text-light);">${formatDateTime(notification.created_at)}</small>
                </div>
            </div>
            <p style="margin: 0; color: var(--text-secondary);">${notification.message}</p>
            <div style="margin-top: 12px;">
                ${!notification.is_read ? `<button class="btn btn-sm btn-outline" onclick="markAsRead(${notification.id})">Mark as Read</button>` : ''}
            </div>
        </div>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Notification form
    document.getElementById('notificationForm').addEventListener('submit', handleNotificationSubmit);
}

// Open notification modal
function openNotificationModal() {
    const modal = document.getElementById('notificationModal');
    const form = document.getElementById('notificationForm');
    
    // Reset form
    form.reset();
    
    modal.classList.add('show');
}

// Close notification modal
function closeNotificationModal() {
    document.getElementById('notificationModal').classList.remove('show');
}

// Mark notification as read
async function markAsRead(id) {
    try {
        await notificationsAPI.markRead(id);
        showToast('Notification marked as read', 'success');
        await loadUnreadCount();
        await loadNotifications();
    } catch (error) {
        console.error('Error marking notification as read:', error);
        showToast('Failed to mark notification as read', 'error');
    }
}

// Mark all notifications as read
async function markAllAsRead() {
    try {
        await notificationsAPI.markAllRead();
        showToast('All notifications marked as read', 'success');
        await loadUnreadCount();
        await loadNotifications();
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        showToast('Failed to mark all notifications as read', 'error');
    }
}

// Handle notification form submission
async function handleNotificationSubmit(event) {
    event.preventDefault();
    
    const notificationData = {
        title: document.getElementById('notificationTitle').value,
        message: document.getElementById('notificationMessage').value,
        notification_type: document.getElementById('notificationType').value
    };
    
    try {
        await notificationsAPI.create(notificationData);
        showToast('Notification sent successfully', 'success');
        closeNotificationModal();
        await loadNotifications();
    } catch (error) {
        console.error('Error sending notification:', error);
        showToast('Failed to send notification', 'error');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initNotificationsPage);
