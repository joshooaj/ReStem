# Admin System Documentation

## Overview

The admin system provides administrative capabilities for managing users, credits, and jobs.

## Setup

### 1. Run Database Migration

Before using the admin system, run the migration script to add required database columns:

```bash
cd backend
python migrate_admin.py
```

This will:
- Add `is_admin` column to users table (0=regular user, 1=admin)
- Add `active` column to users table (0=disabled, 1=active)
- Add `archived` column to jobs table (0=active, 1=archived)
- Set the first user (ID=1) as admin

### 2. Make a User Admin

If you need to make a different user an admin, use psql or another database tool:

```sql
UPDATE users SET is_admin = 1 WHERE email = 'admin@example.com';
```

## Features

### User Management

Admin users can:
- View all registered users
- View detailed user information including:
  - Basic account details
  - Credit balance and transaction history
  - Job history
- Adjust user credits (add or subtract)
- Enable/disable user accounts

### Job Management

Admin users can:
- View all jobs across all users
- Archive jobs (deletes audio files but keeps record)
- Permanently delete jobs

### Access Control

- Admin endpoints require authentication
- Only users with `is_admin = 1` can access admin features
- Disabled users (`active = 0`) cannot log in

## API Endpoints

All admin endpoints require the `Authorization: Bearer <token>` header and admin privileges.

### User Management

- `GET /admin/users` - List all users
- `GET /admin/users/{user_id}` - Get detailed user info
- `POST /admin/users/{user_id}/credits` - Adjust user credits
  ```json
  {
    "amount": 10,
    "reason": "Bonus credits"
  }
  ```
- `POST /admin/users/{user_id}/toggle-active` - Enable/disable user account

### Job Management

- `GET /admin/jobs` - List all jobs
- `POST /admin/jobs/{job_id}/archive` - Archive job (delete files, keep record)
- `DELETE /admin/jobs/{job_id}` - Permanently delete job

## Frontend Access

### Admin Page

Admin users will see an "Admin" button in the dashboard header. Clicking it opens the admin panel at `/admin`.

The admin panel has two tabs:
1. **Users** - Manage users and credits
2. **All Jobs** - View and manage all jobs

### User Actions

From the Users tab:
1. Click "View" to see detailed user information
2. In the detail modal:
   - Click "Adjust Credits" to add/subtract credits
   - Click "Toggle Active" to enable/disable the account

### Job Actions

From the All Jobs tab:
- Click "Archive" to delete audio files but keep the record
- Click "Delete" to permanently remove the job

## Security Notes

- Admin status is stored in the database (not in JWT)
- Each admin request is validated server-side
- Disabled users cannot authenticate
- Admin actions are logged (credit adjustments, etc.)

## Testing

1. Create a test user account
2. Run the migration script
3. Log in with user ID 1 (now admin)
4. Navigate to `/admin`
5. Test user and job management features
