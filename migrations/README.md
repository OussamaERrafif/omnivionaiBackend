# Database Migrations

This directory contains SQL migration files for implementing security features.

## Overview

These migrations implement the complete security architecture including:
- Row Level Security (RLS) policies
- Atomic quota operations
- Security auditing
- Performance indexes

## Migration Files

### 001_enable_rls_policies.sql
**Purpose:** Enable Row Level Security on all tables

**What it does:**
- Enables RLS on `encrypted_search_history`
- Enables RLS on `user_subscriptions`
- Enables RLS on `user_payments`
- Enables RLS on `lemon_squeezy_webhooks`
- Creates `agent_progress` table with RLS
- Creates validation function

**Security Model:**
- ✅ Frontend (anon key): Can only SELECT own data
- ✅ Backend (service role): Can do ALL operations (bypasses RLS)
- ✅ Users isolated: Cannot see other users' data

### 002_security_audit.sql
**Purpose:** Security validation and performance optimization

**What it does:**
- Creates `security_audit()` function to verify RLS setup
- Creates performance indexes on all tables
- Creates security event logging function
- Validates all security policies

**Indexes created:**
- `idx_search_history_user_id` - Fast user filtering
- `idx_search_history_created_at` - Time-based sorting
- `idx_search_history_user_created` - Composite index
- `idx_user_subscriptions_user_id` - Subscription lookups
- `idx_webhooks_event_id` - Webhook deduplication

### 004_atomic_quota_functions.sql
**Purpose:** Atomic quota operations (prevent race conditions)

**What it does:**
- Creates `decrement_search_quota()` - Atomic quota check + decrement
- Creates `refund_search_quota()` - Atomic quota refund
- Creates `get_quota_status()` - Read quota information
- Creates `reset_monthly_quota()` - Monthly quota reset

**Features:**
- ✅ Row-level locking (FOR UPDATE)
- ✅ Prevents race conditions
- ✅ Atomic operations
- ✅ No negative quotas possible

## How to Apply Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy and paste migration content
5. Run the query
6. Verify success

**Order:**
```
1. 001_enable_rls_policies.sql
2. 002_security_audit.sql
3. 004_atomic_quota_functions.sql
```

### Option 2: Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link your project
supabase link --project-ref your-project-ref

# Apply migrations
supabase db push

# Or apply individually
psql $DATABASE_URL -f migrations/001_enable_rls_policies.sql
psql $DATABASE_URL -f migrations/002_security_audit.sql
psql $DATABASE_URL -f migrations/004_atomic_quota_functions.sql
```

### Option 3: Direct psql

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Apply migrations in order
psql $DATABASE_URL -f migrations/001_enable_rls_policies.sql
psql $DATABASE_URL -f migrations/002_security_audit.sql
psql $DATABASE_URL -f migrations/004_atomic_quota_functions.sql
```

## Verification

After applying migrations, run these checks:

### 1. Verify RLS is enabled

```sql
SELECT * FROM validate_rls_policies();
```

Expected output:
```
table_name               | rls_enabled | policy_count
-------------------------|-------------|-------------
agent_progress           | true        | 1
encrypted_search_history | true        | 1
lemon_squeezy_webhooks   | true        | 1
user_payments            | true        | 1
user_subscriptions       | true        | 1
```

### 2. Run security audit

```sql
SELECT * FROM security_audit();
```

All checks should show `PASS` status.

### 3. Test quota functions

```sql
-- Replace 'your-user-uuid' with actual user ID
SELECT * FROM get_quota_status('your-user-uuid');
SELECT * FROM decrement_search_quota('your-user-uuid');
SELECT * FROM refund_search_quota('your-user-uuid');
```

### 4. Test RLS enforcement

Try to insert as authenticated user (should fail):

```sql
-- This should return 403 Forbidden or 0 rows affected
INSERT INTO encrypted_search_history (user_id, query)
VALUES ('some-user-id', 'test query');
```

## Rollback (if needed)

If you need to rollback migrations:

```sql
-- Disable RLS
ALTER TABLE encrypted_search_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_payments DISABLE ROW LEVEL SECURITY;
ALTER TABLE lemon_squeezy_webhooks DISABLE ROW LEVEL SECURITY;

-- Drop policies
DROP POLICY IF EXISTS "users_read_own_searches" ON encrypted_search_history;
DROP POLICY IF EXISTS "users_read_own_subscription" ON user_subscriptions;
DROP POLICY IF EXISTS "users_read_own_payments" ON user_payments;
DROP POLICY IF EXISTS "service_role_only" ON lemon_squeezy_webhooks;

-- Drop functions
DROP FUNCTION IF EXISTS decrement_search_quota(UUID);
DROP FUNCTION IF EXISTS refund_search_quota(UUID);
DROP FUNCTION IF EXISTS get_quota_status(UUID);
DROP FUNCTION IF EXISTS reset_monthly_quota();
DROP FUNCTION IF EXISTS validate_rls_policies();
DROP FUNCTION IF EXISTS security_audit();
```

## Troubleshooting

### Issue: "relation does not exist"

**Cause:** Table hasn't been created yet

**Solution:** Create the table first:
```sql
CREATE TABLE encrypted_search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    results JSONB,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Issue: "permission denied for table"

**Cause:** Using wrong key (anon instead of service_role)

**Solution:** Make sure you're using the service_role key when applying migrations

### Issue: "function already exists"

**Cause:** Migration already applied

**Solution:** Use `CREATE OR REPLACE FUNCTION` or skip

## Monitoring

Set up monitoring for:

1. **RLS Policy Violations**
   ```sql
   -- Check logs for RLS denials
   SELECT * FROM security_audit_log 
   WHERE event_type = 'rls_violation'
   ORDER BY created_at DESC LIMIT 100;
   ```

2. **Quota Operations**
   ```sql
   -- Monitor quota usage
   SELECT 
       plan_type,
       AVG(searches_remaining) as avg_remaining,
       COUNT(*) as user_count
   FROM user_subscriptions
   GROUP BY plan_type;
   ```

3. **Performance**
   ```sql
   -- Check index usage
   SELECT 
       schemaname,
       tablename,
       indexname,
       idx_scan
   FROM pg_stat_user_indexes
   WHERE tablename LIKE '%search%'
   ORDER BY idx_scan DESC;
   ```

## Maintenance

### Monthly Quota Reset

Set up a cron job to reset quotas:

```sql
-- Run on 1st of each month
SELECT * FROM reset_monthly_quota();
```

### Index Maintenance

```sql
-- Reindex for performance (run weekly)
REINDEX TABLE encrypted_search_history;
REINDEX TABLE user_subscriptions;
```

## Security Checklist

After applying migrations, verify:

- [ ] RLS enabled on all tables
- [ ] Policies created correctly
- [ ] Frontend cannot write to database
- [ ] Backend can write with service_role
- [ ] Quota functions work atomically
- [ ] Indexes created for performance
- [ ] Security audit passes
- [ ] No public write policies exist

## Support

If you encounter issues:

1. Check Supabase logs in dashboard
2. Run `SELECT * FROM security_audit();`
3. Verify environment variables are set
4. Check that service_role key is used for migrations
5. Review Supabase documentation: https://supabase.com/docs/guides/auth/row-level-security
