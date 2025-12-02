//! Repository trait for data persistence abstraction.

use crate::domain::{Account, BalanceSnapshot, Integration, ServiceResult, Transaction};
use std::collections::HashMap;
use uuid::Uuid;

/// Result of a SQL query.
#[derive(Debug, Clone)]
pub struct QueryResult {
    pub columns: Vec<String>,
    pub rows: Vec<Vec<serde_json::Value>>,
    pub row_count: usize,
}

/// Repository abstraction for all data persistence operations.
pub trait Repository: Send + Sync {
    fn ensure_db_exists(&self) -> ServiceResult<()>;
    fn ensure_schema_upgraded(&self) -> ServiceResult<()>;

    fn add_account(&self, account: &Account) -> ServiceResult<Account>;
    fn bulk_upsert_accounts(&self, accounts: &[Account]) -> ServiceResult<Vec<Account>>;
    fn get_accounts(&self) -> ServiceResult<Vec<Account>>;
    fn get_account_by_id(&self, account_id: Uuid) -> ServiceResult<Account>;
    fn update_account_by_id(&self, account: &Account) -> ServiceResult<Account>;

    fn bulk_upsert_transactions(&self, transactions: &[Transaction]) -> ServiceResult<Vec<Transaction>>;
    fn get_transactions_by_external_ids(&self, external_ids: &[HashMap<String, String>]) -> ServiceResult<Vec<Transaction>>;
    fn get_transactions_by_account(&self, account_id: Uuid) -> ServiceResult<Vec<Transaction>>;
    fn get_transaction_counts_by_fingerprint(&self, fingerprints: &[String]) -> ServiceResult<HashMap<String, i64>>;

    fn add_balance(&self, balance: &BalanceSnapshot) -> ServiceResult<BalanceSnapshot>;
    fn get_balance_snapshots(&self, account_id: Option<Uuid>, date: Option<&str>) -> ServiceResult<Vec<BalanceSnapshot>>;

    fn execute_query(&self, sql: &str) -> ServiceResult<QueryResult>;

    fn upsert_integration(&self, integration_name: &str, integration_options: &serde_json::Value) -> ServiceResult<()>;
    fn list_integrations(&self) -> ServiceResult<Vec<Integration>>;
}
