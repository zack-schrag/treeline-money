-- Add tags column to accounts
-- This allows accounts to have multiple classification tags
-- Note: We keep account_type for backward compatibility but the app now uses tags

-- Add tags column as VARCHAR array
ALTER TABLE sys_accounts ADD COLUMN tags VARCHAR[];

-- Migrate existing account_type values to tags
-- If account_type is set, create a single-element array
-- If account_type is NULL, create an empty array
UPDATE sys_accounts
SET tags = CASE
    WHEN account_type IS NOT NULL THEN [account_type]
    ELSE []
END;

-- Update the transactions view to include account tags
CREATE OR REPLACE VIEW transactions AS
SELECT
    t.transaction_id,
    t.account_id,
    t.amount,
    t.description,
    t.transaction_date,
    t.posted_date,
    t.tags,
    -- Account details
    a.name AS account_name,
    a.tags AS account_tags,
    a.currency,
    a.institution_name
FROM sys_transactions t
LEFT JOIN sys_accounts a ON t.account_id = a.account_id;

