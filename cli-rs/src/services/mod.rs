//! Service layer implementations.

use crate::domain::{Account, BalanceSnapshot, Integration, ServiceResult, Transaction};
use crate::infra::{ColumnMapping, CSVProvider, DemoDataProvider, SimpleFINProvider};
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
    pub start_date: Option<String>, pub provider_warnings: Vec<String>, pub error: Option<String>,
}
#[derive(Debug, Clone, Serialize)]
pub struct TransactionStats { pub discovered: usize, pub new: usize, pub skipped: usize }

struct SyncDateRange {
    start: chrono::DateTime<Utc>,
    end: chrono::DateTime<Utc>,
    sync_type: String,
}

pub struct SyncService { repository: Arc<dyn Repository>, account_service: Arc<AccountService> }
impl SyncService {
    pub fn new(repository: Arc<dyn Repository>, account_service: Arc<AccountService>) -> Self {
        SyncService { repository, account_service }
    }

    /// Calculate sync date range based on existing transactions.
    /// - If transactions exist: incremental sync from (max_date - 7 days) to now
    /// - If no transactions: initial sync for last 90 days
    fn calculate_sync_date_range(&self) -> SyncDateRange {
        let end = Utc::now();

        // Query for the latest transaction date
        let stats = self.repository.execute_query("SELECT MAX(transaction_date) as max_date FROM transactions");

        if let Some(r) = stats.data {
            if !r.rows.is_empty() && !r.rows[0].is_empty() {
                if let Some(max_date_str) = r.rows[0].get(0).and_then(|v| v.as_str()) {
                    // Parse the date and calculate incremental range
                    if let Ok(max_date) = NaiveDate::parse_from_str(max_date_str, "%Y-%m-%d") {
                        let start = max_date.and_hms_opt(0, 0, 0).unwrap().and_utc() - Duration::days(7);
                        return SyncDateRange {
                            start,
                            end,
                            sync_type: "incremental".to_string(),
                        };
                    }
                }
            }
        }

        // Fallback to initial 90-day sync
        SyncDateRange {
            start: end - Duration::days(90),
            end,
            sync_type: "initial".to_string(),
        }
    }

    pub async fn sync_all_integrations(&self, dry_run: bool) -> ServiceResult<SyncResult> {
        let integrations = self.repository.list_integrations().data.unwrap_or_default();
        if integrations.is_empty() { return ServiceResult::fail("No integrations configured"); }

        let mut sync_results = Vec::new();
        let mut all_new_accounts = Vec::new();

        for integration in integrations {
            let name = integration.integration_name.clone();
            let options = integration.integration_options.clone();
            let access_url = options.get("accessUrl").and_then(|v| v.as_str()).unwrap_or_default();

            // Get accounts based on provider type
            let (accounts, acc_errors): (Vec<Account>, Vec<String>) = if name == "demo" {
                let demo = DemoDataProvider::new();
                let acc_result = demo.get_accounts();
                if !acc_result.success {
                    sync_results.push(IntegrationSyncResult {
                        integration: name, accounts_synced: 0, transactions_synced: 0, transaction_stats: None,
                        sync_type: "unknown".to_string(), start_date: None, provider_warnings: Vec::new(), error: acc_result.error,
                    });
                    continue;
                }
                let acc_data = acc_result.data.unwrap();
                (acc_data.accounts, acc_data.errors)
            } else {
                // SimpleFIN
                let acc_result = SimpleFINProvider::get_accounts(access_url).await;
                if !acc_result.success {
                    sync_results.push(IntegrationSyncResult {
                        integration: name, accounts_synced: 0, transactions_synced: 0, transaction_stats: None,
                        sync_type: "unknown".to_string(), start_date: None, provider_warnings: Vec::new(), error: acc_result.error,
                    });
                    continue;
                }
                let acc_data = acc_result.data.unwrap();
                (acc_data.accounts, acc_data.errors)
            };

            let existing = self.repository.get_accounts().data.unwrap_or_default();

            // Map accounts
            let mut updated_accounts = Vec::new();
            let mut new_accounts = Vec::new();
            for discovered in accounts {
                let disc_ext = discovered.external_ids.get("simplefin");
                let mut matched = false;
                for existing_acc in &existing {
                    let exist_ext = existing_acc.external_ids.get("simplefin");
                    if let (Some(d), Some(e)) = (disc_ext, exist_ext) {
                        if d == e {
                            let mut updated = discovered.clone();
                            updated.id = existing_acc.id;
                            updated.account_type = existing_acc.account_type.clone();
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

            // Calculate sync date range (incremental vs initial)
            let date_range = self.calculate_sync_date_range();

            // Get transactions
            let (tx_with_accounts, tx_errors): (Vec<(String, Transaction)>, Vec<String>) = if name == "demo" {
                let demo = DemoDataProvider::new();
                let tx_result = demo.get_transactions();
                if !tx_result.success {
                    sync_results.push(IntegrationSyncResult {
                        integration: name, accounts_synced: updated_accounts.len(), transactions_synced: 0,
                        transaction_stats: None, sync_type: date_range.sync_type.clone(),
                        start_date: Some(date_range.start.format("%Y-%m-%d").to_string()),
                        provider_warnings: acc_errors, error: tx_result.error,
                    });
                    continue;
                }
                let tx_data = tx_result.data.unwrap();
                (tx_data.transactions, tx_data.errors)
            } else {
                // SimpleFIN - use calculated date range (incremental or initial)
                let tx_result = SimpleFINProvider::get_transactions(access_url, Some(date_range.start), Some(date_range.end)).await;
                if !tx_result.success {
                    sync_results.push(IntegrationSyncResult {
                        integration: name, accounts_synced: updated_accounts.len(), transactions_synced: 0,
                        transaction_stats: None, sync_type: date_range.sync_type.clone(),
                        start_date: Some(date_range.start.format("%Y-%m-%d").to_string()),
                        provider_warnings: acc_errors, error: tx_result.error,
                    });
                    continue;
                }
                let tx_data = tx_result.data.unwrap();
                (tx_data.transactions, tx_data.errors)
            };

            // Map transactions to internal account IDs
            let account_id_map: HashMap<String, Uuid> = updated_accounts.iter()
                .filter_map(|a| a.external_ids.get("simplefin").map(|ext| (ext.clone(), a.id)))
                .collect();

            let mut mapped_txs = Vec::new();
            for (provider_acc_id, mut tx) in tx_with_accounts {
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

            let mut all_warnings = acc_errors;
            all_warnings.extend(tx_errors);

            sync_results.push(IntegrationSyncResult {
                integration: name, accounts_synced: updated_accounts.len(), transactions_synced: to_insert.len(),
                transaction_stats: Some(TransactionStats { discovered: mapped_txs.len(), new: new_count, skipped: skipped_count }),
                sync_type: date_range.sync_type, start_date: Some(date_range.start.format("%Y-%m-%d").to_string()),
                provider_warnings: all_warnings, error: None,
            });
        }

        ServiceResult::ok(SyncResult { results: sync_results, new_accounts_without_type: all_new_accounts })
    }

    pub async fn create_integration(&self, integration_name: &str, options: &HashMap<String, String>) -> ServiceResult<()> {
        let settings: HashMap<String, String> = if integration_name == "demo" {
            let demo = DemoDataProvider::new();
            let result = demo.create_integration();
            if !result.success { return ServiceResult::fail(result.error.unwrap_or_default()); }
            result.data.unwrap()
        } else {
            // SimpleFIN - exchange setup token for access URL
            let setup_token = options.get("setupToken").map(|s| s.as_str()).unwrap_or_default();
            let result = SimpleFINProvider::create_integration(setup_token).await;
            if !result.success { return ServiceResult::fail(result.error.unwrap_or_default()); }
            result.data.unwrap()
        };

        let settings_value = serde_json::to_value(settings).unwrap_or(serde_json::Value::Object(serde_json::Map::new()));
        self.repository.upsert_integration(integration_name, &settings_value)
    }
}

// Import Service for CSV imports
#[derive(Debug, Clone, Serialize)]
pub struct ImportResult {
    pub transactions_discovered: usize,
    pub transactions_imported: usize,
    pub transactions_skipped: usize,
}

pub struct ImportService { repository: Arc<dyn Repository> }
impl ImportService {
    pub fn new(repository: Arc<dyn Repository>) -> Self {
        ImportService { repository }
    }

    pub fn detect_columns(&self, file_path: &str) -> ServiceResult<ColumnMapping> {
        CSVProvider::detect_columns(file_path)
    }

    pub fn get_headers(&self, file_path: &str) -> ServiceResult<Vec<String>> {
        CSVProvider::get_headers(file_path)
    }

    pub fn preview(&self, file_path: &str, mapping: &ColumnMapping, limit: usize, flip_signs: bool, debit_negative: bool) -> ServiceResult<Vec<Transaction>> {
        CSVProvider::preview_transactions(file_path, mapping, limit, flip_signs, debit_negative)
    }

    pub fn import_csv(&self, file_path: &str, account_id: Uuid, mapping: &ColumnMapping, flip_signs: bool, debit_negative: bool) -> ServiceResult<ImportResult> {
        // Verify account exists
        let acc_result = self.repository.get_account_by_id(account_id);
        if !acc_result.success {
            return ServiceResult::fail("Account not found");
        }

        // Parse CSV
        let tx_result = CSVProvider::get_transactions(file_path, mapping, flip_signs, debit_negative);
        if !tx_result.success {
            return ServiceResult::fail(tx_result.error.unwrap_or_default());
        }
        let mut transactions = tx_result.data.unwrap();

        // Set account ID and generate fingerprints
        for tx in &mut transactions {
            tx.account_id = account_id;
            tx.ensure_fingerprint();
        }

        let discovered = transactions.len();

        // Check for existing transactions by fingerprint
        let fingerprints: Vec<String> = transactions.iter()
            .filter_map(|tx| tx.external_ids.get("fingerprint").cloned())
            .collect();

        let existing_counts = self.repository.get_transaction_counts_by_fingerprint(&fingerprints);
        let existing_fps: std::collections::HashSet<String> = existing_counts.data.unwrap_or_default()
            .into_iter()
            .filter(|(_, count)| *count > 0)
            .map(|(fp, _)| fp)
            .collect();

        // Filter out existing transactions
        let to_insert: Vec<Transaction> = transactions.into_iter()
            .filter(|tx| {
                tx.external_ids.get("fingerprint")
                    .map(|fp| !existing_fps.contains(fp))
                    .unwrap_or(true)
            })
            .collect();

        let new_count = to_insert.len();
        let skipped = discovered - new_count;

        // Insert new transactions
        if !to_insert.is_empty() {
            let _ = self.repository.bulk_upsert_transactions(&to_insert);
        }

        ServiceResult::ok(ImportResult {
            transactions_discovered: discovered,
            transactions_imported: new_count,
            transactions_skipped: skipped,
        })
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
