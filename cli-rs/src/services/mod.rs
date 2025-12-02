//! Service layer implementations.

use crate::domain::{Account, BalanceSnapshot, Integration, ServiceResult, Transaction};
use crate::infra::DemoDataProvider;
use crate::repository::Repository;
use chrono::{Duration, NaiveDate, NaiveDateTime, Utc};
use rust_decimal::Decimal;
use serde::Serialize;
use std::collections::HashMap;
use std::sync::Arc;
use uuid::Uuid;

pub struct DbService { repository: Arc<dyn Repository> }
impl DbService {
    pub fn new(repository: Arc<dyn Repository>) -> Self { DbService { repository } }
    pub fn initialize_db(&self) -> ServiceResult<()> {
        let r = self.repository.ensure_db_exists();
        if !r.success { return r; }
        self.repository.ensure_schema_upgraded()
    }
    pub fn execute_query(&self, sql: &str) -> ServiceResult<crate::repository::QueryResult> {
        self.repository.execute_query(sql)
    }
}

pub struct AccountService { repository: Arc<dyn Repository> }
impl AccountService {
    pub fn new(repository: Arc<dyn Repository>) -> Self { AccountService { repository } }
    pub fn get_accounts(&self) -> ServiceResult<Vec<Account>> { self.repository.get_accounts() }
    pub fn add_balance_snapshot(&self, account_id: Uuid, balance: Decimal, snapshot_date: Option<NaiveDate>) -> ServiceResult<BalanceSnapshot> {
        let r = self.repository.get_account_by_id(account_id);
        if !r.success { return ServiceResult::fail(r.error.unwrap_or_else(|| "Account not found".to_string())); }
        let date = snapshot_date.unwrap_or_else(|| Utc::now().date_naive());
        let snapshot_time = NaiveDateTime::new(date, chrono::NaiveTime::from_hms_opt(0, 0, 0).unwrap());
        let existing = self.repository.get_balance_snapshots(Some(account_id), Some(&date.to_string()));
        if let Some(snaps) = existing.data {
            if snaps.iter().any(|s| (s.balance - balance).abs() < Decimal::new(1, 2)) {
                return ServiceResult::fail(format!("Balance snapshot already exists for {} with same balance", date));
            }
        }
        let now = Utc::now();
        let snapshot = BalanceSnapshot { id: Uuid::new_v4(), account_id, balance, snapshot_time, created_at: now, updated_at: now };
        self.repository.add_balance(&snapshot)
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct StatusData {
    pub accounts: Vec<Account>, pub integrations: Vec<Integration>,
    pub total_accounts: usize, pub total_transactions: i64, pub total_snapshots: i64,
    pub total_integrations: usize, pub integration_names: Vec<String>,
    pub earliest_date: Option<String>, pub latest_date: Option<String>,
}

pub struct StatusService { repository: Arc<dyn Repository> }
impl StatusService {
    pub fn new(repository: Arc<dyn Repository>) -> Self { StatusService { repository } }
    pub fn get_status(&self) -> ServiceResult<StatusData> {
        let accounts = self.repository.get_accounts().data.unwrap_or_default();
        let integrations = self.repository.list_integrations().data.unwrap_or_default();
        let stats = self.repository.execute_query("SELECT COUNT(*) as total, MIN(transaction_date) as earliest, MAX(transaction_date) as latest FROM transactions");
        let (total_transactions, earliest_date, latest_date) = if let Some(r) = stats.data {
            if !r.rows.is_empty() && !r.rows[0].is_empty() {
                (r.rows[0].get(0).and_then(|v| v.as_i64()).unwrap_or(0),
                 r.rows[0].get(1).and_then(|v| v.as_str()).map(|s| s.to_string()),
                 r.rows[0].get(2).and_then(|v| v.as_str()).map(|s| s.to_string()))
            } else { (0, None, None) }
        } else { (0, None, None) };
        let bal_stats = self.repository.execute_query("SELECT COUNT(*) FROM balance_snapshots");
        let total_snapshots = if let Some(r) = bal_stats.data {
            if !r.rows.is_empty() && !r.rows[0].is_empty() { r.rows[0][0].as_i64().unwrap_or(0) } else { 0 }
        } else { 0 };
        let integration_names: Vec<String> = integrations.iter().map(|i| i.integration_name.clone()).collect();
        ServiceResult::ok(StatusData {
            total_accounts: accounts.len(), total_transactions, total_snapshots,
            total_integrations: integrations.len(), integration_names, earliest_date, latest_date,
            accounts, integrations,
        })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct SyncResult { pub results: Vec<IntegrationSyncResult>, pub new_accounts_without_type: Vec<Account> }
#[derive(Debug, Clone, Serialize)]
pub struct IntegrationSyncResult {
    pub integration: String, pub accounts_synced: usize, pub transactions_synced: usize,
    pub transaction_stats: Option<TransactionStats>, pub sync_type: String,
    pub provider_warnings: Vec<String>, pub error: Option<String>,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransactionStats { pub discovered: usize, pub new: usize, pub skipped: usize }

pub struct SyncService { repository: Arc<dyn Repository>, account_service: Arc<AccountService> }
impl SyncService {
    pub fn new(repository: Arc<dyn Repository>, account_service: Arc<AccountService>) -> Self {
        SyncService { repository, account_service }
    }

    pub async fn sync_all_integrations(&self, dry_run: bool) -> ServiceResult<SyncResult> {
        let integrations = self.repository.list_integrations().data.unwrap_or_default();
        if integrations.is_empty() { return ServiceResult::fail("No integrations configured"); }

        let mut sync_results = Vec::new();
        let mut all_new_accounts = Vec::new();

        for integration in integrations {
            let name = integration.integration_name.clone();
            let options: HashMap<String, serde_json::Value> = integration.integration_options;

            // Sync accounts
            let demo = DemoDataProvider::new();
            let acc_result = demo.get_accounts();
            if !acc_result.success {
                sync_results.push(IntegrationSyncResult {
                    integration: name, accounts_synced: 0, transactions_synced: 0, transaction_stats: None,
                    sync_type: "unknown".to_string(), provider_warnings: Vec::new(), error: acc_result.error,
                });
                continue;
            }
            let acc_data = acc_result.data.unwrap();
            let existing = self.repository.get_accounts().data.unwrap_or_default();

            // Map accounts
            let mut updated_accounts = Vec::new();
            let mut new_accounts = Vec::new();
            for discovered in acc_data.accounts {
                let disc_ext = discovered.external_ids.get("simplefin");
                let mut matched = false;
                for existing_acc in &existing {
                    let exist_ext = existing_acc.external_ids.get("simplefin");
                    if let (Some(d), Some(e)) = (disc_ext, exist_ext) {
                        if d == e {
                            let mut updated = discovered.clone();
                            updated.id = existing_acc.id;
                            updated_accounts.push(updated);
                            matched = true;
                            break;
                        }
                    }
                }
                if !matched {
                    new_accounts.push(discovered.clone());
                    updated_accounts.push(discovered);
                }
            }

            if !dry_run {
                let _ = self.repository.bulk_upsert_accounts(&updated_accounts);
                for account in &updated_accounts {
                    if let Some(balance) = account.balance {
                        let _ = self.account_service.add_balance_snapshot(account.id, balance, None);
                    }
                }
            }
            for account in &new_accounts {
                if account.account_type.is_none() { all_new_accounts.push(account.clone()); }
            }

            // Sync transactions
            let tx_result = demo.get_transactions();
            if !tx_result.success {
                sync_results.push(IntegrationSyncResult {
                    integration: name, accounts_synced: updated_accounts.len(), transactions_synced: 0,
                    transaction_stats: None, sync_type: "initial".to_string(),
                    provider_warnings: acc_data.errors, error: tx_result.error,
                });
                continue;
            }
            let tx_data = tx_result.data.unwrap();

            // Map transactions
            let account_id_map: HashMap<String, Uuid> = updated_accounts.iter()
                .filter_map(|a| a.external_ids.get("simplefin").map(|ext| (ext.clone(), a.id)))
                .collect();

            let mut mapped_txs = Vec::new();
            for (provider_acc_id, mut tx) in tx_data.transactions {
                if let Some(internal_id) = account_id_map.get(&provider_acc_id) {
                    tx.account_id = *internal_id;
                    tx.external_ids.remove("fingerprint");
                    tx.ensure_fingerprint();
                    mapped_txs.push(tx);
                }
            }

            // Check for existing transactions
            let ext_ids: Vec<HashMap<String, String>> = mapped_txs.iter()
                .filter_map(|tx| tx.external_ids.get("simplefin").map(|v| {
                    let mut m = HashMap::new();
                    m.insert("simplefin".to_string(), v.clone());
                    m
                }))
                .collect();
            let existing_txs = if !ext_ids.is_empty() {
                self.repository.get_transactions_by_external_ids(&ext_ids).data.unwrap_or_default()
            } else { Vec::new() };
            let existing_by_ext: HashMap<String, Transaction> = existing_txs.into_iter()
                .filter_map(|tx| {
                    let ext_id = tx.external_ids.get("simplefin").cloned();
                    ext_id.map(|v| (v, tx))
                })
                .collect();

            let mut to_insert = Vec::new();
            let mut new_count = 0;
            let mut skipped_count = 0;
            for tx in &mapped_txs {
                if let Some(ext_id) = tx.external_ids.get("simplefin") {
                    if existing_by_ext.contains_key(ext_id) { skipped_count += 1; continue; }
                }
                to_insert.push(tx.clone());
                new_count += 1;
            }

            if !dry_run && !to_insert.is_empty() {
                let _ = self.repository.bulk_upsert_transactions(&to_insert);
            }

            sync_results.push(IntegrationSyncResult {
                integration: name, accounts_synced: updated_accounts.len(), transactions_synced: to_insert.len(),
                transaction_stats: Some(TransactionStats { discovered: mapped_txs.len(), new: new_count, skipped: skipped_count }),
                sync_type: "initial".to_string(), provider_warnings: acc_data.errors, error: None,
            });
        }

        ServiceResult::ok(SyncResult { results: sync_results, new_accounts_without_type: all_new_accounts })
    }

    pub async fn create_integration(&self, integration_name: &str, _options: &HashMap<String, String>) -> ServiceResult<()> {
        let demo = DemoDataProvider::new();
        let result = demo.create_integration();
        if !result.success { return ServiceResult::fail(result.error.unwrap_or_default()); }
        let settings = result.data.unwrap();
        let settings_value = serde_json::to_value(settings).unwrap_or(serde_json::Value::Object(serde_json::Map::new()));
        self.repository.upsert_integration(integration_name, &settings_value)
    }
}

pub struct BackfillService { repository: Arc<dyn Repository>, account_service: Arc<AccountService> }
impl BackfillService {
    pub fn new(repository: Arc<dyn Repository>, account_service: Arc<AccountService>) -> Self {
        BackfillService { repository, account_service }
    }
    pub fn backfill_balances(&self, account_ids: Option<Vec<Uuid>>, days: i64, dry_run: bool) -> ServiceResult<BackfillResult> {
        let all_accounts = self.repository.get_accounts().data.unwrap_or_default();
        let accounts: Vec<_> = if let Some(ids) = &account_ids {
            all_accounts.into_iter().filter(|a| ids.contains(&a.id)).collect()
        } else { all_accounts };
        if accounts.is_empty() { return ServiceResult::fail("No accounts found"); }

        let end_date = Utc::now().date_naive();
        let start_date = end_date - Duration::days(days);
        let mut created = 0; let mut skipped = 0;

        for account in &accounts {
            let txs = self.repository.get_transactions_by_account(account.id).data.unwrap_or_default();
            let current_balance = account.balance.unwrap_or(Decimal::ZERO);
            let mut date = end_date;
            while date >= start_date {
                let future_sum: Decimal = txs.iter().filter(|tx| tx.transaction_date > date).map(|tx| tx.amount).sum();
                let balance_at_date = current_balance - future_sum;
                let existing = self.repository.get_balance_snapshots(Some(account.id), Some(&date.to_string()));
                let should_create = existing.data.map(|e| !e.iter().any(|s| (s.balance - balance_at_date).abs() < Decimal::new(1, 2))).unwrap_or(true);
                if should_create {
                    if !dry_run {
                        let snapshot_time = NaiveDateTime::new(date, chrono::NaiveTime::from_hms_opt(0, 0, 0).unwrap());
                        let now = Utc::now();
                        let snapshot = BalanceSnapshot { id: Uuid::new_v4(), account_id: account.id, balance: balance_at_date, snapshot_time, created_at: now, updated_at: now };
                        if self.repository.add_balance(&snapshot).success { created += 1; }
                    } else { created += 1; }
                } else { skipped += 1; }
                date -= Duration::days(1);
            }
        }
        ServiceResult::ok(BackfillResult { accounts_processed: accounts.len(), snapshots_created: created, snapshots_skipped: skipped })
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct BackfillResult { pub accounts_processed: usize, pub snapshots_created: usize, pub snapshots_skipped: usize }
