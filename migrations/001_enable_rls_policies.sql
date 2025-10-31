-- Migration 001: Enable Row Level Security (RLS) Policies
-- This migration creates comprehensive RLS policies for all tables
-- Frontend can only SELECT, backend (service role) can do all operations

-- ============================================================================
-- TABLE: encrypted_search_history
-- ============================================================================

-- Enable RLS
ALTER TABLE encrypted_search_history ENABLE ROW LEVEL SECURITY;

-- Policy 1: Users can read their own search history
CREATE POLICY "users_read_own_searches"
ON encrypted_search_history
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 2: Users CANNOT insert/update/delete (backend only)
-- Service role bypasses RLS, so only backend can write

-- Drop any existing permissive policies
DROP POLICY IF EXISTS "users_insert_own_searches" ON encrypted_search_history;
DROP POLICY IF EXISTS "users_update_own_searches" ON encrypted_search_history;
DROP POLICY IF EXISTS "users_delete_own_searches" ON encrypted_search_history;

-- ============================================================================
-- TABLE: user_subscriptions
-- ============================================================================

-- Enable RLS
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy 1: Users can read their own subscription
CREATE POLICY "users_read_own_subscription"
ON user_subscriptions
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 2: Users CANNOT update/delete subscription (backend only)
DROP POLICY IF EXISTS "users_update_own_subscription" ON user_subscriptions;
DROP POLICY IF EXISTS "users_delete_own_subscription" ON user_subscriptions;

-- ============================================================================
-- TABLE: user_payments
-- ============================================================================

-- Enable RLS
ALTER TABLE user_payments ENABLE ROW LEVEL SECURITY;

-- Policy 1: Users can read their own payment history
CREATE POLICY "users_read_own_payments"
ON user_payments
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy 2: Users CANNOT insert/update/delete payments (backend only)
DROP POLICY IF EXISTS "users_insert_payments" ON user_payments;
DROP POLICY IF EXISTS "users_update_payments" ON user_payments;
DROP POLICY IF EXISTS "users_delete_payments" ON user_payments;

-- ============================================================================
-- TABLE: lemon_squeezy_webhooks
-- ============================================================================

-- Enable RLS
ALTER TABLE lemon_squeezy_webhooks ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can access webhooks (backend only)
-- No user access at all
CREATE POLICY "service_role_only"
ON lemon_squeezy_webhooks
FOR ALL
TO service_role
USING (true);

-- ============================================================================
-- TABLE: agent_progress (if exists)
-- ============================================================================

-- Create table if not exists
CREATE TABLE IF NOT EXISTS agent_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    data JSONB,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (search_id) REFERENCES encrypted_search_history(id) ON DELETE CASCADE
);

-- Enable RLS
ALTER TABLE agent_progress ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read progress for their own searches
CREATE POLICY "users_read_own_progress"
ON agent_progress
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM encrypted_search_history
        WHERE encrypted_search_history.id = agent_progress.search_id
        AND encrypted_search_history.user_id = auth.uid()
    )
);

-- ============================================================================
-- VERIFICATION FUNCTION
-- ============================================================================

-- Function to verify RLS is enabled and policies are correct
CREATE OR REPLACE FUNCTION validate_rls_policies()
RETURNS TABLE (
    table_name TEXT,
    rls_enabled BOOLEAN,
    policy_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.relname::TEXT as table_name,
        c.relrowsecurity as rls_enabled,
        COUNT(p.polname)::INTEGER as policy_count
    FROM pg_class c
    LEFT JOIN pg_policy p ON p.polrelid = c.oid
    WHERE c.relname IN (
        'encrypted_search_history',
        'user_subscriptions', 
        'user_payments',
        'lemon_squeezy_webhooks',
        'agent_progress'
    )
    GROUP BY c.relname, c.relrowsecurity
    ORDER BY c.relname;
END;
$$ LANGUAGE plpgsql;

-- Run verification
SELECT * FROM validate_rls_policies();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON POLICY "users_read_own_searches" ON encrypted_search_history IS 
    'Users can only read their own search history';

COMMENT ON POLICY "users_read_own_subscription" ON user_subscriptions IS 
    'Users can only read their own subscription data';

COMMENT ON POLICY "users_read_own_payments" ON user_payments IS 
    'Users can only read their own payment history';

COMMENT ON POLICY "service_role_only" ON lemon_squeezy_webhooks IS 
    'Only backend (service role) can access webhook logs';

COMMENT ON POLICY "users_read_own_progress" ON agent_progress IS 
    'Users can read agent progress for their own searches';

-- ============================================================================
-- EXPECTED OUTPUT
-- ============================================================================

/*
Expected validation results:
+---------------------------+-------------+--------------+
| table_name                | rls_enabled | policy_count |
+---------------------------+-------------+--------------+
| agent_progress            | true        | 1            |
| encrypted_search_history  | true        | 1            |
| lemon_squeezy_webhooks    | true        | 1            |
| user_payments             | true        | 1            |
| user_subscriptions        | true        | 1            |
+---------------------------+-------------+--------------+

Security Model:
✅ Frontend (anon key): Can only SELECT own data
✅ Backend (service role): Can do ALL operations (bypasses RLS)
✅ Webhooks: Only backend can access
✅ Quota: Only backend can modify
✅ History: Only backend can write
*/
