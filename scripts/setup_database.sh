#!/bin/bash
# Database Setup Script for Phase 7
# Creates PostgreSQL database and user for FlexCube chatbot

set -e

DB_NAME="flexcube_chatbot"
DB_USER="chatbot_user"
DB_PASSWORD="${CHATBOT_DB_PASSWORD:-chatbot_pass_$(openssl rand -hex 8)}"

echo "=========================================="
echo "FlexCube Chatbot - Database Setup"
echo "=========================================="
echo ""

# Use PostgreSQL 16 psql directly
PSQL_BIN="/usr/pgsql-16/bin/psql"

# Check if running as root or postgres user
if [ "$EUID" -eq 0 ]; then
    PSQL_CMD="sudo -u postgres $PSQL_BIN"
elif [ "$USER" == "postgres" ]; then
    PSQL_CMD="$PSQL_BIN"
else
    PSQL_CMD="sudo -u postgres $PSQL_BIN"
fi

echo "Step 1: Creating database user (if not exists)..."
$PSQL_CMD <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'User $DB_USER created';
    ELSE
        RAISE NOTICE 'User $DB_USER already exists - skipping';
    END IF;
END
\$\$;
EOF

echo "Step 2: Creating database (if not exists)..."
$PSQL_CMD <<EOF
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
EOF

# Verify database was created or already exists
DB_EXISTS=$($PSQL_CMD -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
if [ -z "$DB_EXISTS" ]; then
    echo "❌ Error: Database $DB_NAME was not created"
    exit 1
else
    echo "✅ Database $DB_NAME exists"
fi

echo "Step 3: Granting privileges (only to $DB_USER on $DB_NAME)..."
$PSQL_CMD -d $DB_NAME <<EOF
-- Grant privileges ONLY to chatbot_user on flexcube_chatbot database
-- This will NOT affect any other databases or users
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo ""
echo "=========================================="
echo "✅ Database setup complete!"
echo "=========================================="
echo ""
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"
echo ""
echo "Connection string:"
echo "postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "⚠️  Save this password! You'll need it for DATABASE_URL environment variable."
echo ""

