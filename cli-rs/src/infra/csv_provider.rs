//! CSV provider for importing transactions from files.

use crate::domain::{ServiceResult, Transaction};
use chrono::{NaiveDate, Utc};
use regex::Regex;
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;
use std::str::FromStr;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct ColumnMapping {
    pub date: Option<String>,
    pub description: Option<String>,
    pub amount: Option<String>,
    pub debit: Option<String>,
    pub credit: Option<String>,
    pub posted_date: Option<String>,
}

impl ColumnMapping {
    pub fn new() -> Self {
        ColumnMapping {
            date: None,
            description: None,
            amount: None,
            debit: None,
            credit: None,
            posted_date: None,
        }
    }
}

pub struct CSVProvider;

impl CSVProvider {
    pub fn new() -> Self {
        CSVProvider
    }

    /// Detect column mapping from CSV headers
    pub fn detect_columns(file_path: &str) -> ServiceResult<ColumnMapping> {
        let path = Path::new(file_path);
        if !path.exists() {
            return ServiceResult::fail(format!("File not found: {}", file_path));
        }

        let file = match File::open(path) {
            Ok(f) => f,
            Err(e) => return ServiceResult::fail(format!("Failed to open file: {}", e)),
        };

        let mut reader = csv::Reader::from_reader(BufReader::new(file));
        let headers: Vec<String> = match reader.headers() {
            Ok(h) => h.iter().map(|s| s.to_string()).collect(),
            Err(e) => return ServiceResult::fail(format!("Failed to read headers: {}", e)),
        };

        let date_patterns = ["date", "transaction date", "trans date", "txn date", "posted", "post date"];
        let desc_patterns = ["description", "desc", "memo", "payee", "merchant", "details", "narration"];
        let amount_patterns = ["amount", "amt", "total", "transaction amount"];
        let debit_patterns = ["debit", "dr", "withdrawal", "debit amount"];
        let credit_patterns = ["credit", "cr", "deposit", "credit amount"];

        let mut mapping = ColumnMapping::new();

        // Find date column
        for header in &headers {
            let lower = header.to_lowercase();
            if date_patterns.iter().any(|p| lower.contains(p)) {
                mapping.date = Some(header.clone());
                break;
            }
        }

        // Find amount column
        for header in &headers {
            let lower = header.to_lowercase();
            if amount_patterns.iter().any(|p| lower.contains(p)) {
                mapping.amount = Some(header.clone());
                break;
            }
        }

        // If no amount, look for debit/credit
        if mapping.amount.is_none() {
            for header in &headers {
                let lower = header.to_lowercase();
                if debit_patterns.iter().any(|p| lower.contains(p)) {
                    mapping.debit = Some(header.clone());
                }
                if credit_patterns.iter().any(|p| lower.contains(p)) {
                    mapping.credit = Some(header.clone());
                }
            }
        }

        // Find description column
        for header in &headers {
            let lower = header.to_lowercase();
            if Some(header) != mapping.date.as_ref() {
                if desc_patterns.iter().any(|p| lower.contains(p)) {
                    mapping.description = Some(header.clone());
                    break;
                }
            }
        }

        // Fallback for description
        if mapping.description.is_none() {
            let fallback = ["name", "type", "ref", "reference", "category"];
            for header in &headers {
                let lower = header.to_lowercase();
                if Some(header) != mapping.date.as_ref() {
                    if fallback.iter().any(|p| lower.contains(p)) {
                        mapping.description = Some(header.clone());
                        break;
                    }
                }
            }
        }

        ServiceResult::ok(mapping)
    }

    /// Get the headers from a CSV file
    pub fn get_headers(file_path: &str) -> ServiceResult<Vec<String>> {
        let path = Path::new(file_path);
        if !path.exists() {
            return ServiceResult::fail(format!("File not found: {}", file_path));
        }

        let file = match File::open(path) {
            Ok(f) => f,
            Err(e) => return ServiceResult::fail(format!("Failed to open file: {}", e)),
        };

        let mut reader = csv::Reader::from_reader(BufReader::new(file));
        match reader.headers() {
            Ok(h) => ServiceResult::ok(h.iter().map(|s| s.to_string()).collect()),
            Err(e) => ServiceResult::fail(format!("Failed to read headers: {}", e)),
        }
    }

    /// Parse transactions from CSV file
    pub fn get_transactions(
        file_path: &str,
        mapping: &ColumnMapping,
        flip_signs: bool,
        debit_negative: bool,
    ) -> ServiceResult<Vec<Transaction>> {
        let path = Path::new(file_path);
        if !path.exists() {
            return ServiceResult::fail(format!("File not found: {}", file_path));
        }

        let file = match File::open(path) {
            Ok(f) => f,
            Err(e) => return ServiceResult::fail(format!("Failed to open file: {}", e)),
        };

        let mut reader = csv::Reader::from_reader(BufReader::new(file));

        // Get headers before iterating records
        let headers: Vec<String> = match reader.headers() {
            Ok(h) => h.iter().map(|s| s.to_string()).collect(),
            Err(e) => return ServiceResult::fail(format!("Failed to read headers: {}", e)),
        };

        let mut transactions = Vec::new();
        let now = Utc::now();

        for result in reader.records() {
            let record = match result {
                Ok(r) => r,
                Err(_) => continue, // Skip invalid rows
            };

            // Parse date
            let date_col = mapping.date.as_ref();
            let date_str = date_col.and_then(|col| {
                headers.iter().position(|c| c == col)
                    .and_then(|idx| record.get(idx))
            });

            let transaction_date = match date_str {
                Some(s) => match Self::parse_date(s) {
                    Some(d) => d,
                    None => continue,
                },
                None => continue,
            };

            // Parse amount
            let amount = if let Some(ref amt_col) = mapping.amount {
                let amt_str = headers.iter().position(|c| c == amt_col)
                    .and_then(|idx| record.get(idx));
                match amt_str.and_then(Self::parse_amount) {
                    Some(a) => a,
                    None => continue,
                }
            } else {
                // Handle debit/credit columns
                let debit_str = mapping.debit.as_ref().and_then(|col| {
                    headers.iter().position(|c| c == col)
                        .and_then(|idx| record.get(idx))
                });
                let credit_str = mapping.credit.as_ref().and_then(|col| {
                    headers.iter().position(|c| c == col)
                        .and_then(|idx| record.get(idx))
                });

                let debit_amt = debit_str.and_then(Self::parse_amount);
                let credit_amt = credit_str.and_then(Self::parse_amount);

                match (debit_amt, credit_amt) {
                    (Some(d), Some(c)) => {
                        if d.abs() > c.abs() { d } else { c }
                    }
                    (Some(mut d), None) => {
                        if debit_negative && d > Decimal::ZERO {
                            d = -d;
                        }
                        d
                    }
                    (None, Some(c)) => c,
                    (None, None) => continue,
                }
            };

            // Apply sign flip
            let final_amount = if flip_signs { -amount } else { amount };

            // Parse description
            let desc_str = mapping.description.as_ref().and_then(|col| {
                headers.iter().position(|c| c == col)
                    .and_then(|idx| record.get(idx))
            });
            let description = desc_str.map(|s| Self::clean_description(s));

            let transaction = Transaction {
                id: Uuid::new_v4(),
                account_id: Uuid::nil(), // Will be set by import service
                external_ids: HashMap::new(),
                amount: final_amount,
                description,
                transaction_date,
                posted_date: transaction_date,
                tags: Vec::new(),
                created_at: now,
                updated_at: now,
                deleted_at: None,
                parent_transaction_id: None,
            };

            transactions.push(transaction);
        }

        ServiceResult::ok(transactions)
    }

    /// Preview first N transactions
    pub fn preview_transactions(
        file_path: &str,
        mapping: &ColumnMapping,
        limit: usize,
        flip_signs: bool,
        debit_negative: bool,
    ) -> ServiceResult<Vec<Transaction>> {
        let result = Self::get_transactions(file_path, mapping, flip_signs, debit_negative);
        match result.data {
            Some(txs) => ServiceResult::ok(txs.into_iter().take(limit).collect()),
            None => result,
        }
    }

    fn parse_date(date_str: &str) -> Option<NaiveDate> {
        let s = date_str.trim();
        if s.is_empty() {
            return None;
        }

        let formats = [
            "%Y-%m-%d",  // 2024-10-01
            "%m/%d/%Y",  // 10/01/2024
            "%d/%m/%Y",  // 01/10/2024
            "%Y/%m/%d",  // 2024/10/01
            "%m-%d-%Y",  // 10-01-2024
            "%d-%m-%Y",  // 01-10-2024
        ];

        for fmt in &formats {
            if let Ok(date) = NaiveDate::parse_from_str(s, fmt) {
                return Some(date);
            }
        }

        None
    }

    fn parse_amount(amount_str: &str) -> Option<Decimal> {
        let s = amount_str.trim();
        if s.is_empty() {
            return None;
        }

        let mut cleaned = s.replace("$", "")
            .replace(",", "")
            .replace(" ", "");

        // Handle parentheses notation: (100.00) -> -100.00
        if cleaned.starts_with('(') && cleaned.ends_with(')') {
            cleaned = format!("-{}", &cleaned[1..cleaned.len()-1]);
        }

        Decimal::from_str(&cleaned).ok()
    }

    fn clean_description(description: &str) -> String {
        let mut cleaned = description.to_string();

        // Remove literal "null" strings
        let null_re = Regex::new(r"(?i)\bnull\b").unwrap();
        cleaned = null_re.replace_all(&cleaned, "").to_string();

        // Remove card number masks
        let card_re = Regex::new(r"(?i)x{10,}\d+").unwrap();
        cleaned = card_re.replace_all(&cleaned, "").to_string();

        // Clean up whitespace
        let ws_re = Regex::new(r"\s+").unwrap();
        cleaned = ws_re.replace_all(&cleaned, " ").trim().to_string();

        cleaned
    }

    /// Check if debits should be negated
    pub fn should_negate_debits(file_path: &str, debit_col: &str) -> ServiceResult<bool> {
        let path = Path::new(file_path);
        if !path.exists() {
            return ServiceResult::fail(format!("File not found: {}", file_path));
        }

        let file = match File::open(path) {
            Ok(f) => f,
            Err(e) => return ServiceResult::fail(format!("Failed to open file: {}", e)),
        };

        let mut reader = csv::Reader::from_reader(BufReader::new(file));
        let headers: Vec<String> = match reader.headers() {
            Ok(h) => h.iter().map(|s| s.to_string()).collect(),
            Err(e) => return ServiceResult::fail(format!("Failed to read headers: {}", e)),
        };

        let debit_idx = headers.iter().position(|h| h == debit_col);
        if debit_idx.is_none() {
            return ServiceResult::ok(false);
        }
        let idx = debit_idx.unwrap();

        let mut debit_values = Vec::new();
        for (i, result) in reader.records().enumerate() {
            if i >= 10 { break; } // Sample first 10 rows
            if let Ok(record) = result {
                if let Some(val) = record.get(idx) {
                    if let Some(amt) = Self::parse_amount(val) {
                        debit_values.push(amt);
                    }
                }
            }
        }

        if debit_values.len() >= 2 {
            let all_positive = debit_values.iter().all(|&amt| amt > Decimal::ZERO);
            return ServiceResult::ok(all_positive);
        }

        ServiceResult::ok(false)
    }
}
