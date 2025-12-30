// Mux Minus - Main Application
// Use empty string for relative URLs (works with reverse proxy)
const API_URL = '';
let currentToken = localStorage.getItem('token');
let currentUser = null;
let squarePayments = null;
let jobPollingInterval = null; // For automatic job status updates
let squareCard = null;
let selectedPackage = null;
let transactionsData = []; // Store transactions for export

// Page Navigation
const pages = {
    landing: document.getElementById('landing-page'),
    login: document.getElementById('login-page'),
    register: document.getElementById('register-page'),
    dashboard: document.getElementById('dashboard-page'),
    purchase: document.getElementById('purchase-page'),
    profile: document.getElementById('profile-page'),
    admin: document.getElementById('admin-page')
};

function showPage(pageName) {
    Object.values(pages).forEach(page => page.style.display = 'none');
    if (pages[pageName]) {
        pages[pageName].style.display = 'block';
        
        // Update URL without reloading the page
        let path = '/';
        if (pageName === 'landing') {
            path = '/';
        } else if (pageName === 'login') {
            path = '/login';
        } else if (pageName === 'register') {
            path = '/register';
        } else if (pageName === 'dashboard') {
            path = '/dashboard';
        } else if (pageName === 'purchase') {
            path = '/purchase';
        } else if (pageName === 'profile') {
            path = '/profile';
        } else if (pageName === 'admin') {
            path = '/admin';
        }
        
        if (window.location.pathname !== path) {
            window.history.pushState({ page: pageName }, '', path);
        }
    }
    
    // Stop polling when leaving dashboard
    if (pageName !== 'dashboard') {
        stopJobPolling();
    }
}

// Handle browser back/forward buttons
window.addEventListener('popstate', (event) => {
    const path = window.location.pathname;
    
    if (event.state && event.state.page) {
        // Show the page without updating history (to avoid duplicate entries)
        Object.values(pages).forEach(page => page.style.display = 'none');
        if (pages[event.state.page]) {
            pages[event.state.page].style.display = 'block';
        }
        
        // Load page-specific data
        if (event.state.page === 'purchase' && currentToken) {
            loadPurchasePage();
        } else if (event.state.page === 'profile' && currentToken) {
            loadProfilePage();
        } else if (event.state.page === 'admin' && currentToken) {
            loadAdminPage();
        }
        
        // Stop polling if not on dashboard
        if (event.state.page !== 'dashboard') {
            stopJobPolling();
        }
    } else {
        // No state - determine page from URL path
        let targetPage = 'landing';
        
        if (path === '/login') {
            targetPage = 'login';
        } else if (path === '/register') {
            targetPage = 'register';
        } else if (path === '/dashboard') {
            targetPage = currentToken ? 'dashboard' : 'landing';
        } else if (path === '/purchase') {
            targetPage = currentToken ? 'purchase' : 'landing';
        } else if (path === '/admin') {
            targetPage = currentToken ? 'admin' : 'landing';
            if (currentToken) loadAdminPage();
        } else {
            // Root or unknown path
            targetPage = currentToken ? 'dashboard' : 'landing';
        }
        
        Object.values(pages).forEach(page => page.style.display = 'none');
        if (pages[targetPage]) {
            pages[targetPage].style.display = 'block';
        }
        
        // Load page-specific data
        if (targetPage === 'purchase' && currentToken) {
            loadPurchasePage();
        }
        
        if (targetPage !== 'dashboard') {
            stopJobPolling();
        }
    }
});

// Authentication Check
async function checkAuth() {
    if (!currentToken) {
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
            return false;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

// Update User Info in UI
function updateUserInfo() {
    if (currentUser) {
        document.getElementById('user-name').textContent = currentUser.username;
        const credits = currentUser.credits.toFixed(1);
        document.getElementById('header-credits').textContent = credits;
        document.getElementById('header-credits-purchase').textContent = credits;
        
        // Update profile page if it exists
        const profileCredits = document.getElementById('header-credits-profile');
        if (profileCredits) {
            profileCredits.textContent = credits;
        }
        
        // Show admin button if user is admin
        const adminButton = document.getElementById('admin-button');
        if (adminButton) {
            adminButton.style.display = currentUser.is_admin ? 'block' : 'none';
        }
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

// Go Home (Landing or Dashboard depending on auth state)
window.goHome = function() {
    if (currentToken) {
        showPage('dashboard');
        loadDashboard();
    } else {
        showPage('landing');
    }
};

// Load Dashboard
async function loadDashboard() {
    await loadJobList();
}

// Load Purchase Page
async function loadPurchasePage() {
    // Update user info
    if (currentUser) {
        document.getElementById('user-name-purchase').textContent = currentUser.username;
        document.getElementById('header-credits-purchase').textContent = currentUser.credits.toFixed(1);
    }
}

// Load Profile Page
async function loadProfilePage() {
    if (!currentUser) return;
    
    // Populate current values
    document.getElementById('current-email').textContent = currentUser.email;
    document.getElementById('current-username').textContent = currentUser.username;
    document.getElementById('header-credits-profile').textContent = currentUser.credits.toFixed(1);
    document.getElementById('account-id').textContent = currentUser.id;
    
    // Format member since date
    const memberSince = new Date(currentUser.created_at);
    document.getElementById('member-since').textContent = memberSince.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    // Clear forms
    document.getElementById('update-email-form').reset();
    document.getElementById('update-username-form').reset();
    document.getElementById('update-password-form').reset();
    
    // Clear messages
    ['email', 'username', 'password'].forEach(type => {
        const errorDiv = document.getElementById(`${type}-error`);
        const successDiv = document.getElementById(`${type}-success`);
        if (errorDiv) errorDiv.textContent = '';
        if (successDiv) successDiv.style.display = 'none';
    });
}

// Update Email
window.updateEmail = async function(event) {
    event.preventDefault();
    const errorDiv = document.getElementById('email-error');
    const successDiv = document.getElementById('email-success');
    const newEmail = document.getElementById('new-email').value;
    
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/auth/email`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: newEmail })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to update email');
        }
        
        // Update current user
        currentUser.email = newEmail;
        document.getElementById('current-email').textContent = newEmail;
        document.getElementById('update-email-form').reset();
        
        // Show success message
        successDiv.textContent = 'Email updated successfully!';
        successDiv.style.display = 'block';
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
};

// Update Username
window.updateUsername = async function(event) {
    event.preventDefault();
    const errorDiv = document.getElementById('username-error');
    const successDiv = document.getElementById('username-success');
    const newUsername = document.getElementById('new-username').value;
    
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/auth/username`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: newUsername })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to update username');
        }
        
        // Update current user and UI
        currentUser.username = newUsername;
        document.getElementById('current-username').textContent = newUsername;
        document.getElementById('user-name').textContent = newUsername;
        document.getElementById('user-name-purchase').textContent = newUsername;
        document.getElementById('update-username-form').reset();
        
        // Show success message
        successDiv.textContent = 'Username updated successfully!';
        successDiv.style.display = 'block';
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
};

// Update Password
window.updatePassword = async function(event) {
    event.preventDefault();
    const errorDiv = document.getElementById('password-error');
    const successDiv = document.getElementById('password-success');
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'New passwords do not match';
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/auth/password`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to update password');
        }
        
        document.getElementById('update-password-form').reset();
        
        // Show success message
        successDiv.textContent = 'Password updated successfully!';
        successDiv.style.display = 'block';
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
};

// Show Delete Account Modal
window.showDeleteAccountModal = function() {
    const modal = document.getElementById('delete-account-modal');
    const errorDiv = document.getElementById('delete-error');
    const passwordField = document.getElementById('delete-password');
    
    // Clear form and errors
    passwordField.value = '';
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    
    modal.style.display = 'flex';
};

// Close Delete Account Modal
window.closeDeleteAccountModal = function() {
    const modal = document.getElementById('delete-account-modal');
    modal.style.display = 'none';
};

// Confirm Delete Account
window.confirmDeleteAccount = async function(event) {
    event.preventDefault();
    const errorDiv = document.getElementById('delete-error');
    const password = document.getElementById('delete-password').value;
    
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/auth/account`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to delete account');
        }
        
        // Close modal
        closeDeleteAccountModal();
        
        // Account deleted successfully - logout and redirect
        showNotification('Your account has been permanently deleted', 'info');
        
        // Clear local data
        localStorage.removeItem('token');
        currentToken = null;
        currentUser = null;
        
        // Redirect to landing page after a brief delay
        setTimeout(() => {
            showPage('landing');
        }, 2000);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
};

// Show Transaction History Modal
window.showTransactionHistory = async function() {
    const modal = document.getElementById('transaction-modal');
    modal.style.display = 'flex';
    await loadTransactionHistory();
};

// Close Transaction History Modal
window.closeTransactionHistory = function() {
    const modal = document.getElementById('transaction-modal');
    modal.style.display = 'none';
};

// Close modal when clicking outside of it
window.addEventListener('click', (event) => {
    const modal = document.getElementById('transaction-modal');
    if (event.target === modal) {
        closeTransactionHistory();
    }
});

// Load Transaction History
async function loadTransactionHistory() {
    try {
        const response = await fetch(`${API_URL}/credits/history`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            const transactions = data.transactions || [];
            transactionsData = transactions; // Store for export
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

// Export Transaction History to CSV
window.exportTransactionHistory = function() {
    if (!transactionsData || transactionsData.length === 0) {
        showNotification('No transactions to export', 'info');
        return;
    }

    // Create CSV header
    const csvRows = [];
    csvRows.push(['Date', 'Description', 'Amount', 'Credits', 'Balance'].join(','));

    // Add transaction rows
    transactionsData.forEach(tx => {
        const date = new Date(tx.created_at).toLocaleString();
        const description = `"${tx.description.replace(/"/g, '""')}"`;
        const amount = tx.amount.toFixed(1);
        const balance = tx.balance_after ? tx.balance_after.toFixed(1) : '';
        
        csvRows.push([date, description, amount, balance].join(','));
    });

    // Create blob and download
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `muxminus_transactions_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    showNotification('Transaction history exported', 'success');
};

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

            if (jobs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #999;">No jobs yet</td></tr>';
                stopJobPolling();
                return;
            }

            // Check if any jobs are processing
            const processingJobs = jobs.filter(job => 
                job.status.toUpperCase() === 'PENDING' || job.status.toUpperCase() === 'PROCESSING'
            );

            // Update polling job IDs
            pollingJobIds.clear();
            processingJobs.forEach(job => pollingJobIds.add(job.id));

            // Start or stop polling based on job status
            if (pollingJobIds.size > 0) {
                startJobPolling();
            } else {
                stopJobPolling();
            }

            // Build a map of existing rows by job ID
            const existingRows = new Map();
            const rows = Array.from(tbody.querySelectorAll('tr[data-job-id]'));
            rows.forEach(row => {
                const jobId = row.getAttribute('data-job-id');
                existingRows.set(jobId, row);
            });
            
            // Remove any non-job rows (like loading messages)
            const nonJobRows = Array.from(tbody.querySelectorAll('tr:not([data-job-id])'));
            nonJobRows.forEach(row => row.remove());

            jobs.forEach(job => {
                const existingRow = existingRows.get(job.id);
                const statusClass = `status-${job.status.toLowerCase()}`;
                
                // Add visual indicator for processing jobs
                let statusBadge = `<span class="status-badge ${statusClass}">${job.status}</span>`;
                if (job.status.toUpperCase() === 'PROCESSING') {
                    statusBadge += ' <span style="animation: pulse 1.5s infinite;">⏳</span>';
                }

                if (existingRow) {
                    // Update existing row ONLY if status changed
                    const currentStatus = existingRow.getAttribute('data-status');
                    if (currentStatus !== job.status) {
                        // Only update the cells that changed, preserve the row itself
                        existingRow.cells[2].innerHTML = statusBadge;
                        existingRow.cells[4].innerHTML = job.status.toUpperCase() === 'COMPLETED' ? 
                            `<button onclick="showJobDetails('${job.id}')" class="btn-download">View/Play</button>
                             <button onclick="downloadJob('${job.id}')" class="btn-download">Download</button>` : 
                            `<button onclick="checkJobStatus('${job.id}')" class="btn-refresh">Refresh</button>`;
                        
                        existingRow.setAttribute('data-status', job.status);
                        
                        // If job just completed, create the details row
                        if (job.status.toUpperCase() === 'COMPLETED') {
                            let detailsRow = document.getElementById(`job-details-${job.id}`);
                            if (!detailsRow) {
                                detailsRow = document.createElement('tr');
                                detailsRow.id = `job-details-${job.id}`;
                                detailsRow.style.display = 'none';
                                detailsRow.innerHTML = `
                                    <td colspan="5" style="padding: 20px; background: #f9fafb;">
                                        <div id="stems-${job.id}" style="display: flex; flex-direction: column; gap: 15px;">
                                            <p style="color: #667eea; font-weight: 600;">Loading stems...</p>
                                        </div>
                                    </td>
                                `;
                                existingRow.insertAdjacentElement('afterend', detailsRow);
                            }
                        }
                    }
                    existingRows.delete(job.id);
                } else {
                    // New job - add it at the top
                    const row = document.createElement('tr');
                    row.setAttribute('data-job-id', job.id);
                    row.setAttribute('data-status', job.status);
                    row.innerHTML = `
                        <td>${job.filename}</td>
                        <td>${job.model}</td>
                        <td>${statusBadge}</td>
                        <td>${new Date(job.created_at).toLocaleString()}</td>
                        <td>
                            ${job.status.toUpperCase() === 'COMPLETED' ? 
                                `<button onclick="showJobDetails('${job.id}')" class="btn-download">View/Play</button>
                                 <button onclick="downloadJob('${job.id}')" class="btn-download">Download</button>` : 
                                `<button onclick="checkJobStatus('${job.id}')" class="btn-refresh">Refresh</button>`
                            }
                        </td>
                    `;
                    tbody.insertBefore(row, tbody.firstChild);
                    
                    // Add details row if completed
                    if (job.status.toUpperCase() === 'COMPLETED') {
                        const detailsRow = document.createElement('tr');
                        detailsRow.id = `job-details-${job.id}`;
                        detailsRow.style.display = 'none';
                        detailsRow.innerHTML = `
                            <td colspan="5" style="padding: 20px; background: #f9fafb;">
                                <div id="stems-${job.id}" style="display: flex; flex-direction: column; gap: 15px;">
                                    <p style="color: #667eea; font-weight: 600;">Loading stems...</p>
                                </div>
                            </td>
                        `;
                        row.insertAdjacentElement('afterend', detailsRow);
                    }
                }
            });

            // Remove jobs that no longer exist
            existingRows.forEach((row, jobId) => {
                row.remove();
                const detailsRow = document.getElementById(`job-details-${jobId}`);
                if (detailsRow) detailsRow.remove();
            });
        }
    } catch (error) {
        console.error('Failed to load job list:', error);
    }
}

// Drag and Drop for Upload Area
const uploadArea = document.querySelector('.upload-area');
if (uploadArea) {
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragging');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragging');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragging');
        
        const fileInput = document.getElementById('audio-file');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            // Show file name
            const fileName = e.dataTransfer.files[0].name;
            const fileInfo = document.createElement('p');
            fileInfo.style.marginTop = '10px';
            fileInfo.style.color = '#4f46e5';
            fileInfo.innerHTML = `<strong>Selected:</strong> ${fileName}`;
            const existingInfo = uploadArea.querySelector('p[style*="color: rgb"]');
            if (existingInfo) existingInfo.remove();
            uploadArea.appendChild(fileInfo);
        }
    });
}

// Stem count selector event listener
document.getElementById('stem-count').addEventListener('change', (e) => {
    const twoStemOption = document.getElementById('two-stem-option');
    if (e.target.value === '2') {
        twoStemOption.style.display = 'block';
    } else {
        twoStemOption.style.display = 'none';
    }
});

// Upload Audio
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('audio-file');
    const model = document.getElementById('model-select').value;
    const stemCount = document.getElementById('stem-count').value;
    const twoStemType = document.getElementById('two-stem-type').value;
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
    formData.append('stem_count', stemCount);
    if (stemCount === '2') {
        formData.append('two_stem_type', twoStemType);
    }
    
    console.log('Upload params:', { model, stem_count: stemCount, two_stem_type: stemCount === '2' ? twoStemType : 'N/A' });

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

// Check Job Status (Global function for onclick)
window.checkJobStatus = async function(jobId) {
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
};

// Track jobs that are currently being polled
let pollingJobIds = new Set();

// Start automatic job status polling
function startJobPolling() {
    // Don't start if already polling
    if (jobPollingInterval) {
        return;
    }
    
    console.log('Starting job status polling...');
    jobPollingInterval = setInterval(async () => {
        // Only poll if we're on the dashboard page and have jobs to track
        const dashboardPage = document.getElementById('dashboard-page');
        if (dashboardPage && dashboardPage.style.display !== 'none' && pollingJobIds.size > 0) {
            await pollJobStatuses();
        }
    }, 5000); // Poll every 5 seconds
}

// Poll only the jobs that are in progress
async function pollJobStatuses() {
    if (pollingJobIds.size === 0) {
        stopJobPolling();
        return;
    }
    
    // Poll each job individually
    const pollPromises = Array.from(pollingJobIds).map(async (jobId) => {
        try {
            const response = await fetch(`${API_URL}/jobs/${jobId}`, {
                headers: { 'Authorization': `Bearer ${currentToken}` }
            });

            if (response.ok) {
                const job = await response.json();
                updateJobInList(job);
                
                // Remove from polling if no longer in progress
                if (job.status.toUpperCase() !== 'PENDING' && job.status.toUpperCase() !== 'PROCESSING') {
                    pollingJobIds.delete(job.id);
                }
            }
        } catch (error) {
            console.error(`Failed to poll job ${jobId}:`, error);
        }
    });
    
    await Promise.all(pollPromises);
    
    // Stop polling if no jobs left to track
    if (pollingJobIds.size === 0) {
        stopJobPolling();
    }
}

// Update a single job in the list without touching other DOM elements
function updateJobInList(job) {
    const existingRow = document.querySelector(`tr[data-job-id="${job.id}"]`);
    if (!existingRow) return;
    
    const currentStatus = existingRow.getAttribute('data-status');
    if (currentStatus === job.status) return; // No change
    
    const statusClass = `status-${job.status.toLowerCase()}`;
    let statusBadge = `<span class="status-badge ${statusClass}">${job.status}</span>`;
    if (job.status.toUpperCase() === 'PROCESSING') {
        statusBadge += ' <span style="animation: pulse 1.5s infinite;">⏳</span>';
    }
    
    // Update only the cells that changed
    existingRow.cells[2].innerHTML = statusBadge;
    existingRow.cells[4].innerHTML = job.status.toUpperCase() === 'COMPLETED' ? 
        `<button onclick="showJobDetails('${job.id}')" class="btn-download">View/Play</button>
         <button onclick="downloadJob('${job.id}')" class="btn-download">Download</button>` : 
        `<button onclick="checkJobStatus('${job.id}')" class="btn-refresh">Refresh</button>`;
    
    existingRow.setAttribute('data-status', job.status);
    
    // If job just completed, create the details row
    if (job.status.toUpperCase() === 'COMPLETED') {
        let detailsRow = document.getElementById(`job-details-${job.id}`);
        if (!detailsRow) {
            detailsRow = document.createElement('tr');
            detailsRow.id = `job-details-${job.id}`;
            detailsRow.style.display = 'none';
            detailsRow.innerHTML = `
                <td colspan="5" style="padding: 20px; background: #f9fafb;">
                    <div id="stems-${job.id}" style="display: flex; flex-direction: column; gap: 15px;">
                        <p style="color: #667eea; font-weight: 600;">Loading stems...</p>
                    </div>
                </td>
            `;
            existingRow.insertAdjacentElement('afterend', detailsRow);
        }
    }
}

// Stop automatic job status polling
function stopJobPolling() {
    if (jobPollingInterval) {
        console.log('Stopping job status polling...');
        clearInterval(jobPollingInterval);
        jobPollingInterval = null;
    }
}

// Download Job (Global function for onclick)
window.downloadJob = async function(jobId) {
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
};

// Show job details and stems (Global function for onclick)
window.showJobDetails = async function(jobId) {
    const detailsRow = document.getElementById(`job-details-${jobId}`);
    const stemsDiv = document.getElementById(`stems-${jobId}`);
    
    // If details row doesn't exist, create it
    if (!detailsRow) {
        const jobRow = document.querySelector(`tr[data-job-id="${jobId}"]`);
        if (!jobRow) {
            console.error(`Job row not found for ${jobId}`);
            return;
        }
        
        const newDetailsRow = document.createElement('tr');
        newDetailsRow.id = `job-details-${jobId}`;
        newDetailsRow.style.display = 'table-row';
        newDetailsRow.innerHTML = `
            <td colspan="5" style="padding: 20px; background: #f9fafb;">
                <div id="stems-${jobId}" style="display: flex; flex-direction: column; gap: 15px;">
                    <p style="color: #667eea; font-weight: 600;">Loading stems...</p>
                </div>
            </td>
        `;
        jobRow.insertAdjacentElement('afterend', newDetailsRow);
        
        // Now load the stems
        await loadJobStems(jobId);
        return;
    }
    
    // Toggle visibility
    if (detailsRow.style.display === 'none') {
        detailsRow.style.display = 'table-row';
        
        // Load stems if not already loaded
        if (stemsDiv && stemsDiv.innerHTML.includes('Loading stems')) {
            await loadJobStems(jobId);
        }
    } else {
        detailsRow.style.display = 'none';
    }
};

// Load stems for a job
async function loadJobStems(jobId) {
    const stemsDiv = document.getElementById(`stems-${jobId}`);
    if (!stemsDiv) return;
    
    try {
        const response = await fetch(`${API_URL}/stems/${jobId}`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const stems = data.stems || [];
            
            if (stems.length === 0) {
                stemsDiv.innerHTML = '<p style="color: #ef4444;">No stems found</p>';
                return;
            }
            
            // Create audio players for each stem
            stemsDiv.innerHTML = stems.map(stem => `
                <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #667eea; text-transform: capitalize;">${stem.name}</h4>
                        <button onclick="downloadSingleStem('${jobId}', '${stem.name}')" class="btn-download" style="padding: 6px 12px; font-size: 0.9rem;">
                            Download
                        </button>
                    </div>
                    <audio id="audio-${jobId}-${stem.name}" controls style="width: 100%;" preload="none">
                        Loading...
                    </audio>
                </div>
            `).join('');
            
            // Fetch each audio file as blob and create object URLs
            for (const stem of stems) {
                const audioElement = document.getElementById(`audio-${jobId}-${stem.name}`);
                try {
                    const audioResponse = await fetch(`${API_URL}${stem.url}`, {
                        headers: { 'Authorization': `Bearer ${currentToken}` }
                    });
                    
                    if (audioResponse.ok) {
                        const blob = await audioResponse.blob();
                        const url = window.URL.createObjectURL(blob);
                        audioElement.src = url;
                        
                        // Clean up object URL when audio is loaded
                        audioElement.addEventListener('loadeddata', () => {
                            // URL will be revoked when page unloads
                        }, { once: true });
                    } else {
                        audioElement.outerHTML = '<p style="color: #ef4444; margin: 0;">Failed to load audio</p>';
                    }
                } catch (error) {
                    console.error(`Failed to load stem ${stem.name}:`, error);
                    audioElement.outerHTML = '<p style="color: #ef4444; margin: 0;">Error loading audio</p>';
                }
            }
        } else {
            stemsDiv.innerHTML = '<p style="color: #ef4444;">Failed to load stems</p>';
        }
    } catch (error) {
        console.error('Failed to load stems:', error);
        stemsDiv.innerHTML = '<p style="color: #ef4444;">Error loading stems</p>';
    }
}

// Download single stem (Global function for onclick)
window.downloadSingleStem = async function(jobId, stemName) {
    try {
        const response = await fetch(`${API_URL}/stems/${jobId}/${stemName}`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${stemName}.mp3`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Download started', 'success');
        } else {
            showNotification('Download failed', 'error');
        }
    } catch (error) {
        console.error('Download error:', error);
        showNotification('Download error', 'error');
    }
};

// Square Payment Integration
// Load Square SDK dynamically based on environment
async function loadSquareSDK(environment) {
    return new Promise((resolve, reject) => {
        // Check if already loaded
        if (window.Square) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = environment === 'production' 
            ? 'https://web.squarecdn.com/v1/square.js'
            : 'https://sandbox.web.squarecdn.com/v1/square.js';
        
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Failed to load Square SDK'));
        
        document.head.appendChild(script);
    });
}

async function initializeSquarePayments() {
    try {
        const response = await fetch(`${API_URL}/credits/square-config`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (!response.ok) {
            throw new Error('Square not configured');
        }
        
        const config = await response.json();
        
        // Load the appropriate Square SDK
        await loadSquareSDK(config.environment);
        
        if (!window.Square) {
            throw new Error('Square.js failed to load');
        }
        
        squarePayments = window.Square.payments(config.application_id, config.location_id);
        squareCard = await squarePayments.card();
        await squareCard.attach('#card-container');
        
        document.getElementById('card-button').addEventListener('click', handlePayment);
        
        return true;
    } catch (error) {
        console.error('Failed to initialize Square:', error);
        showNotification('Payment system not available. Please contact support.', 'error');
        return false;
    }
}

// Select a credit package
async function selectCreditPackage(amount, price) {
    selectedPackage = { amount, price };
    
    document.getElementById('selected-package').textContent = 
        `Purchase ${amount} credits for $${price.toFixed(2)}`;
    
    const paymentSection = document.getElementById('payment-section');
    paymentSection.style.display = 'block';
    paymentSection.scrollIntoView({ behavior: 'smooth' });
    
    if (!squareCard) {
        await initializeSquarePayments();
    }
}

// Cancel payment
function cancelPayment() {
    selectedPackage = null;
    document.getElementById('payment-section').style.display = 'none';
    if (squareCard) {
        squareCard.destroy();
        squareCard = null;
    }
}

// Handle Square payment
async function handlePayment(event) {
    event.preventDefault();
    
    if (!selectedPackage) {
        showNotification('Please select a package', 'error');
        return;
    }
    
    const cardButton = document.getElementById('card-button');
    const paymentStatus = document.getElementById('payment-status');
    
    try {
        cardButton.disabled = true;
        paymentStatus.innerHTML = '<p style=\"color: #667eea;\">Processing payment...</p>';
        
        // Tokenize card
        const result = await squareCard.tokenize();
        
        if (result.status === 'OK') {
            // Send payment to backend
            const response = await fetch(`${API_URL}/credits/purchase`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${currentToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    amount: selectedPackage.amount,
                    price: selectedPackage.price,
                    payment_nonce: result.token
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                showNotification(`Successfully purchased ${selectedPackage.amount} credits!`, 'success');
                
                // Update user info
                await checkAuth();
                await loadDashboard();
                
                // Reset and go back to dashboard
                cancelPayment();
                showPage('dashboard');
            } else {
                const error = await response.json();
                paymentStatus.innerHTML = `<p style=\"color: #ef4444;\">${error.detail || 'Payment failed'}</p>`;
                showNotification(error.detail || 'Payment failed', 'error');
            }
        } else {
            let errorMessage = 'Payment failed';
            if (result.errors) {
                errorMessage = result.errors.map(error => error.message).join(', ');
            }
            paymentStatus.innerHTML = `<p style=\"color: #ef4444;\">${errorMessage}</p>`;
            showNotification(errorMessage, 'error');
        }
    } catch (error) {
        console.error('Payment error:', error);
        paymentStatus.innerHTML = '<p style=\"color: #ef4444;\">Payment processing error</p>';
        showNotification('Payment processing error', 'error');
    } finally {
        cardButton.disabled = false;
    }
}

// Credit Purchase (Legacy - keeping for compatibility)
async function purchaseCredits(amount, price) {
    selectCreditPackage(amount, price);
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

document.getElementById('nav-purchase').addEventListener('click', () => {
    showPage('purchase');
    loadPurchasePage();
});

document.getElementById('nav-profile').addEventListener('click', () => {
    showPage('profile');
    loadProfilePage();
});

document.getElementById('nav-logout').addEventListener('click', logout);

// Profile page nav buttons
document.getElementById('nav-dashboard-profile').addEventListener('click', () => {
    showPage('dashboard');
    loadDashboard();
});

document.getElementById('nav-purchase-profile').addEventListener('click', () => {
    showPage('purchase');
    loadPurchasePage();
});

document.getElementById('nav-profile-profile').addEventListener('click', () => {
    showPage('profile');
    loadProfilePage();
});

document.getElementById('nav-logout-profile').addEventListener('click', logout);

document.getElementById('show-register').addEventListener('click', (e) => {
    e.preventDefault();
    showPage('register');
});

document.getElementById('show-login').addEventListener('click', (e) => {
    e.preventDefault();
    showPage('login');
});

// Admin page navigation
document.getElementById('nav-admin-users').addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    document.querySelectorAll('.admin-tab').forEach(tab => tab.style.display = 'none');
    document.getElementById('admin-users-tab').style.display = 'block';
    loadAdminUsers();
});

document.getElementById('nav-admin-jobs').addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    document.querySelectorAll('.admin-tab').forEach(tab => tab.style.display = 'none');
    document.getElementById('admin-jobs-tab').style.display = 'block';
    loadAdminJobs();
});

document.getElementById('nav-admin-dashboard').addEventListener('click', (e) => {
    e.preventDefault();
    showPage('dashboard');
});

document.getElementById('nav-admin-logout').addEventListener('click', logout);

// Initialize App
(async function init() {
    const isAuthenticated = await checkAuth();
    
    // Check URL path to determine which page to show
    const path = window.location.pathname;
    let targetPage = 'dashboard';
    
    if (path === '/purchase' || path === '/credits') {
        targetPage = 'purchase';
    } else if (path === '/dashboard') {
        targetPage = 'dashboard';
    } else if (path === '/admin') {
        targetPage = 'admin';
    } else if (path === '/register') {
        targetPage = 'register';
    } else if (path === '/login') {
        targetPage = 'login';
    } else if (path === '/' || path === '/landing') {
        targetPage = isAuthenticated ? 'dashboard' : 'landing';
    }
    
    if (isAuthenticated) {
        showPage(targetPage);
        if (targetPage === 'dashboard' || targetPage === 'purchase') {
            await loadDashboard();
        } else if (targetPage === 'admin') {
            loadAdminPage();
        }
    } else {
        // Non-authenticated users see landing page by default
        if (targetPage === 'login' || targetPage === 'register') {
            showPage(targetPage);
        } else {
            showPage('landing');
        }
    }
})();

// Admin Page Functions

function loadAdminPage() {
    if (!currentUser || !currentUser.is_admin) {
        showPage('dashboard');
        return;
    }
    loadAdminUsers();
}

async function loadAdminUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load users');
        }
        
        const data = await response.json();
        const users = data.users || data; // Handle both {users: [...]} and direct array
        const tbody = document.getElementById('admin-users-tbody');
        
        if (!tbody) {
            console.error('admin-users-tbody element not found');
            throw new Error('Admin users table not found in DOM');
        }
        
        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.credits}</td>
                <td>${user.is_admin ? 'Yes' : 'No'}</td>
                <td>${user.active ? 'Active' : 'Disabled'}</td>
                <td>
                    <button class="action-btn" onclick="viewAdminUser(${user.id})">View</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading users:', error);
        console.error('Error stack:', error.stack);
        showNotification('Failed to load users', 'error');
    }
}

async function loadAdminJobs() {
    try {
        const response = await fetch(`${API_URL}/admin/jobs`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load jobs');
        }
        
        const data = await response.json();
        const jobs = data.jobs || data; // Handle both {jobs: [...]} and direct array
        const tbody = document.getElementById('admin-jobs-tbody');
        
        tbody.innerHTML = jobs.map(job => `
            <tr>
                <td>${job.id}</td>
                <td>${job.user_id}</td>
                <td>${job.username || 'Unknown'}</td>
                <td>${job.filename}</td>
                <td>${job.status}</td>
                <td>${job.archived ? 'Yes' : 'No'}</td>
                <td>${new Date(job.created_at).toLocaleString()}</td>
                <td>
                    ${!job.archived ? `<button class="action-btn" onclick="archiveJob('${job.id}')">Archive</button>` : ''}
                    <button class="action-btn delete-btn" onclick="deleteJob('${job.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading jobs:', error);
        showNotification('Failed to load jobs', 'error');
    }
}

async function viewAdminUser(userId) {
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load user details');
        }
        
        const user = await response.json();
        
        document.getElementById('admin-user-id').textContent = user.id;
        document.getElementById('admin-user-username').textContent = user.username;
        document.getElementById('admin-user-email').textContent = user.email;
        document.getElementById('admin-user-credits').textContent = user.credits;
        document.getElementById('admin-user-status').textContent = user.active ? 'Active' : 'Disabled';
        document.getElementById('admin-user-admin').textContent = user.is_admin ? 'Yes' : 'No';
        document.getElementById('admin-user-created').textContent = new Date(user.created_at).toLocaleString();
        
        // Render jobs
        const jobsHtml = user.jobs && user.jobs.length > 0 ? user.jobs.map(job => `
            <tr>
                <td>${job.filename}</td>
                <td>${job.status}</td>
                <td>${new Date(job.created_at).toLocaleString()}</td>
            </tr>
        `).join('') : '<tr><td colspan="3">No jobs</td></tr>';
        
        document.querySelector('#admin-user-jobs tbody').innerHTML = jobsHtml;
        
        // Render transactions
        const txHtml = user.transactions && user.transactions.length > 0 ? user.transactions.map(tx => `
            <tr>
                <td>${tx.amount > 0 ? '+' : ''}${tx.amount}</td>
                <td>${tx.description}</td>
                <td>${new Date(tx.created_at).toLocaleString()}</td>
            </tr>
        `).join('') : '<tr><td colspan="3">No transactions</td></tr>';
        
        document.querySelector('#admin-user-transactions tbody').innerHTML = txHtml;
        
        // Show modal
        document.getElementById('admin-user-detail-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading user details:', error);
        showNotification('Failed to load user details', 'error');
    }
}

function closeAdminUserModal() {
    document.getElementById('admin-user-detail-modal').style.display = 'none';
}

async function adjustCredits(userId) {
    const amount = prompt('Enter credit adjustment (positive or negative):');
    if (amount === null) return;
    
    const credits = parseFloat(amount);
    if (isNaN(credits)) {
        showNotification('Invalid amount', 'error');
        return;
    }
    
    const description = prompt('Reason for adjustment:') || 'Admin adjustment';
    
    try {
        const formData = new FormData();
        formData.append('amount', credits.toString());
        formData.append('description', description);
        
        const response = await fetch(`${API_URL}/admin/users/${userId}/credits`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to adjust credits');
        }
        
        showNotification('Credits adjusted successfully', 'success');
        closeAdminUserModal();
        loadAdminUsers();
    } catch (error) {
        console.error('Error adjusting credits:', error);
        showNotification('Failed to adjust credits', 'error');
    }
}

async function toggleUserActive(userId) {
    if (!confirm('Toggle user active status?')) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}/toggle-active`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to toggle user status');
        }
        
        showNotification('User status updated', 'success');
        closeAdminUserModal();
        loadAdminUsers();
    } catch (error) {
        console.error('Error toggling user status:', error);
        showNotification('Failed to update user status', 'error');
    }
}

async function archiveJob(jobId) {
    if (!confirm('Archive this job? This will delete the audio files but keep the record.')) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/jobs/${jobId}/archive`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to archive job');
        }
        
        showNotification('Job archived successfully', 'success');
        loadAdminJobs();
    } catch (error) {
        console.error('Error archiving job:', error);
        showNotification('Failed to archive job', 'error');
    }
}

async function deleteJob(jobId) {
    if (!confirm('Permanently delete this job? This cannot be undone!')) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/jobs/${jobId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete job');
        }
        
        showNotification('Job deleted successfully', 'success');
        loadAdminJobs();
    } catch (error) {
        console.error('Error deleting job:', error);
        showNotification('Failed to delete job', 'error');
    }
}

// Make admin functions globally available
window.viewAdminUser = viewAdminUser;
window.closeAdminUserModal = closeAdminUserModal;
window.adjustCredits = adjustCredits;
window.toggleUserActive = toggleUserActive;
window.archiveJob = archiveJob;
window.deleteJob = deleteJob;
