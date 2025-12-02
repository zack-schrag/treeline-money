//! Domain model definitions.

use chrono::{DateTime, NaiveDate, NaiveDateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use uuid::Uuid;

/// Represents a financial account owned by the user.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    pub id: Uuid,
    pub name: String,
    pub nickname: Option<String>,
    pub account_type: Option<String>,
    pub currency: String,
    pub external_ids: HashMap<String, String>,
    pub balance: Option<Decimal>,
    pub institution_name: Option<String>,
    pub institution_url: Option<String>,
    pub institution_domain: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Account {
    pub fn new(name: String) -> Self {
        let now = Utc::now();
        Account {
            id: Uuid::new_v4(),
            name,
            nickname: None,
            account_type: None,
            currency: "USD".to_string(),
            external_ids: HashMap::new(),
            balance: None,
            institution_name: None,
            institution_url: None,
            institution_domain: None,
            created_at: now,
            updated_at: now,
        }
    }
}

/// A single transaction belonging to an account.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub id: Uuid,
    pub account_id: Uuid,
    pub external_ids: HashMap<String, String>,
    pub amount: Decimal,
    pub description: Option<String>,
    pub transaction_date: NaiveDate,
    pub posted_date: NaiveDate,
    pub tags: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub deleted_at: Option<DateTime<Utc>>,
    pub parent_transaction_id: Option<Uuid>,
}

impl Transaction {
    pub fn new(account_id: Uuid, amount: Decimal, transaction_date: NaiveDate) -> Self {
        let now = Utc::now();
        let mut tx = Transaction {
            id: Uuid::new_v4(),
            account_id,
            external_ids: HashMap::new(),
            amount,
            description: None,
            transaction_date,
            posted_date: transaction_date,
            tags: Vec::new(),
            created_at: now,
            updated_at: now,
            deleted_at: None,
            parent_transaction_id: None,
        };
        tx.ensure_fingerprint();
        tx
    }

    pub fn ensure_fingerprint(&mut self) {
        if !self.external_ids.contains_key("fingerprint") {
            let fingerprint = self.calculate_fingerprint();
            self.external_ids.insert("fingerprint".to_string(), fingerprint);
        }
    }

    fn calculate_fingerprint(&self) -> String {
        let tx_date = self.transaction_date.to_string();
        let amount = if self.amount == Decimal::ZERO {
            Decimal::ZERO
        } else {
            self.amount
        };
        let amount_normalized = format!("{:.2}", amount);
        let desc = self.description.as_deref().unwrap_or("").to_lowercase();
        let desc_normalized = normalize_description(&desc);

        let fingerprint_str = format!(
            "{}|{}|{}|{}",
            self.account_id, tx_date, amount_normalized, desc_normalized
        );

        let mut hasher = Sha256::new();
        hasher.update(fingerprint_str.as_bytes());
        let result = hasher.finalize();
        hex::encode(&result[..8])
    }
}

fn normalize_description(desc: &str) -> String {
    let mut normalized = desc.to_string();
    normalized = normalized.replace("null", "");
    normalized.retain(|c| c.is_alphanumeric());
    normalized
}

/// Represents an account balance captured at a point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BalanceSnapshot {
    pub id: Uuid,
    pub account_id: Uuid,
    pub balance: Decimal,
    pub snapshot_time: NaiveDateTime,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl BalanceSnapshot {
    pub fn new(account_id: Uuid, balance: Decimal, snapshot_time: NaiveDateTime) -> Self {
        let now = Utc::now();
        BalanceSnapshot {
            id: Uuid::new_v4(),
            account_id,
            balance,
            snapshot_time,
            created_at: now,
            updated_at: now,
        }
    }
}

/// Generic result wrapper for service operations.
#[derive(Debug, Clone)]
pub struct ServiceResult<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}

impl<T> ServiceResult<T> {
    pub fn ok(data: T) -> Self {
        ServiceResult {
            success: true,
            data: Some(data),
            error: None,
        }
    }

    pub fn fail(error: impl Into<String>) -> Self {
        ServiceResult {
            success: false,
            data: None,
            error: Some(error.into()),
        }
    }
}

impl ServiceResult<()> {
    pub fn ok_empty() -> Self {
        ServiceResult {
            success: true,
            data: Some(()),
            error: None,
        }
    }
}

/// Integration settings stored in the database.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Integration {
    pub integration_name: String,
    pub integration_options: HashMap<String, serde_json::Value>,
}
