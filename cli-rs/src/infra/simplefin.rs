//! SimpleFIN provider for real bank syncing.

use crate::domain::{Account, ServiceResult, Transaction};
use chrono::{DateTime, NaiveDate, TimeZone, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::str::FromStr;
use uuid::Uuid;

#[derive(Debug, Deserialize)]
struct SimpleFINOrg {
    name: Option<String>,
    url: Option<String>,
    domain: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SimpleFINAccount {
    id: String,
    name: String,
    currency: Option<String>,
    balance: Option<f64>,
    org: Option<SimpleFINOrg>,
    transactions: Option<Vec<SimpleFINTransaction>>,
}

#[derive(Debug, Deserialize)]
struct SimpleFINTransaction {
    id: String,
    posted: i64,
    amount: f64,
    description: Option<String>,
    extra: Option<SimpleFINExtra>,
}

#[derive(Debug, Deserialize)]
struct SimpleFINExtra {
    category: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SimpleFINResponse {
    errors: Option<Vec<String>>,
    accounts: Option<Vec<SimpleFINAccount>>,
}

pub struct SimpleFINAccountsResponse {
    pub accounts: Vec<Account>,
    pub errors: Vec<String>,
}

pub struct SimpleFINTransactionsResponse {
    pub transactions: Vec<(String, Transaction)>, // (simplefin_account_id, transaction)
    pub errors: Vec<String>,
}

struct AccessUrlParts {
    clean_url: String,
    username: String,
    password: String,
}

pub struct SimpleFINProvider;

impl SimpleFINProvider {
    pub fn new() -> Self {
        SimpleFINProvider
    }

    fn parse_access_url(access_url: &str) -> Result<AccessUrlParts, String> {
        if access_url.is_empty() {
            return Err("accessUrl is required".to_string());
        }

        let parsed = url::Url::parse(access_url)
            .map_err(|_| "Invalid URL format".to_string())?;

        if parsed.scheme() != "https" {
            return Err("accessUrl must use HTTPS".to_string());
        }

        let host = parsed.host_str().ok_or("Invalid URL: no host")?;
        if !host.ends_with("simplefin.org") {
            return Err("accessUrl must be from simplefin.org domain".to_string());
        }

        let username = parsed.username();
        let password = parsed.password().ok_or("accessUrl must contain password")?;

        if username.is_empty() {
            return Err("accessUrl must contain username".to_string());
        }

        let clean_url = format!("{}://{}{}", parsed.scheme(), host, parsed.path());

        Ok(AccessUrlParts {
            clean_url,
            username: username.to_string(),
            password: password.to_string(),
        })
    }

    pub async fn create_integration(setup_token: &str) -> ServiceResult<HashMap<String, String>> {
        if setup_token.is_empty() {
            return ServiceResult::fail("setupToken is required for SimpleFIN integration");
        }

        // Decode Base64 setup token to get claim URL
        let claim_url = match base64::Engine::decode(&base64::engine::general_purpose::STANDARD, setup_token) {
            Ok(bytes) => match String::from_utf8(bytes) {
                Ok(url) => url,
                Err(_) => return ServiceResult::fail("Invalid setup token format"),
            },
            Err(_) => return ServiceResult::fail("Invalid setup token format"),
        };

        // Exchange setup token for access URL
        let client = reqwest::Client::new();
        let response = match client.post(&claim_url)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                if e.is_timeout() {
                    return ServiceResult::fail("Integration setup failed: Connection timed out");
                }
                if e.is_connect() {
                    return ServiceResult::fail("Integration setup failed: Unable to connect to SimpleFIN servers");
                }
                return ServiceResult::fail(format!("Integration setup failed: {}", e));
            }
        };

        if response.status() != 200 {
            return ServiceResult::fail("Failed to verify SimpleFIN token");
        }

        let access_url = match response.text().await {
            Ok(url) => url,
            Err(_) => return ServiceResult::fail("No access URL received from SimpleFIN"),
        };

        if access_url.is_empty() {
            return ServiceResult::fail("No access URL received from SimpleFIN");
        }

        let mut result = HashMap::new();
        result.insert("accessUrl".to_string(), access_url);
        ServiceResult::ok(result)
    }

    pub async fn get_accounts(access_url: &str) -> ServiceResult<SimpleFINAccountsResponse> {
        let parts = match Self::parse_access_url(access_url) {
            Ok(p) => p,
            Err(e) => return ServiceResult::fail(e),
        };

        let client = reqwest::Client::new();
        let response = match client.get(format!("{}/accounts", parts.clean_url))
            .basic_auth(&parts.username, Some(&parts.password))
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                if e.is_timeout() {
                    return ServiceResult::fail("Failed to fetch SimpleFIN accounts: Connection timed out after 30 seconds");
                }
                if e.is_connect() {
                    return ServiceResult::fail("Failed to fetch SimpleFIN accounts: Unable to connect to SimpleFIN servers");
                }
                return ServiceResult::fail(format!("Failed to fetch SimpleFIN accounts: {}", e));
            }
        };

        let status = response.status().as_u16();
        if status == 403 {
            return ServiceResult::fail(
                "SimpleFIN authentication failed. Your access token may be invalid or revoked. \
                Please reset your SimpleFIN credentials at https://beta-bridge.simplefin.org/"
            );
        }
        if status == 402 {
            return ServiceResult::fail(
                "SimpleFIN subscription payment required. \
                Please check your SimpleFIN account at https://beta-bridge.simplefin.org/"
            );
        }
        if status != 200 {
            return ServiceResult::fail(format!("SimpleFIN API error: HTTP {}", status));
        }

        let data: SimpleFINResponse = match response.json().await {
            Ok(d) => d,
            Err(e) => return ServiceResult::fail(format!("Failed to parse SimpleFIN response: {}", e)),
        };

        let api_errors = data.errors.unwrap_or_default();
        let now = Utc::now();

        let accounts: Vec<Account> = data.accounts.unwrap_or_default().into_iter().map(|acc| {
            let mut external_ids = HashMap::new();
            external_ids.insert("simplefin".to_string(), acc.id);

            Account {
                id: Uuid::new_v4(),
                name: acc.name,
                nickname: None,
                account_type: None,
                currency: acc.currency.unwrap_or_else(|| "USD".to_string()),
                external_ids,
                balance: acc.balance.map(|b| Decimal::from_str(&format!("{:.2}", b)).unwrap_or_default()),
                institution_name: acc.org.as_ref().and_then(|o| o.name.clone()),
                institution_url: acc.org.as_ref().and_then(|o| o.url.clone()),
                institution_domain: acc.org.as_ref().and_then(|o| o.domain.clone()),
                created_at: now,
                updated_at: now,
            }
        }).collect();

        ServiceResult::ok(SimpleFINAccountsResponse { accounts, errors: api_errors })
    }

    pub async fn get_transactions(
        access_url: &str,
        start_date: Option<DateTime<Utc>>,
        end_date: Option<DateTime<Utc>>,
    ) -> ServiceResult<SimpleFINTransactionsResponse> {
        let parts = match Self::parse_access_url(access_url) {
            Ok(p) => p,
            Err(e) => return ServiceResult::fail(e),
        };

        let mut url = format!("{}/accounts", parts.clean_url);
        let mut params = Vec::new();

        if let Some(start) = start_date {
            params.push(format!("start-date={}", start.timestamp()));
        }
        if let Some(end) = end_date {
            params.push(format!("end-date={}", end.timestamp()));
        }

        if !params.is_empty() {
            url = format!("{}?{}", url, params.join("&"));
        }

        let client = reqwest::Client::new();
        let response = match client.get(&url)
            .basic_auth(&parts.username, Some(&parts.password))
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                if e.is_timeout() {
                    return ServiceResult::fail("Failed to fetch SimpleFIN transactions: Connection timed out after 30 seconds");
                }
                if e.is_connect() {
                    return ServiceResult::fail("Failed to fetch SimpleFIN transactions: Unable to connect to SimpleFIN servers");
                }
                return ServiceResult::fail(format!("Failed to fetch SimpleFIN transactions: {}", e));
            }
        };

        let status = response.status().as_u16();
        if status == 403 {
            return ServiceResult::fail(
                "SimpleFIN authentication failed. Your access token may be invalid or revoked. \
                Please reset your SimpleFIN credentials at https://beta-bridge.simplefin.org/"
            );
        }
        if status == 402 {
            return ServiceResult::fail(
                "SimpleFIN subscription payment required. \
                Please check your SimpleFIN account at https://beta-bridge.simplefin.org/"
            );
        }
        if status != 200 {
            return ServiceResult::fail(format!("SimpleFIN API error: HTTP {}", status));
        }

        let data: SimpleFINResponse = match response.json().await {
            Ok(d) => d,
            Err(e) => return ServiceResult::fail(format!("Failed to parse SimpleFIN response: {}", e)),
        };

        let api_errors = data.errors.unwrap_or_default();
        let now = Utc::now();

        let mut transactions_with_accounts = Vec::new();

        for acc in data.accounts.unwrap_or_default() {
            let simplefin_account_id = acc.id.clone();

            for tx in acc.transactions.unwrap_or_default() {
                let mut external_ids = HashMap::new();
                external_ids.insert("simplefin".to_string(), tx.id);

                let posted_dt = DateTime::from_timestamp(tx.posted, 0)
                    .unwrap_or_else(|| Utc::now());
                let transaction_date = posted_dt.date_naive();

                let tags: Vec<String> = tx.extra
                    .and_then(|e| e.category)
                    .map(|c| vec![c])
                    .unwrap_or_default();

                let transaction = Transaction {
                    id: Uuid::new_v4(),
                    account_id: Uuid::nil(), // Placeholder, will be mapped by service
                    external_ids,
                    amount: Decimal::from_str(&format!("{:.2}", tx.amount)).unwrap_or_default(),
                    description: tx.description,
                    transaction_date,
                    posted_date: transaction_date,
                    tags,
                    created_at: now,
                    updated_at: now,
                    deleted_at: None,
                    parent_transaction_id: None,
                };

                transactions_with_accounts.push((simplefin_account_id.clone(), transaction));
            }
        }

        ServiceResult::ok(SimpleFINTransactionsResponse {
            transactions: transactions_with_accounts,
            errors: api_errors,
        })
    }
}
