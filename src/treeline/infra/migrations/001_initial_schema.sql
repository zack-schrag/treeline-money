-- Initial schema for Treeline Money
-- This creates the core tables for financial data

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    nickname VARCHAR,
    account_type VARCHAR,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    external_ids JSON,
    institution_name VARCHAR,
    institution_url VARCHAR,
    institution_domain VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR PRIMARY KEY,
    account_id VARCHAR NOT NULL,
    external_ids JSON,
    amount DECIMAL(15,2) NOT NULL,
    description VARCHAR,
    transaction_date TIMESTAMP NOT NULL,
    posted_date TIMESTAMP NOT NULL,
    tags VARCHAR[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS balance_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    account_id VARCHAR NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS integrations (
    user_id VARCHAR NOT NULL,
    integration_name VARCHAR NOT NULL,
    integration_settings JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, integration_name)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_balance_snapshots_account_id ON balance_snapshots(account_id);
CREATE INDEX IF NOT EXISTS idx_balance_snapshots_time ON balance_snapshots(snapshot_time);
