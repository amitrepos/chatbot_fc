# Default Admin User Setup

## Overview

The FlexCube chatbot system includes a default admin user that is created during initial setup. This admin user has full system access with all permissions.

## Default Admin Credentials

**⚠️ IMPORTANT: Change the default password after first login!**

- **Username:** `admin`
- **Email:** `admin@flexcube.local`
- **Password:** `Admin123!`
- **User Type:** `operational_admin`
- **Full Name:** System Administrator

## Creating the Default Admin User

### Method 1: Using the Seed Script (Recommended)

Run the seed script to create the default admin user:

```bash
cd /var/www/chatbot_FC
python3 scripts/seed_admin_user.py
```

The script will:
- Check if admin user already exists
- Create the admin user if it doesn't exist
- Assign all permissions via the `operational_admin` role template
- Display the credentials for reference

### Method 2: Manual Creation via API

If you prefer to create the admin user manually, you can use the registration endpoint (if available) or create it directly in the database.

## Converting Other Users to Admin

Once you're logged in as the default admin, you can convert any other user to an admin through the User Management interface:

### Steps:

1. **Log in** as the default admin user (`admin` / `Admin123!`)

2. **Navigate to User Management:**
   - Click the "👑 Admin" button in the top right corner
   - Select "👥 Users" from the admin menu
   - Or go directly to `/admin/users`

3. **Find the user** you want to convert:
   - Use the search box to find by username or email
   - Or browse the user list

4. **Edit the user:**
   - Click the "Edit" button next to the user
   - In the edit modal, change the "User Type" dropdown from "General User" to "Operational Admin"
   - Click "Save"

5. **Verify:**
   - The user's type should now show as "operational_admin" in the user list
   - The user will have all admin permissions and can access admin pages

### Alternative: Direct Database Update

If needed, you can also update the user type directly in the database:

```sql
UPDATE users 
SET user_type = 'operational_admin' 
WHERE username = 'target_username';
```

Then assign the role template:

```python
# Run in Python shell or script
from src.database.database import get_db
from src.database.crud import assign_role_template_to_user

db = next(get_db())
assign_role_template_to_user(db, user_id, 'operational_admin')
```

## Admin Permissions

The `operational_admin` user type has access to all system features:

- ✅ View Admin Dashboard
- ✅ Manage Users (create, edit, deactivate)
- ✅ View Analytics
- ✅ Export Training Data
- ✅ Manage System Settings
- ✅ All chat and document features

## Security Notes

1. **Change Default Password:** Always change the default admin password after first login
2. **Limit Admin Access:** Only grant admin privileges to trusted users
3. **Regular Audits:** Periodically review admin users and their activity
4. **Strong Passwords:** Ensure all admin users have strong passwords

## Troubleshooting

### Admin User Not Created

If the seed script fails:
1. Check database connection settings
2. Verify database tables are created (run `create_tables.sql`)
3. Check that role templates are seeded
4. Review error logs

### Cannot Log In as Admin

1. Verify the user exists: `SELECT * FROM users WHERE username = 'admin';`
2. Check if user is active: `SELECT is_active FROM users WHERE username = 'admin';`
3. Verify password hash is correct (re-run seed script if needed)
4. Check application logs for authentication errors

### User Not Getting Admin Permissions

1. Verify user_type is set to `operational_admin`
2. Check if role template is assigned: `SELECT * FROM role_template_permissions WHERE role_template_id = (SELECT id FROM role_templates WHERE name = 'operational_admin');`
3. Verify permissions are granted: `SELECT * FROM user_permissions WHERE user_id = <user_id>;`

## Related Files

- Seed script: `scripts/seed_admin_user.py`
- Database schema: `scripts/create_tables.sql`
- User management UI: `/admin/users`
- CRUD operations: `src/database/crud.py`

