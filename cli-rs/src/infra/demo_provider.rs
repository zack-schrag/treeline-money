//! Demo data provider for testing without real API calls.

use crate::domain::{Account, ServiceResult, Transaction};
use chrono::{Duration, Utc};
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::str::FromStr;
use uuid::Uuid;

pub struct DemoDataProvider;

impl DemoDataProvider {
    pub fn new() -> Self { DemoDataProvider }

    pub fn get_accounts(&self) -> ServiceResult<DemoAccountsResponse> {
        let now = Utc::now();
        let accounts = vec![
            Account {
                id: Uuid::new_v4(), name: "Demo Checking Account".to_string(), nickname: None, account_type: None,
                currency: "USD".to_string(), external_ids: [("simplefin".to_string(), "demo-checking-001".to_string())].into_iter().collect(),
                balance: Some(Decimal::from_str("3247.85").unwrap()), institution_name: Some("Demo Bank".to_string()),
                institution_url: Some("https://demo-bank.example.com".to_string()), institution_domain: Some("demo-bank.example.com".to_string()),
                created_at: now, updated_at: now,
            },
            Account {
                id: Uuid::new_v4(), name: "Demo Savings Account".to_string(), nickname: None, account_type: None,
                currency: "USD".to_string(), external_ids: [("simplefin".to_string(), "demo-savings-001".to_string())].into_iter().collect(),
                balance: Some(Decimal::from_str("15420.50").unwrap()), institution_name: Some("Demo Bank".to_string()),
                institution_url: Some("https://demo-bank.example.com".to_string()), institution_domain: Some("demo-bank.example.com".to_string()),
                created_at: now, updated_at: now,
            },
            Account {
                id: Uuid::new_v4(), name: "Demo Credit Card".to_string(), nickname: None, account_type: None,
                currency: "USD".to_string(), external_ids: [("simplefin".to_string(), "demo-credit-001".to_string())].into_iter().collect(),
                balance: Some(Decimal::from_str("-842.32").unwrap()), institution_name: Some("Demo Credit Union".to_string()),
                institution_url: Some("https://demo-credit.example.com".to_string()), institution_domain: Some("demo-credit.example.com".to_string()),
                created_at: now, updated_at: now,
            },
        ];
        ServiceResult::ok(DemoAccountsResponse { accounts, errors: Vec::new() })
    }

    pub fn get_transactions(&self) -> ServiceResult<DemoTransactionsResponse> {
        let now = Utc::now();
        let start = now - Duration::days(90);
        let templates: Vec<(&str, &str, &str, &str)> = vec![
            ("demo-checking-001", "QFC Grocery Store", "-87.43", "groceries"),
            ("demo-checking-001", "Starbucks", "-5.75", "coffee"),
            ("demo-checking-001", "Shell Gas Station", "-52.00", "transportation"),
            ("demo-checking-001", "Netflix", "-15.99", "entertainment"),
            ("demo-checking-001", "Direct Deposit - Payroll", "3500.00", "income"),
            ("demo-checking-001", "Amazon.com", "-124.87", "shopping"),
            ("demo-checking-001", "PG&E Utility Bill", "-145.23", "utilities"),
            ("demo-checking-001", "Target", "-67.92", "shopping"),
            ("demo-checking-001", "Whole Foods", "-112.56", "groceries"),
            ("demo-checking-001", "Uber", "-23.40", "transportation"),
            ("demo-credit-001", "Delta Airlines", "-450.00", "travel"),
            ("demo-credit-001", "Hilton Hotel", "-285.60", "travel"),
            ("demo-credit-001", "Restaurant - Fine Dining", "-95.75", "dining"),
            ("demo-credit-001", "Apple Store", "-1299.00", "electronics"),
            ("demo-credit-001", "Spotify Premium", "-9.99", "entertainment"),
            ("demo-credit-001", "Payment Thank You", "500.00", "payment"),
            ("demo-savings-001", "Transfer from Checking", "500.00", "transfer"),
            ("demo-savings-001", "Interest Payment", "12.45", "income"),
        ];
        let mut transactions = Vec::new();
        for (i, (account_id, description, amount_str, category)) in templates.iter().enumerate() {
            let offset_days = (i as i64 * 90) / templates.len() as i64;
            let tx_date = start + Duration::days(offset_days);
            let mut tx = Transaction {
                id: Uuid::new_v4(), account_id: Uuid::nil(),
                external_ids: [("simplefin".to_string(), format!("demo-tx-{:04}", i))].into_iter().collect(),
                amount: Decimal::from_str(amount_str).unwrap_or_default(),
                description: Some(description.to_string()),
                transaction_date: tx_date.date_naive(), posted_date: tx_date.date_naive(),
                tags: vec![category.to_string()],
                created_at: now, updated_at: now, deleted_at: None, parent_transaction_id: None,
            };
            tx.ensure_fingerprint();
            transactions.push((account_id.to_string(), tx));
        }
        ServiceResult::ok(DemoTransactionsResponse { transactions, errors: Vec::new() })
    }

    pub fn create_integration(&self) -> ServiceResult<HashMap<String, String>> {
        let mut result = HashMap::new();
        result.insert("accessUrl".to_string(), "https://demo-provider.example.com/access/demo-user".to_string());
        result.insert("demo".to_string(), "true".to_string());
        ServiceResult::ok(result)
    }
}

impl Default for DemoDataProvider { fn default() -> Self { Self::new() } }

pub struct DemoAccountsResponse { pub accounts: Vec<Account>, pub errors: Vec<String> }
pub struct DemoTransactionsResponse { pub transactions: Vec<(String, Transaction)>, pub errors: Vec<String> }
