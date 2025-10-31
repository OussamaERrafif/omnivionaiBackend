-- Migration 002: Security Audit and Validation
-- This migration performs comprehensive security checks

-- ============================================================================
-- SECURITY AUDIT FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION security_audit()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
DECLARE
    v_table_name TEXT;
    v_rls_enabled BOOLEAN;
    v_policy_count INTEGER;
BEGIN
    -- Check 1: Verify RLS is enabled on all tables
    FOR v_table_name, v_rls_enabled IN
        SELECT c.relname::TEXT, c.relrowsecurity
        FROM pg_class c
        WHERE c.relname IN (
            'encrypted_search_history',
            'user_subscriptions',
            'user_payments',
            'lemon_squeezy_webhooks'
        )
    LOOP
        IF v_rls_enabled THEN
            RETURN QUERY SELECT 
                'RLS_ENABLED'::TEXT,
                'PASS'::TEXT,
                format('Table %s has RLS enabled', v_table_name)::TEXT;
        ELSE
            RETURN QUERY SELECT 
                'RLS_ENABLED'::TEXT,
                'FAIL'::TEXT,
                format('Table %s does NOT have RLS enabled', v_table_name)::TEXT;
        END IF;
    END LOOP;

    -- Check 2: Verify policies exist
    FOR v_table_name, v_policy_count IN
        SELECT c.relname::TEXT, COUNT(p.polname)::INTEGER
        FROM pg_class c
        LEFT JOIN pg_policy p ON p.polrelid = c.oid
        WHERE c.relname IN (
            'encrypted_search_history',
            'user_subscriptions',
            'user_payments',
            'lemon_squeezy_webhooks'
        )
        GROUP BY c.relname
    LOOP
        IF v_policy_count > 0 THEN
            RETURN QUERY SELECT 
                'POLICY_EXISTS'::TEXT,
                'PASS'::TEXT,
                format('Table %s has %s policies', v_table_name, v_policy_count)::TEXT;
        ELSE
            RETURN QUERY SELECT 
                'POLICY_EXISTS'::TEXT,
                'FAIL'::TEXT,
                format('Table %s has NO policies', v_table_name)::TEXT;
        END IF;
    END LOOP;

    -- Check 3: Verify no public INSERT/UPDATE/DELETE policies
    FOR v_table_name IN
        SELECT DISTINCT c.relname::TEXT
        FROM pg_class c
        JOIN pg_policy p ON p.polrelid = c.oid
        WHERE c.relname IN ('encrypted_search_history', 'user_subscriptions', 'user_payments')
        AND p.polcmd IN ('w', 'a', 'd')  -- write, all, delete
        AND p.polroles = ARRAY[0]::oid[]  -- public role
    LOOP
        RETURN QUERY SELECT 
            'NO_PUBLIC_WRITE'::TEXT,
            'FAIL'::TEXT,
            format('Table %s has public write policies', v_table_name)::TEXT;
    END LOOP;

    -- If no failures found for check 3
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            'NO_PUBLIC_WRITE'::TEXT,
            'PASS'::TEXT,
            'No tables have public write policies'::TEXT;
    END IF;

    -- Check 4: Verify indexes exist for performance
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'encrypted_search_history' 
        AND indexname LIKE '%user_id%'
    ) THEN
        RETURN QUERY SELECT 
            'INDEX_USER_ID'::TEXT,
            'PASS'::TEXT,
            'User ID index exists on encrypted_search_history'::TEXT;
    ELSE
        RETURN QUERY SELECT 
            'INDEX_USER_ID'::TEXT,
            'WARN'::TEXT,
            'Consider adding index on user_id for performance'::TEXT;
    END IF;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CREATE PERFORMANCE INDEXES
-- ============================================================================

-- Index for filtering by user_id (most common query)
CREATE INDEX IF NOT EXISTS idx_search_history_user_id 
ON encrypted_search_history(user_id);

-- Index for filtering by created_at (for sorting recent searches)
CREATE INDEX IF NOT EXISTS idx_search_history_created_at 
ON encrypted_search_history(created_at DESC);

-- Composite index for user queries with time sorting
CREATE INDEX IF NOT EXISTS idx_search_history_user_created 
ON encrypted_search_history(user_id, created_at DESC);

-- Index for search status filtering
CREATE INDEX IF NOT EXISTS idx_search_history_status 
ON encrypted_search_history(status);

-- Index for subscription lookups
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id 
ON user_subscriptions(user_id);

-- Index for payment lookups
CREATE INDEX IF NOT EXISTS idx_user_payments_user_id 
ON user_payments(user_id);

-- Index for webhook event deduplication
CREATE INDEX IF NOT EXISTS idx_webhooks_event_id 
ON lemon_squeezy_webhooks(event_id);

-- ============================================================================
-- CREATE AUDIT LOG FUNCTION
-- ============================================================================

-- Function to log security events
CREATE OR REPLACE FUNCTION log_security_event(
    event_type TEXT,
    user_id UUID,
    details JSONB
) RETURNS VOID AS $$
BEGIN
    -- Create audit log table if not exists
    CREATE TABLE IF NOT EXISTS security_audit_log (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        event_type TEXT NOT NULL,
        user_id UUID,
        details JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    INSERT INTO security_audit_log (event_type, user_id, details)
    VALUES (event_type, user_id, details);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- RUN SECURITY AUDIT
-- ============================================================================

SELECT * FROM security_audit();

-- ============================================================================
-- EXPECTED OUTPUT
-- ============================================================================

/*
Expected audit results:

+------------------+--------+--------------------------------------------------------+
| check_name       | status | details                                                |
+------------------+--------+--------------------------------------------------------+
| RLS_ENABLED      | PASS   | Table encrypted_search_history has RLS enabled         |
| RLS_ENABLED      | PASS   | Table user_subscriptions has RLS enabled               |
| RLS_ENABLED      | PASS   | Table user_payments has RLS enabled                    |
| RLS_ENABLED      | PASS   | Table lemon_squeezy_webhooks has RLS enabled          |
| POLICY_EXISTS    | PASS   | Table encrypted_search_history has 1 policies          |
| POLICY_EXISTS    | PASS   | Table user_subscriptions has 1 policies                |
| POLICY_EXISTS    | PASS   | Table user_payments has 1 policies                     |
| POLICY_EXISTS    | PASS   | Table lemon_squeezy_webhooks has 1 policies           |
| NO_PUBLIC_WRITE  | PASS   | No tables have public write policies                   |
| INDEX_USER_ID    | PASS   | User ID index exists on encrypted_search_history       |
+------------------+--------+--------------------------------------------------------+

All checks should show PASS status ✅
*/
