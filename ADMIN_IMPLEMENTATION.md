# Admin Page Implementation Progress

## Completed Backend Changes ✅

1. **Database Models** (`backend/models.py`)
   - Added `is_admin` field to User model (0 = regular, 1 = admin)
   - Added `active` field to User model (0 = disabled, 1 = active)
   - Added `archived` field to Job model (0 = active, 1 = archived/files deleted)

2. **Authentication** (`backend/auth.py`)
   - Updated `get_current_user()` to check if user account is active
   - Disabled accounts return 403 Forbidden error

3. **Admin Endpoints** (`backend/main.py`)
   - `GET /admin/users` - List all users with summary info
   - `GET /admin/users/{user_id}` - Get detailed user info (jobs, transactions)
   - `POST /admin/users/{user_id}/credits` - Add/subtract credits from user
   - `POST /admin/users/{user_id}/toggle-active` - Enable/disable user account
   - `GET /admin/jobs` - List all jobs across all users
   - `POST /admin/jobs/{job_id}/archive` - Archive job (delete files, keep record)
   - `DELETE /admin/jobs/{job_id}` - Completely delete job and files
   - Added `get_admin_user()` dependency that verifies admin access
   - Updated catch-all route to exclude `admin/` paths

## TODO: Frontend Changes

### 1. Create Admin Page HTML (`frontend/index.html`)
Add admin page after purchase-page:

```html
<!-- Admin Page -->
<div id="admin-page" class="page">
    <div class="dashboard-header">
        <h1 class="clickable-logo" onclick="goHome()"><span class="logo">🎚️</span> Mux Minus</h1>
        <div class="user-info">
            <h2>Admin Panel</h2>
            <p id="admin-user-email">admin@example.com</p>
        </div>
    </div>

    <div class="nav-buttons">
        <button id="nav-admin-users" class="nav-btn active">Users</button>
        <button id="nav-admin-jobs" class="nav-btn">All Jobs</button>
        <button id="nav-admin-dashboard" class="nav-btn">Dashboard</button>
        <button id="nav-admin-logout" class="nav-btn">Logout</button>
    </div>

    <!-- Users Tab -->
    <div id="admin-users-tab" class="admin-tab">
        <div class="dashboard-card">
            <h3>👥 User Management</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Credits</th>
                        <th>Jobs</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="admin-user-list">
                    <tr><td colspan="7" style="text-align: center; color: #999;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Jobs Tab -->
    <div id="admin-jobs-tab" class="admin-tab" style="display: none;">
        <div class="dashboard-card">
            <h3>🎵 All Jobs</h3>
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>User</th>
                        <th>File</th>
                        <th>Status</th>
                        <th>Date</th>
                        <th>Archived</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="admin-job-list">
                    <tr><td colspan="7" style="text-align: center; color: #999;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Admin User Detail Modal -->
<div id="admin-user-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h2 id="modal-user-title">User Details</h2>
            <button class="modal-close" onclick="closeAdminUserModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div id="admin-user-details">Loading...</div>
        </div>
    </div>
</div>
```

### 2. Update JavaScript (`frontend/app.js`)

#### Add admin page to pages object:
```javascript
const pages = {
    landing: document.getElementById('landing-page'),
    login: document.getElementById('login-page'),
    register: document.getElementById('register-page'),
    dashboard: document.getElementById('dashboard-page'),
    purchase: document.getElementById('purchase-page'),
    admin: document.getElementById('admin-page')
};
```

#### Add admin check to currentUser:
```javascript
let currentUser = null; // Add is_admin property when loaded
```

#### Update showPage function to handle /admin route:
```javascript
else if (pageName === 'admin') {
    path = '/admin';
}
```

#### Add admin page loading:
```javascript
async function loadAdminPage() {
    if (!currentUser.is_admin) {
        showPage('dashboard');
        return;
    }
    
    // Load users by default
    await loadAdminUsers();
}

async function loadAdminUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const tbody = document.getElementById('admin-user-list');
            tbody.innerHTML = '';
            
            data.users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.id}</td>
                    <td>${user.username}${user.is_admin ? ' <span style="color: #667eea;">👑</span>' : ''}</td>
                    <td>${user.email}</td>
                    <td>${user.credits.toFixed(1)}</td>
                    <td>${user.job_count}</td>
                    <td>${user.active ? '<span class="status-badge status-completed">Active</span>' : '<span class="status-badge status-failed">Disabled</span>'}</td>
                    <td>
                        <button onclick="viewAdminUser(${user.id})" class="btn-download">View</button>
                        ${!user.is_admin ? `<button onclick="toggleUserActive(${user.id}, ${user.active})" class="btn-refresh">${user.active ? 'Disable' : 'Enable'}</button>` : ''}
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

async function loadAdminJobs() {
    try {
        const response = await fetch(`${API_URL}/admin/jobs`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const tbody = document.getElementById('admin-job-list');
            tbody.innerHTML = '';
            
            data.jobs.forEach(job => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${job.id.substring(0, 8)}...</td>
                    <td>${job.username}</td>
                    <td>${job.filename}</td>
                    <td><span class="status-badge status-${job.status}">${job.status}</span></td>
                    <td>${new Date(job.created_at).toLocaleString()}</td>
                    <td>${job.archived ? '✓' : ''}</td>
                    <td>
                        ${!job.archived ? `<button onclick="archiveJob('${job.id}')" class="btn-refresh">Archive</button>` : ''}
                        <button onclick="deleteJob('${job.id}')" class="btn-download" style="background: #ef4444;">Delete</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load jobs:', error);
    }
}

window.viewAdminUser = async function(userId) {
    // Fetch detailed user info and show modal
    const response = await fetch(`${API_URL}/admin/users/${userId}`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.ok) {
        const user = await response.json();
        const modal = document.getElementById('admin-user-modal');
        const details = document.getElementById('admin-user-details');
        
        details.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h3>${user.username} (${user.email})</h3>
                <p>Credits: ${user.credits.toFixed(1)}</p>
                <p>Status: ${user.active ? 'Active' : 'Disabled'}</p>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <input type="number" id="credit-adjustment" placeholder="Amount" step="0.1" style="padding: 8px;">
                    <button onclick="adjustCredits(${user.id})" class="btn">Adjust Credits</button>
                </div>
            </div>
            
            <h4>Recent Jobs</h4>
            <ul>
                ${user.jobs.map(job => `<li>${job.filename} - ${job.status} (${new Date(job.created_at).toLocaleString()})</li>`).join('')}
            </ul>
            
            <h4>Transactions</h4>
            <ul>
                ${user.transactions.map(tx => `<li>${tx.description}: ${tx.amount > 0 ? '+' : ''}${tx.amount} (Balance: ${tx.balance_after})</li>`).join('')}
            </ul>
        `;
        
        modal.style.display = 'flex';
    }
};

window.closeAdminUserModal = function() {
    document.getElementById('admin-user-modal').style.display = 'none';
};

window.adjustCredits = async function(userId) {
    const amount = parseFloat(document.getElementById('credit-adjustment').value);
    if (isNaN(amount)) return;
    
    const formData = new FormData();
    formData.append('amount', amount);
    formData.append('description', 'Admin adjustment');
    
    const response = await fetch(`${API_URL}/admin/users/${userId}/credits`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` },
        body: formData
    });
    
    if (response.ok) {
        showNotification('Credits adjusted successfully', 'success');
        closeAdminUserModal();
        loadAdminUsers();
    }
};

window.toggleUserActive = async function(userId, currentActive) {
    const response = await fetch(`${API_URL}/admin/users/${userId}/toggle-active`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.ok) {
        showNotification(`User ${currentActive ? 'disabled' : 'enabled'} successfully`, 'success');
        loadAdminUsers();
    }
};

window.archiveJob = async function(jobId) {
    if (!confirm('Archive this job? Files will be deleted but record will remain.')) return;
    
    const response = await fetch(`${API_URL}/admin/jobs/${jobId}/archive`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.ok) {
        showNotification('Job archived successfully', 'success');
        loadAdminJobs();
    }
};

window.deleteJob = async function(jobId) {
    if (!confirm('Permanently delete this job? This cannot be undone!')) return;
    
    const response = await fetch(`${API_URL}/admin/jobs/${jobId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    
    if (response.ok) {
        showNotification('Job deleted successfully', 'success');
        loadAdminJobs();
    }
};
```

#### Add admin tab switching:
```javascript
document.getElementById('nav-admin-users').addEventListener('click', () => {
    document.querySelectorAll('.admin-tab').forEach(tab => tab.style.display = 'none');
    document.getElementById('admin-users-tab').style.display = 'block';
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('nav-admin-users').classList.add('active');
    loadAdminUsers();
});

document.getElementById('nav-admin-jobs').addEventListener('click', () => {
    document.querySelectorAll('.admin-tab').forEach(tab => tab.style.display = 'none');
    document.getElementById('admin-jobs-tab').style.display = 'block';
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('nav-admin-jobs').classList.add('active');
    loadAdminJobs();
});

document.getElementById('nav-admin-dashboard').addEventListener('click', () => {
    showPage('dashboard');
    loadDashboard();
});

document.getElementById('nav-admin-logout').addEventListener('click', logout);
```

#### Update dashboard to show Admin link if user is admin:
```javascript
// In loadDashboard() function, check if user is admin and show link
if (currentUser.is_admin) {
    // Add admin button to nav-buttons
}
```

### 3. Add CSS Styles (`frontend/styles.css`)

```css
/* Admin Page */
.admin-tab {
    display: block;
}

.nav-btn.active {
    background: var(--primary);
    color: white;
}
```

## Database Migration Required

After deploying these changes, you'll need to update the database schema:

```sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1 NOT NULL;

-- Add new column to jobs table
ALTER TABLE jobs ADD COLUMN archived INTEGER DEFAULT 0 NOT NULL;

-- Create your first admin user (replace user_id with your ID)
UPDATE users SET is_admin = 1 WHERE id = 1;
```

## Testing Checklist

1. ✅ Backend endpoints return correct data
2. ⬜ Admin page loads for admin users
3. ⬜ Non-admin users cannot access admin endpoints
4. ⬜ Can view all users and their details
5. ⬜ Can adjust user credits
6. ⬜ Can enable/disable user accounts
7. ⬜ Can view all jobs
8. ⬜ Can archive jobs (files deleted, record remains)
9. ⬜ Can delete jobs completely
10. ⬜ Disabled users cannot log in
11. ⬜ Admin navigation works correctly

## Security Notes

- Admin endpoints check `is_admin` flag before allowing access
- Cannot disable admin accounts via toggle
- Disabled users receive 403 Forbidden on auth check
- All admin actions are logged via transactions where applicable
