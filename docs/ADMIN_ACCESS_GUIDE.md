# Admin Section Access Guide

## How to Access Admin Section

### Method 1: Via Admin Link (Recommended)

1. **Log in** as admin user:
   - Username: `admin`
   - Password: `Admin123!`
   - Go to `/login`

2. **After login**, you should see:
   - Your username in the top right corner
   - A "👑 Admin" button next to your username
   - Click the "👑 Admin" button to go to `/admin/dashboard`

3. **If the Admin button doesn't appear:**
   - Refresh the page (F5 or Ctrl+R)
   - The system will automatically refresh your user info from the API
   - The Admin button should appear after refresh

### Method 2: Direct URL Access

You can also access admin pages directly:

- **Admin Dashboard:** `/admin/dashboard`
- **User Management:** `/admin/users`
- **Analytics:** `/admin/analytics`
- **Training Data Export:** `/admin/training-data`
- **System Settings:** `/admin/settings`

**Note:** You must be logged in as an admin user. If you're not logged in or don't have admin permissions, you'll be redirected to the login page or see a 403 Forbidden error.

## Admin Navigation

Once you're in any admin page, you'll see a navigation bar at the top with links to:
- 🏠 Home - Return to main chat interface
- 📈 Dashboard - Admin dashboard
- 👥 Users - User management
- 📊 Analytics - System analytics
- 📥 Export - Training data export
- ⚙️ Settings - System settings
- 🚪 Logout - Log out

## Troubleshooting

### Admin Button Not Showing

**Problem:** After logging in as admin, the "👑 Admin" button doesn't appear.

**Solutions:**
1. **Refresh the page** - The system will automatically fetch your permissions from the API
2. **Check browser console** - Open Developer Tools (F12) and check for JavaScript errors
3. **Clear localStorage and re-login:**
   ```javascript
   localStorage.clear();
   window.location.href = '/login';
   ```
4. **Verify you're logged in as admin:**
   - Check the user info in browser console: `JSON.parse(localStorage.getItem('user_info'))`
   - Should show `user_type: "operational_admin"` and `permissions` array with admin permissions

### 403 Forbidden Error

**Problem:** You get a 403 error when accessing admin pages.

**Solutions:**
1. **Verify admin user exists:**
   ```bash
   python3 scripts/seed_admin_user.py
   ```
2. **Check user permissions in database:**
   ```sql
   SELECT u.username, u.user_type, p.name 
   FROM users u
   LEFT JOIN user_permissions up ON u.id = up.user_id
   LEFT JOIN permissions p ON up.permission_id = p.id
   WHERE u.username = 'admin';
   ```
3. **Re-assign role template:**
   ```python
   from src.database.database import get_db
   from src.database.crud import assign_role_template_to_user, get_user_by_username
   
   db = next(get_db())
   user = get_user_by_username(db, 'admin')
   assign_role_template_to_user(db, user.id, 'operational_admin')
   ```

### Permissions Not Loading

**Problem:** User info doesn't include permissions array.

**Solutions:**
1. **Log out and log back in** - This will fetch fresh user info with permissions
2. **Use the refresh function** - The page automatically refreshes user info if permissions are missing
3. **Check API response:**
   - Open Network tab in Developer Tools
   - Check `/api/auth/login` response
   - Verify `user.permissions` array is present

## Testing Admin Access

### Integration Tests

Run the admin endpoint integration tests:

```bash
cd /var/www/chatbot_FC
source venv/bin/activate
python -m pytest src/tests/integration/test_admin_endpoints.py -v
```

**Expected:** All 19 tests should pass:
- ✅ Authentication requirements
- ✅ Permission requirements
- ✅ Admin dashboard functionality
- ✅ User management operations
- ✅ Analytics endpoints
- ✅ Training data export
- ✅ System settings
- ✅ Permission management

### Manual Testing Checklist

- [ ] Can log in as admin user
- [ ] Admin button appears in top right after login
- [ ] Can access `/admin/dashboard`
- [ ] Can access `/admin/users`
- [ ] Can view user list
- [ ] Can create new user
- [ ] Can edit user (including converting to admin)
- [ ] Can deactivate user
- [ ] Can access `/admin/analytics`
- [ ] Can access `/admin/training-data`
- [ ] Can export training data
- [ ] Can access `/admin/settings`
- [ ] Can update system settings

## Converting Users to Admin

1. Log in as admin
2. Go to `/admin/users`
3. Find the user you want to convert
4. Click "Edit" button
5. Change "User Type" from "General User" to "Operational Admin"
6. Click "Save"
7. User will immediately have admin access

## Security Notes

- Admin pages require authentication (JWT token)
- Admin pages require `view_admin_dashboard` permission or `operational_admin` user type
- All admin API endpoints are protected with permission checks
- General users cannot access admin pages (403 Forbidden)




