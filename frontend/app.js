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
    purchase: document.getElementById('purchase-page')
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
        document.getElementById('user-email').textContent = currentUser.email;
        const credits = currentUser.credits.toFixed(1);
        document.getElementById('header-credits').textContent = credits;
        document.getElementById('header-credits-purchase').textContent = credits;
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
        document.getElementById('user-email-purchase').textContent = currentUser.email;
        document.getElementById('header-credits-purchase').textContent = currentUser.credits.toFixed(1);
    }
}

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
            const hasProcessingJobs = jobs.some(job => 
                job.status.toUpperCase() === 'PENDING' || job.status.toUpperCase() === 'PROCESSING'
            );

            // Start or stop polling based on job status
            if (hasProcessingJobs) {
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

            jobs.forEach(job => {
                const existingRow = existingRows.get(job.id);
                const statusClass = `status-${job.status.toLowerCase()}`;
                
                // Add visual indicator for processing jobs
                let statusBadge = `<span class="status-badge ${statusClass}">${job.status}</span>`;
                if (job.status.toUpperCase() === 'PROCESSING') {
                    statusBadge += ' <span style="animation: pulse 1.5s infinite;">⏳</span>';
                }
                
                const rowHTML = `
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

                if (existingRow) {
                    // Only update if status changed
                    const currentStatus = existingRow.getAttribute('data-status');
                    if (currentStatus !== job.status) {
                        existingRow.innerHTML = rowHTML;
                        existingRow.setAttribute('data-status', job.status);
                        
                        // If job just completed, add the details row
                        if (job.status.toUpperCase() === 'COMPLETED' && !document.getElementById(`job-details-${job.id}`)) {
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
                            existingRow.insertAdjacentElement('afterend', detailsRow);
                        }
                    }
                    existingRows.delete(job.id);
                } else {
                    // New job - add it
                    const row = document.createElement('tr');
                    row.setAttribute('data-job-id', job.id);
                    row.setAttribute('data-status', job.status);
                    row.innerHTML = rowHTML;
                    tbody.insertBefore(row, tbody.firstChild);
                    
                    // Add expandable row for stems if completed
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

            // Remove any jobs that no longer exist
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

// Start automatic job status polling
function startJobPolling() {
    // Don't start if already polling
    if (jobPollingInterval) {
        return;
    }
    
    console.log('Starting job status polling...');
    jobPollingInterval = setInterval(async () => {
        // Only poll if we're on the dashboard page
        const dashboardPage = document.getElementById('dashboard-page');
        if (dashboardPage && dashboardPage.style.display !== 'none') {
            await loadJobList();
        }
    }, 5000); // Poll every 5 seconds
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
    
    // Toggle visibility
    if (detailsRow.style.display === 'none') {
        detailsRow.style.display = 'table-row';
        
        // Load stems if not already loaded
        if (stemsDiv.innerHTML.includes('Loading stems')) {
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
    } else {
        detailsRow.style.display = 'none';
    }
};

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
async function initializeSquarePayments() {
    try {
        const response = await fetch(`${API_URL}/credits/square-config`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (!response.ok) {
            throw new Error('Square not configured');
        }
        
        const config = await response.json();
        
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
    
    // Check URL path to determine which page to show
    const path = window.location.pathname;
    let targetPage = 'dashboard';
    
    if (path === '/purchase' || path === '/credits') {
        targetPage = 'purchase';
    } else if (path === '/dashboard') {
        targetPage = 'dashboard';
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
