//! DuckDB implementation of the Repository trait.

use crate::domain::{Account, BalanceSnapshot, Integration, ServiceResult, Transaction};
use crate::repository::{QueryResult, Repository};
use chrono::{NaiveDate, NaiveDateTime, TimeZone, Utc};
use duckdb::{params, Connection};
use duckdb::arrow::array::{Array, AsArray};
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::path::PathBuf;
use std::str::FromStr;
use std::sync::Mutex;
use uuid::Uuid;

fn arrow_value_to_json(col: &dyn Array, row_idx: usize) -> serde_json::Value {
    use duckdb::arrow::datatypes::DataType;
    if col.is_null(row_idx) {
        return serde_json::Value::Null;
    }
    match col.data_type() {
        DataType::Boolean => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::BooleanArray>().unwrap();
            serde_json::Value::Bool(arr.value(row_idx))
        }
        DataType::Int8 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Int8Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Int16 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Int16Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Int32 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Int32Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Int64 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Int64Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::UInt8 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::UInt8Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::UInt16 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::UInt16Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::UInt32 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::UInt32Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::UInt64 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::UInt64Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Float32 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Float32Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Float64 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Float64Array>().unwrap();
            serde_json::json!(arr.value(row_idx))
        }
        DataType::Utf8 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::StringArray>().unwrap();
            serde_json::Value::String(arr.value(row_idx).to_string())
        }
        DataType::LargeUtf8 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::LargeStringArray>().unwrap();
            serde_json::Value::String(arr.value(row_idx).to_string())
        }
        DataType::Date32 => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Date32Array>().unwrap();
            let days = arr.value(row_idx);
            let date = chrono::NaiveDate::from_num_days_from_ce_opt(days + 719163).unwrap_or_default();
            serde_json::Value::String(date.to_string())
        }
        DataType::Timestamp(_, _) => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::TimestampMicrosecondArray>().unwrap();
            let micros = arr.value(row_idx);
            let dt = chrono::DateTime::from_timestamp_micros(micros).unwrap_or_default();
            serde_json::Value::String(dt.to_string())
        }
        DataType::Decimal128(_, scale) => {
            let arr = col.as_any().downcast_ref::<duckdb::arrow::array::Decimal128Array>().unwrap();
            let val = arr.value(row_idx);
            let scale_factor = 10_i128.pow(*scale as u32);
            let decimal = val as f64 / scale_factor as f64;
            serde_json::json!(decimal)
        }
        _ => serde_json::Value::String(format!("{:?}", col.data_type())),
    }
}

const MIGRATION_000: &str = "CREATE TABLE IF NOT EXISTS sys_migrations (migration_name VARCHAR PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);";

const MIGRATION_001: &str = r#"
CREATE TABLE IF NOT EXISTS sys_accounts (
    account_id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, nickname VARCHAR, account_type VARCHAR,
    currency VARCHAR NOT NULL DEFAULT 'USD', balance DECIMAL(15,2), external_ids JSON DEFAULT '{}',
    institution_name VARCHAR, institution_url VARCHAR, institution_domain VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sys_transactions (
    transaction_id VARCHAR PRIMARY KEY, account_id VARCHAR NOT NULL, amount DECIMAL(15,2) NOT NULL,
    description VARCHAR, transaction_date DATE NOT NULL, posted_date DATE NOT NULL, tags JSON DEFAULT '[]',
    external_ids JSON DEFAULT '{}', created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TIMESTAMP, parent_transaction_id VARCHAR
);
CREATE TABLE IF NOT EXISTS sys_balance_snapshots (
    snapshot_id VARCHAR PRIMARY KEY, account_id VARCHAR NOT NULL, balance DECIMAL(15,2) NOT NULL,
    snapshot_time TIMESTAMP NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sys_integrations (
    integration_name VARCHAR PRIMARY KEY, integration_settings JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE VIEW transactions AS SELECT t.*, a.name AS account_name, a.account_type, a.currency, a.institution_name FROM sys_transactions t LEFT JOIN sys_accounts a ON t.account_id = a.account_id;
CREATE OR REPLACE VIEW accounts AS SELECT * FROM sys_accounts;
CREATE OR REPLACE VIEW balance_snapshots AS SELECT s.*, a.name AS account_name, a.institution_name FROM sys_balance_snapshots s LEFT JOIN sys_accounts a ON s.account_id = a.account_id;
"#;

pub struct DuckDBRepository {
    db_path: PathBuf,
    conn: Mutex<Connection>,
}

impl DuckDBRepository {
    pub fn new(db_file_path: &str) -> Result<Self, String> {
        let db_path = PathBuf::from(db_file_path);
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("Failed to create database directory: {}", e))?;
        }
        let conn = Connection::open(&db_path).map_err(|e| format!("Failed to open database: {}", e))?;
        Ok(DuckDBRepository { db_path, conn: Mutex::new(conn) })
    }

    fn parse_datetime(s: &str) -> Option<chrono::DateTime<Utc>> {
        NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S%.f").ok()
            .or_else(|| NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S").ok())
            .map(|n| Utc.from_utc_datetime(&n))
    }

    fn parse_date(s: &str) -> Option<NaiveDate> {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").ok()
    }

    fn parse_naive_datetime(s: &str) -> Option<NaiveDateTime> {
        NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S%.f").ok()
            .or_else(|| NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S").ok())
            .or_else(|| NaiveDate::parse_from_str(s, "%Y-%m-%d").ok().map(|d| d.and_hms_opt(0,0,0).unwrap()))
    }
}

impl Repository for DuckDBRepository {
    fn ensure_db_exists(&self) -> ServiceResult<()> {
        if let Some(parent) = self.db_path.parent() {
            if let Err(e) = std::fs::create_dir_all(parent) {
                return ServiceResult::fail(format!("Failed to create database directory: {}", e));
            }
        }
        ServiceResult::ok(())
    }

    fn ensure_schema_upgraded(&self) -> ServiceResult<()> {
        let conn = self.conn.lock().unwrap();
        let migrations_exists: bool = conn.query_row(
            "SELECT COUNT(*) > 0 FROM information_schema.tables WHERE table_name = 'sys_migrations'",
            [], |row| row.get(0),
        ).unwrap_or(false);

        if !migrations_exists {
            if let Err(e) = conn.execute_batch(MIGRATION_000) {
                return ServiceResult::fail(format!("Failed to create migrations table: {}", e));
            }
        }

        for (name, sql) in [("000_migrations.sql", MIGRATION_000), ("001_initial_schema.sql", MIGRATION_001)] {
            let applied: bool = conn.query_row(
                "SELECT COUNT(*) > 0 FROM sys_migrations WHERE migration_name = ?",
                params![name], |row| row.get(0),
            ).unwrap_or(false);

            if !applied {
                if let Err(e) = conn.execute_batch(sql) {
                    return ServiceResult::fail(format!("Failed to run migration {}: {}", name, e));
                }
                let _ = conn.execute("INSERT INTO sys_migrations (migration_name) VALUES (?)", params![name]);
            }
        }
        ServiceResult::ok(())
    }

    fn add_account(&self, account: &Account) -> ServiceResult<Account> {
        let conn = self.conn.lock().unwrap();
        let ext_json = serde_json::to_string(&account.external_ids).unwrap_or_default();
        let created = account.created_at.format("%Y-%m-%d %H:%M:%S").to_string();
        let updated = account.updated_at.format("%Y-%m-%d %H:%M:%S").to_string();

        if let Err(e) = conn.execute(
            "INSERT INTO sys_accounts (account_id, name, nickname, account_type, currency, external_ids, institution_name, institution_url, institution_domain, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params![account.id.to_string(), account.name, account.nickname, account.account_type, account.currency, ext_json, account.institution_name, account.institution_url, account.institution_domain, created, updated],
        ) {
            return ServiceResult::fail(format!("Failed to add account: {}", e));
        }
        ServiceResult::ok(account.clone())
    }

    fn bulk_upsert_accounts(&self, accounts: &[Account]) -> ServiceResult<Vec<Account>> {
        let conn = self.conn.lock().unwrap();
        for account in accounts {
            let ext_json = serde_json::to_string(&account.external_ids).unwrap_or_default();
            let created = account.created_at.format("%Y-%m-%d %H:%M:%S").to_string();
            let updated = account.updated_at.format("%Y-%m-%d %H:%M:%S").to_string();
            let _ = conn.execute(
                "INSERT INTO sys_accounts (account_id, name, nickname, account_type, currency, external_ids, institution_name, institution_url, institution_domain, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (account_id) DO UPDATE SET name = excluded.name, nickname = COALESCE(sys_accounts.nickname, excluded.nickname), account_type = COALESCE(sys_accounts.account_type, excluded.account_type), currency = excluded.currency, external_ids = excluded.external_ids, institution_name = COALESCE(excluded.institution_name, sys_accounts.institution_name), updated_at = excluded.updated_at",
                params![account.id.to_string(), account.name, account.nickname, account.account_type, account.currency, ext_json, account.institution_name, account.institution_url, account.institution_domain, created, updated],
            );
        }
        ServiceResult::ok(accounts.to_vec())
    }

    fn get_accounts(&self) -> ServiceResult<Vec<Account>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = match conn.prepare("SELECT account_id, name, nickname, account_type, currency, balance, external_ids, institution_name, institution_url, institution_domain, created_at, updated_at FROM sys_accounts") {
            Ok(s) => s, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        let mut rows = match stmt.query([]) {
            Ok(r) => r, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        let mut accounts = Vec::new();
        while let Ok(Some(row)) = rows.next() {
            let id_str: String = row.get(0).unwrap_or_default();
            let ext_str: String = row.get::<_, Option<String>>(6).unwrap_or_default().unwrap_or_default();
            let balance: Option<f64> = row.get(5).unwrap_or(None);
            let created_str: String = row.get::<_, Option<String>>(10).unwrap_or_default().unwrap_or_default();
            let updated_str: String = row.get::<_, Option<String>>(11).unwrap_or_default().unwrap_or_default();
            accounts.push(Account {
                id: Uuid::from_str(&id_str).unwrap_or_default(),
                name: row.get(1).unwrap_or_default(),
                nickname: row.get::<_, Option<String>>(2).unwrap_or_default(),
                account_type: row.get::<_, Option<String>>(3).unwrap_or_default(),
                currency: row.get::<_, Option<String>>(4).unwrap_or_default().unwrap_or_else(|| "USD".to_string()),
                external_ids: serde_json::from_str(&ext_str).unwrap_or_default(),
                balance: balance.map(|b| Decimal::from_str(&format!("{:.2}", b)).unwrap_or_default()),
                institution_name: row.get::<_, Option<String>>(7).unwrap_or_default(),
                institution_url: row.get::<_, Option<String>>(8).unwrap_or_default(),
                institution_domain: row.get::<_, Option<String>>(9).unwrap_or_default(),
                created_at: Self::parse_datetime(&created_str).unwrap_or_else(Utc::now),
                updated_at: Self::parse_datetime(&updated_str).unwrap_or_else(Utc::now),
            });
        }
        ServiceResult::ok(accounts)
    }

    fn get_account_by_id(&self, account_id: Uuid) -> ServiceResult<Account> {
        let conn = self.conn.lock().unwrap();
        match conn.query_row(
            "SELECT account_id, name, nickname, account_type, currency, balance, external_ids, institution_name, institution_url, institution_domain, created_at, updated_at FROM sys_accounts WHERE account_id = ?",
            params![account_id.to_string()],
            |row| {
                let id_str: String = row.get(0)?;
                let ext_str: String = row.get::<_, Option<String>>(6)?.unwrap_or_default();
                let balance: Option<f64> = row.get(5)?;
                let created_str: String = row.get::<_, Option<String>>(10)?.unwrap_or_default();
                let updated_str: String = row.get::<_, Option<String>>(11)?.unwrap_or_default();
                Ok(Account {
                    id: Uuid::from_str(&id_str).unwrap_or_default(),
                    name: row.get(1)?,
                    nickname: row.get::<_, Option<String>>(2)?,
                    account_type: row.get::<_, Option<String>>(3)?,
                    currency: row.get::<_, Option<String>>(4)?.unwrap_or_else(|| "USD".to_string()),
                    external_ids: serde_json::from_str(&ext_str).unwrap_or_default(),
                    balance: balance.map(|b| Decimal::from_str(&format!("{:.2}", b)).unwrap_or_default()),
                    institution_name: row.get::<_, Option<String>>(7)?,
                    institution_url: row.get::<_, Option<String>>(8)?,
                    institution_domain: row.get::<_, Option<String>>(9)?,
                    created_at: Self::parse_datetime(&created_str).unwrap_or_else(Utc::now),
                    updated_at: Self::parse_datetime(&updated_str).unwrap_or_else(Utc::now),
                })
            },
        ) {
            Ok(a) => ServiceResult::ok(a),
            Err(_) => ServiceResult::fail("Account not found"),
        }
    }

    fn update_account_by_id(&self, account: &Account) -> ServiceResult<Account> {
        let conn = self.conn.lock().unwrap();
        let ext_json = serde_json::to_string(&account.external_ids).unwrap_or_default();
        let updated = account.updated_at.format("%Y-%m-%d %H:%M:%S").to_string();
        if let Err(e) = conn.execute(
            "UPDATE sys_accounts SET name = ?, nickname = ?, account_type = ?, currency = ?, external_ids = ?, institution_name = ?, institution_url = ?, institution_domain = ?, updated_at = ? WHERE account_id = ?",
            params![account.name, account.nickname, account.account_type, account.currency, ext_json, account.institution_name, account.institution_url, account.institution_domain, updated, account.id.to_string()],
        ) {
            return ServiceResult::fail(format!("Failed to update account: {}", e));
        }
        ServiceResult::ok(account.clone())
    }

    fn bulk_upsert_transactions(&self, transactions: &[Transaction]) -> ServiceResult<Vec<Transaction>> {
        let conn = self.conn.lock().unwrap();
        for tx in transactions {
            let ext_json = serde_json::to_string(&tx.external_ids).unwrap_or_default();
            let tags_json = serde_json::to_string(&tx.tags).unwrap_or_default();
            let created = tx.created_at.format("%Y-%m-%d %H:%M:%S").to_string();
            let updated = tx.updated_at.format("%Y-%m-%d %H:%M:%S").to_string();
            let deleted = tx.deleted_at.map(|d| d.format("%Y-%m-%d %H:%M:%S").to_string());
            let parent_id = tx.parent_transaction_id.map(|p| p.to_string());
            let _ = conn.execute(
                "INSERT INTO sys_transactions (transaction_id, account_id, external_ids, amount, description, transaction_date, posted_date, tags, created_at, updated_at, deleted_at, parent_transaction_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (transaction_id) DO UPDATE SET account_id = excluded.account_id, external_ids = excluded.external_ids, amount = excluded.amount, description = excluded.description, transaction_date = excluded.transaction_date, posted_date = excluded.posted_date, tags = excluded.tags, updated_at = excluded.updated_at",
                params![tx.id.to_string(), tx.account_id.to_string(), ext_json, tx.amount.to_string().parse::<f64>().unwrap_or(0.0), tx.description, tx.transaction_date.to_string(), tx.posted_date.to_string(), tags_json, created, updated, deleted, parent_id],
            );
        }
        ServiceResult::ok(transactions.to_vec())
    }

    fn get_transactions_by_external_ids(&self, external_ids: &[HashMap<String, String>]) -> ServiceResult<Vec<Transaction>> {
        let conn = self.conn.lock().unwrap();
        let mut transactions = Vec::new();
        for ext_id_obj in external_ids {
            for (_, value) in ext_id_obj {
                let query = format!("SELECT transaction_id, account_id, amount, description, transaction_date, posted_date, tags, external_ids, created_at, updated_at, deleted_at, parent_transaction_id FROM sys_transactions WHERE external_ids::VARCHAR LIKE '%{}%'", value);
                if let Ok(mut stmt) = conn.prepare(&query) {
                    if let Ok(iter) = stmt.query_map([], |row| {
                        let id_str: String = row.get(0)?;
                        let acc_str: String = row.get(1)?;
                        let amount: f64 = row.get(2)?;
                        let ext_str: String = row.get::<_, Option<String>>(7)?.unwrap_or_default();
                        let tags_str: String = row.get::<_, Option<String>>(6)?.unwrap_or_default();
                        let created_str: String = row.get::<_, Option<String>>(8)?.unwrap_or_default();
                        let updated_str: String = row.get::<_, Option<String>>(9)?.unwrap_or_default();
                        let deleted_str: Option<String> = row.get(10).ok();
                        let parent_str: Option<String> = row.get(11).ok();
                        let tx_date_str: String = row.get::<_, Option<String>>(4)?.unwrap_or_default();
                        let posted_str: String = row.get::<_, Option<String>>(5)?.unwrap_or_default();
                        Ok(Transaction {
                            id: Uuid::from_str(&id_str).unwrap_or_default(),
                            account_id: Uuid::from_str(&acc_str).unwrap_or_default(),
                            external_ids: serde_json::from_str(&ext_str).unwrap_or_default(),
                            amount: Decimal::from_str(&format!("{:.2}", amount)).unwrap_or_default(),
                            description: row.get(3)?,
                            transaction_date: Self::parse_date(&tx_date_str).unwrap_or_else(|| chrono::Local::now().date_naive()),
                            posted_date: Self::parse_date(&posted_str).unwrap_or_else(|| chrono::Local::now().date_naive()),
                            tags: serde_json::from_str(&tags_str).unwrap_or_default(),
                            created_at: Self::parse_datetime(&created_str).unwrap_or_else(Utc::now),
                            updated_at: Self::parse_datetime(&updated_str).unwrap_or_else(Utc::now),
                            deleted_at: deleted_str.and_then(|s| Self::parse_datetime(&s)),
                            parent_transaction_id: parent_str.and_then(|s| Uuid::from_str(&s).ok()),
                        })
                    }) {
                        transactions.extend(iter.filter_map(|r| r.ok()));
                    }
                }
            }
        }
        ServiceResult::ok(transactions)
    }

    fn get_transactions_by_account(&self, account_id: Uuid) -> ServiceResult<Vec<Transaction>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = match conn.prepare("SELECT transaction_id, account_id, amount, description, transaction_date, posted_date, tags, external_ids, created_at, updated_at, deleted_at, parent_transaction_id FROM sys_transactions WHERE account_id = ? ORDER BY transaction_date DESC") {
            Ok(s) => s, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        let iter = match stmt.query_map(params![account_id.to_string()], |row| {
            let id_str: String = row.get(0)?;
            let acc_str: String = row.get(1)?;
            let amount: f64 = row.get(2)?;
            let ext_str: String = row.get::<_, Option<String>>(7)?.unwrap_or_default();
            let tags_str: String = row.get::<_, Option<String>>(6)?.unwrap_or_default();
            let created_str: String = row.get::<_, Option<String>>(8)?.unwrap_or_default();
            let updated_str: String = row.get::<_, Option<String>>(9)?.unwrap_or_default();
            let deleted_str: Option<String> = row.get(10).ok();
            let parent_str: Option<String> = row.get(11).ok();
            let tx_date_str: String = row.get::<_, Option<String>>(4)?.unwrap_or_default();
            let posted_str: String = row.get::<_, Option<String>>(5)?.unwrap_or_default();
            Ok(Transaction {
                id: Uuid::from_str(&id_str).unwrap_or_default(),
                account_id: Uuid::from_str(&acc_str).unwrap_or_default(),
                external_ids: serde_json::from_str(&ext_str).unwrap_or_default(),
                amount: Decimal::from_str(&format!("{:.2}", amount)).unwrap_or_default(),
                description: row.get(3)?,
                transaction_date: Self::parse_date(&tx_date_str).unwrap_or_else(|| chrono::Local::now().date_naive()),
                posted_date: Self::parse_date(&posted_str).unwrap_or_else(|| chrono::Local::now().date_naive()),
                tags: serde_json::from_str(&tags_str).unwrap_or_default(),
                created_at: Self::parse_datetime(&created_str).unwrap_or_else(Utc::now),
                updated_at: Self::parse_datetime(&updated_str).unwrap_or_else(Utc::now),
                deleted_at: deleted_str.and_then(|s| Self::parse_datetime(&s)),
                parent_transaction_id: parent_str.and_then(|s| Uuid::from_str(&s).ok()),
            })
        }) {
            Ok(i) => i, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        ServiceResult::ok(iter.filter_map(|r| r.ok()).collect())
    }

    fn get_transaction_counts_by_fingerprint(&self, fingerprints: &[String]) -> ServiceResult<HashMap<String, i64>> {
        if fingerprints.is_empty() { return ServiceResult::ok(HashMap::new()); }
        let conn = self.conn.lock().unwrap();
        let fp_list = fingerprints.iter().map(|fp| format!("'{}'", fp)).collect::<Vec<_>>().join(", ");
        let query = format!("SELECT json_extract_string(external_ids, '$.fingerprint') as fp, COUNT(*) as cnt FROM sys_transactions WHERE json_extract_string(external_ids, '$.fingerprint') IN ({}) GROUP BY fp", fp_list);
        let mut counts = HashMap::new();
        if let Ok(mut stmt) = conn.prepare(&query) {
            if let Ok(iter) = stmt.query_map([], |row| {
                let fp: String = row.get(0)?;
                let cnt: i64 = row.get(1)?;
                Ok((fp, cnt))
            }) {
                for row in iter { if let Ok((fp, cnt)) = row { counts.insert(fp, cnt); } }
            }
        }
        ServiceResult::ok(counts)
    }

    fn add_balance(&self, balance: &BalanceSnapshot) -> ServiceResult<BalanceSnapshot> {
        let conn = self.conn.lock().unwrap();
        let snapshot_time = balance.snapshot_time.format("%Y-%m-%d %H:%M:%S").to_string();
        let created = balance.created_at.format("%Y-%m-%d %H:%M:%S").to_string();
        if let Err(e) = conn.execute(
            "INSERT INTO sys_balance_snapshots (snapshot_id, account_id, balance, snapshot_time, created_at) VALUES (?, ?, ?, ?, ?)",
            params![balance.id.to_string(), balance.account_id.to_string(), balance.balance.to_string().parse::<f64>().unwrap_or(0.0), snapshot_time, created],
        ) {
            return ServiceResult::fail(format!("Failed to add balance: {}", e));
        }
        ServiceResult::ok(balance.clone())
    }

    fn get_balance_snapshots(&self, account_id: Option<Uuid>, date: Option<&str>) -> ServiceResult<Vec<BalanceSnapshot>> {
        let conn = self.conn.lock().unwrap();
        let mut query = "SELECT snapshot_id, account_id, balance, snapshot_time, created_at, updated_at FROM sys_balance_snapshots WHERE 1=1".to_string();
        if let Some(acc) = account_id { query.push_str(&format!(" AND account_id = '{}'", acc)); }
        if let Some(d) = date { query.push_str(&format!(" AND DATE(snapshot_time) = '{}'", d)); }
        let mut stmt = match conn.prepare(&query) {
            Ok(s) => s, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        let iter = match stmt.query_map([], |row| {
            let id_str: String = row.get(0)?;
            let acc_str: String = row.get(1)?;
            let balance: f64 = row.get(2)?;
            let snap_str: String = row.get::<_, Option<String>>(3)?.unwrap_or_default();
            let created_str: String = row.get::<_, Option<String>>(4)?.unwrap_or_default();
            let updated_str: String = row.get::<_, Option<String>>(5)?.unwrap_or_default();
            Ok(BalanceSnapshot {
                id: Uuid::from_str(&id_str).unwrap_or_default(),
                account_id: Uuid::from_str(&acc_str).unwrap_or_default(),
                balance: Decimal::from_str(&format!("{:.2}", balance)).unwrap_or_default(),
                snapshot_time: Self::parse_naive_datetime(&snap_str).unwrap_or_else(|| chrono::Local::now().naive_local()),
                created_at: Self::parse_datetime(&created_str).unwrap_or_else(Utc::now),
                updated_at: Self::parse_datetime(&updated_str).unwrap_or_else(Utc::now),
            })
        }) {
            Ok(i) => i, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        ServiceResult::ok(iter.filter_map(|r| r.ok()).collect())
    }

    fn execute_query(&self, sql: &str) -> ServiceResult<QueryResult> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = match conn.prepare(sql) {
            Ok(s) => s, Err(e) => return ServiceResult::fail(format!("Failed to execute query: {}", e)),
        };
        // Use query_arrow for better column name handling
        match stmt.query_arrow([]) {
            Ok(arrow_iter) => {
                let batches: Vec<_> = arrow_iter.collect();
                if batches.is_empty() {
                    return ServiceResult::ok(QueryResult { columns: vec![], rows: vec![], row_count: 0 });
                }
                // Get columns from schema
                let schema = batches[0].schema();
                let columns: Vec<String> = schema.fields().iter().map(|f| f.name().to_string()).collect();
                let col_count = columns.len();
                // Convert arrow batches to rows
                let mut rows = Vec::new();
                for batch in &batches {
                    for row_idx in 0..batch.num_rows() {
                        let mut row_values = Vec::new();
                        for col_idx in 0..col_count {
                            let col = batch.column(col_idx);
                            let json_value = arrow_value_to_json(col, row_idx);
                            row_values.push(json_value);
                        }
                        rows.push(row_values);
                    }
                }
                let row_count = rows.len();
                ServiceResult::ok(QueryResult { columns, rows, row_count })
            }
            Err(e) => ServiceResult::fail(format!("Failed to execute query: {}", e)),
        }
    }

    fn upsert_integration(&self, integration_name: &str, integration_options: &serde_json::Value) -> ServiceResult<()> {
        let conn = self.conn.lock().unwrap();
        let now = Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let options = serde_json::to_string(integration_options).unwrap_or_default();
        if let Err(e) = conn.execute(
            "INSERT INTO sys_integrations (integration_name, integration_settings, created_at, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT (integration_name) DO UPDATE SET integration_settings = excluded.integration_settings, updated_at = ?",
            params![integration_name, options, now.clone(), now.clone(), now],
        ) {
            return ServiceResult::fail(format!("Failed to upsert integration: {}", e));
        }
        ServiceResult::ok(())
    }

    fn list_integrations(&self) -> ServiceResult<Vec<Integration>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = match conn.prepare("SELECT integration_name, integration_settings FROM sys_integrations") {
            Ok(s) => s, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        let iter = match stmt.query_map([], |row| {
            let name: String = row.get(0)?;
            let settings_str: String = row.get(1)?;
            let settings: HashMap<String, serde_json::Value> = serde_json::from_str(&settings_str).unwrap_or_default();
            Ok(Integration { integration_name: name, integration_options: settings })
        }) {
            Ok(i) => i, Err(e) => return ServiceResult::fail(format!("Query failed: {}", e)),
        };
        ServiceResult::ok(iter.filter_map(|r| r.ok()).collect())
    }
}
