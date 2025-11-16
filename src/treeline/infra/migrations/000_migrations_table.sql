-- Migration tracking table
-- This table keeps track of which migrations have been applied to the database

CREATE TABLE IF NOT EXISTS sys_migrations (
    version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR
);
