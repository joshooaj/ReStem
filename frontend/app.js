// Demucs Frontend - Main Application
const API_URL = 'http://localhost:8000';
let currentToken = localStorage.getItem('token');
let currentUser = null;

// Page Navigation
const pages = {
    login: document.getElementById('login-page'),
    register: document.getElementById('register-page'),
    dashboard: document.getElementById('dashboard-page'),
    upload: document.getElementById('upload-page'),
    purchase: document.getElementById('purchase-page')
};

function showPage(pageName) {
    Object.values(pages).forEach(page => page.style.display = 'none');
    if (pages[pageName]) {
        pages[pageName].style.display = 'block';
    }
}

// Authentication Check
async function checkAuth() {
    if (!currentToken) {
        showPage('login');
        return false;
    }

    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            currentUser = await response.json();
            updateUserInfo();
            return true;
        } else {
            localStorage.removeItem('token');
            currentToken = null;
            showPage('login');
            return false;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showPage('login');
        return false;
    }
}

// Update User Info in UI
function updateUserInfo() {
    if (currentUser) {
        document.getElementById('user-name').textContent = currentUser.username;
        document.getElementById('user-email').textContent = currentUser.email;
        document.getElementById('credit-balance').textContent = currentUser.credits.toFixed(1);
        document.getElementById('header-credits').textContent = currentUser.credits.toFixed(1);
    }
}

// Login
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorDiv = document.getElementById('login-error');

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            currentToken = data.access_token;
            localStorage.setItem('token', currentToken);
            await checkAuth();
            showPage('dashboard');
            await loadDashboard();
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
});

// Register
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('register-email').value;
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    const errorDiv = document.getElementById('register-error');

    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username, password })
        });

        if (response.ok) {
            const data = await response.json();
            currentToken = data.access_token;
            localStorage.setItem('token', currentToken);
            await checkAuth();
            showPage('dashboard');
            await loadDashboard();
            showNotification('Welcome! You received 3 free credits!', 'success');
        } else {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Registration failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
});

// Logout
function logout() {
    localStorage.removeItem('token');
    currentToken = null;
    currentUser = null;
    showPage('login');
    showNotification('Logged out successfully', 'info');
}

// Load Dashboard
async function loadDashboard() {
    await Promise.all([
        loadTransactionHistory(),
        loadJobList()
    ]);
}

// Load Transaction History
async function loadTransactionHistory() {
    try {
        const response = await fetch(`${API_URL}/credits/history`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            const transactions = data.transactions || [];
            const tbody = document.getElementById('transaction-history');
            tbody.innerHTML = '';

            if (transactions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #999;">No transactions yet</td></tr>';
                return;
            }

            transactions.forEach(tx => {
                const row = document.createElement('tr');
                const amountClass = tx.amount >= 0 ? 'credit-positive' : 'credit-negative';
                const amountPrefix = tx.amount >= 0 ? '+' : '';
                
                row.innerHTML = `
                    <td>${new Date(tx.created_at).toLocaleDateString()}</td>
                    <td>${tx.description}</td>
                    <td class="${amountClass}">${amountPrefix}${tx.amount.toFixed(1)}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load transaction history:', error);
    }
}

// Load Job List
async function loadJobList() {
    try {
        const response = await fetch(`${API_URL}/jobs`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            const jobs = data.jobs || [];
            const tbody = document.getElementById('job-list');
            tbody.innerHTML = '';

            if (jobs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #999;">No jobs yet</td></tr>';
                return;
            }

            jobs.forEach(job => {
                const row = document.createElement('tr');
                const statusClass = `status-${job.status.toLowerCase()}`;
                
                row.innerHTML = `
                    <td>${job.filename}</td>
                    <td>${job.model}</td>
                    <td><span class="status-badge ${statusClass}">${job.status}</span></td>
                    <td>${new Date(job.created_at).toLocaleString()}</td>
                    <td>
                        ${job.status === 'COMPLETED' ? 
                            `<button onclick="downloadJob('${job.id}')" class="btn-download">Download</button>` : 
                            `<button onclick="checkJobStatus('${job.id}')" class="btn-refresh">Refresh</button>`
                        }
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load job list:', error);
    }
}

// Upload Audio
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('audio-file');
    const model = document.getElementById('model-select').value;
    const errorDiv = document.getElementById('upload-error');
    const progressDiv = document.getElementById('upload-progress');

    if (!fileInput.files[0]) {
        errorDiv.textContent = 'Please select an audio file';
        errorDiv.style.display = 'block';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('model', model);

    try {
        progressDiv.style.display = 'block';
        errorDiv.style.display = 'none';

        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${currentToken}` },
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showNotification('Upload successful! Processing started.', 'success');
            fileInput.value = '';
            progressDiv.style.display = 'none';
            
            // Refresh user info and dashboard
            await checkAuth();
            await loadDashboard();
            showPage('dashboard');
        } else {
            const error = await response.json();
            progressDiv.style.display = 'none';
            errorDiv.textContent = error.detail || 'Upload failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        progressDiv.style.display = 'none';
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
});

// Check Job Status
async function checkJobStatus(jobId) {
    try {
        const response = await fetch(`${API_URL}/status/${jobId}`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            await loadJobList();
            showNotification('Job status updated', 'info');
        }
    } catch (error) {
        console.error('Failed to check job status:', error);
    }
}

// Download Job
async function downloadJob(jobId) {
    try {
        const response = await fetch(`${API_URL}/download/${jobId}`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `separated_tracks_${jobId}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Download started', 'success');
        } else {
            showNotification('Download failed', 'error');
        }
    } catch (error) {
        console.error('Download failed:', error);
        showNotification('Download failed', 'error');
    }
}

// Square Payment (Placeholder - will implement with actual Square SDK)
async function initializeSquarePayment() {
    // TODO: Initialize Square Web Payments SDK
    // This will be implemented in the next step with actual Square credentials
    document.getElementById('square-payment-form').style.display = 'block';
}

// Credit Purchase
async function purchaseCredits(amount, price) {
    // Placeholder for Square payment integration
    try {
        const response = await fetch(`${API_URL}/credits/purchase`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount, payment_method: 'square', transaction_id: 'placeholder' })
        });

        if (response.ok) {
            await checkAuth();
            await loadDashboard();
            showPage('dashboard');
            showNotification(`Successfully purchased ${amount} credits!`, 'success');
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Purchase failed', 'error');
        }
    } catch (error) {
        showNotification('Network error. Please try again.', 'error');
    }
}

// Notification System
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Navigation Buttons
document.getElementById('nav-dashboard').addEventListener('click', () => {
    showPage('dashboard');
    loadDashboard();
});

document.getElementById('nav-upload').addEventListener('click', () => {
    showPage('upload');
});

document.getElementById('nav-purchase').addEventListener('click', () => {
    showPage('purchase');
});

document.getElementById('nav-logout').addEventListener('click', logout);

document.getElementById('show-register').addEventListener('click', (e) => {
    e.preventDefault();
    showPage('register');
});

document.getElementById('show-login').addEventListener('click', (e) => {
    e.preventDefault();
    showPage('login');
});

// Initialize App
(async function init() {
    const isAuthenticated = await checkAuth();
    if (isAuthenticated) {
        showPage('dashboard');
        await loadDashboard();
    } else {
        showPage('login');
    }
})();
