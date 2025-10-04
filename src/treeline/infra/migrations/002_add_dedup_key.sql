-- Add dedup_key column to transactions table for fingerprint-based deduplication

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS dedup_key VARCHAR;

-- Create index for efficient fingerprint lookups
CREATE INDEX IF NOT EXISTS idx_transactions_dedup_key ON transactions(dedup_key);
