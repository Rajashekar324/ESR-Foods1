/**
 * Authentication Functions for ESR Foods
 */

// Check if user is authenticated
function isAuthenticated() {
    const user = getCurrentUser();
    return Boolean(user);
}

// Redirect to login if not authenticated
function requireAuth() {
    // Protected HTML routes and every API enforce authentication server-side.
    // Do not reject a valid HttpOnly-cookie session because its UI cache is empty.
    return true;
}

// Login function
async function login(username, password) {
    try {
        const response = await authAPI.login(username, password);
        
        if (response && response.user) {
            removeAuthToken();
            setCurrentUser(response.user);
            localStorage.setItem('sessionExpiresAt', String(Date.now() + (response.expires_in || 86400) * 1000));
            scheduleSessionExpiry();
            
            navigateForRole(response.user);
            return true;
        }
        return false;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

// Register function
async function register(username, email, password, full_name, phone) {
    try {
        // Send registration without role_id - backend will default to staff
        const userData = {
            username,
            email,
            password,
            full_name,
            phone
        };

        return await authAPI.register(userData);
    } catch (error) {
        console.error('Registration error:', error);
        throw error;
    }
}

// Logout function
async function logout() {
    try {
        await authAPI.logout();
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        removeAuthToken();
        removeCurrentUser();
        localStorage.removeItem('sessionExpiresAt');
        window.location.href = 'login.html';
    }
}

function scheduleSessionExpiry() {
    const expiry = Number(localStorage.getItem('sessionExpiresAt'));
    if (!expiry) return;
    const remaining = expiry - Date.now();
    if (remaining <= 0) {
        removeAuthToken();
        removeCurrentUser();
        localStorage.removeItem('sessionExpiresAt');
        if (!window.location.pathname.endsWith('login.html')) window.location.replace('login.html');
        return;
    }
    window.setTimeout(() => {
        removeAuthToken();
        removeCurrentUser();
        localStorage.removeItem('sessionExpiresAt');
        window.location.replace('login.html');
    }, Math.min(remaining, 2147483647));
}

// Initialize authentication on page load
function initAuth() {
    scheduleSessionExpiry();
    // Check if on login page
    if (window.location.pathname.endsWith('login.html') || window.location.pathname === '/') {
        
        // If already authenticated, redirect to dashboard
        if (isAuthenticated()) restoreLoginSession();
        
        // Setup login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }
        
        // Setup register form
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', handleRegister);
        }
        
        // Setup toggle button
        const toggleBtn = document.getElementById('toggleAuth');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleAuthMode);
        }
        const forgotButton = document.getElementById('forgotPassword');
        if (forgotButton) {
            forgotButton.addEventListener('click', () => {
                const message = document.getElementById('successMessage');
                message.textContent = 'For account security, contact your ESR Foods administrator to reset your password.';
                message.classList.add('show');
            });
        }
    } else {
        // On other pages, require authentication
        restoreSession();
    }
}

async function restoreSession() {
    try {
        const user = await authAPI.getCurrentUser();
        setCurrentUser(user);
        applyRoleNavigation(user);
        const userName = document.getElementById('userName');
        if (userName) userName.textContent = user.full_name || user.username;
    } catch (_) {
        removeCurrentUser();
        window.location.replace('login.html');
    }
}

async function restoreLoginSession() {
    try {
        const user = await authAPI.getCurrentUser();
        setCurrentUser(user);
        navigateForRole(user);
    } catch (_) {
        removeCurrentUser();
        localStorage.removeItem('sessionExpiresAt');
    }
}

function navigateForRole(user) {
    window.location.href = user?.role?.name === 'staff' ? 'notifications.html' : 'dashboard.html';
}

function applyRoleNavigation(user) {
    if (!user || !user.role) return;
    const role = user.role.name;
    document.querySelectorAll('.sidebar-nav a[href="users.html"]').forEach(link => {
        if (role !== 'admin') link.hidden = true;
    });
    document.querySelectorAll('.sidebar-nav a[href="settings.html"]').forEach(link => {
        if (role !== 'admin') link.hidden = true;
    });
    if (role === 'staff') {
        document.querySelectorAll('.sidebar-nav a').forEach(link => {
            const href = link.getAttribute('href');
            if (href !== 'notifications.html' && href !== '#') link.hidden = true;
        });
    }
}

// Toggle between login and register forms
function toggleAuthMode() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleBtn = document.getElementById('toggleAuth');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const forgotWrap = document.getElementById('forgotWrap');
    
    // Hide error message
    errorMessage.classList.remove('show');
    errorMessage.textContent = '';
    if (successMessage) successMessage.classList.remove('show');
    
    if (loginForm.style.display === 'none') {
        // Show login form
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        if (forgotWrap) forgotWrap.style.display = 'flex';
        toggleBtn.textContent = "Don't have an account? Register";
    } else {
        // Show register form
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        if (forgotWrap) forgotWrap.style.display = 'none';
        toggleBtn.textContent = "Already have an account? Sign In";
    }
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    
    // Reset error message
    errorMessage.classList.remove('show');
    errorMessage.textContent = '';
    if (successMessage) successMessage.classList.remove('show');
    
    // Show loading state
    loginBtn.classList.add('loading');
    loginBtn.disabled = true;
    
    try {
        await login(username, password);
    } catch (error) {
        // Show error message
        errorMessage.textContent = error.message || 'Login failed. Please check your credentials.';
        errorMessage.classList.add('show');
        
        // Reset button state
        loginBtn.classList.remove('loading');
        loginBtn.disabled = false;
    }
}

// Handle register form submission
async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const fullName = document.getElementById('regFullName').value;
    const phone = document.getElementById('regPhone').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;
    const registerBtn = document.getElementById('registerBtn');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    
    // Reset error message
    errorMessage.classList.remove('show');
    errorMessage.textContent = '';
    if (successMessage) successMessage.classList.remove('show');
    
    // Validate passwords match
    if (password !== confirmPassword) {
        errorMessage.textContent = 'Passwords do not match';
        errorMessage.classList.add('show');
        return;
    }

    if (password.length < 12 || !/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
        errorMessage.textContent = 'Use at least 12 characters with uppercase, lowercase, and a number.';
        errorMessage.classList.add('show');
        return;
    }
    
    // Show loading state
    registerBtn.classList.add('loading');
    registerBtn.disabled = true;
    
    try {
        await register(username, email, password, fullName, phone);
        registerBtn.classList.remove('loading');
        registerBtn.disabled = false;
        document.getElementById('registerForm').reset();
        toggleAuthMode();
        if (successMessage) {
            successMessage.textContent = 'Your registration has been submitted. Access will be available after Admin approval.';
            successMessage.classList.add('show');
        }
    } catch (error) {
        // Show error message
        errorMessage.textContent = error.message || 'Registration failed. Please try again.';
        errorMessage.classList.add('show');
        
        // Reset button state
        registerBtn.classList.remove('loading');
        registerBtn.disabled = false;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initAuth);

