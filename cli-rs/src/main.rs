//! Treeline CLI - Personal finance in your terminal.

mod domain;
mod infra;
mod repository;
mod services;

use crate::infra::{ColumnMapping, DuckDBRepository};
use crate::repository::Repository;
use crate::services::{AccountService, BackfillService, DbService, ImportService, StatusService, SyncService};
use chrono::NaiveDate;
use clap::{Parser, Subcommand};
use colored::Colorize;
use comfy_table::{presets::UTF8_FULL, Table, Cell, Color};
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use uuid::Uuid;

#[derive(Parser)]
#[command(name = "tl", author, version, about = "Treeline - personal finance in your terminal")]
struct Cli {
    /// Show version information
    #[arg(short = 'v', long = "version", action = clap::ArgAction::Version)]
    version: (),

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Show account summary and statistics
    Status { #[arg(long)] json: bool },
    /// Set up financial integrations
    Setup { integration: String, #[arg(long)] token: Option<String> },
    /// Synchronize from integrations
    Sync { #[arg(long)] dry_run: bool, #[arg(long)] json: bool },
    /// Execute SQL queries
    Query { sql: Option<String>, #[arg(long, short, default_value = "table")] format: String, #[arg(long, short)] file: Option<PathBuf> },
    /// Create new resources
    New { resource_type: String, #[arg(long)] account_id: Option<Uuid>, #[arg(long)] balance: Option<Decimal>, #[arg(long)] date: Option<NaiveDate> },
    /// Backfill historical data
    Backfill { resource_type: String, #[arg(long)] account_id: Option<Uuid>, #[arg(long, default_value = "90")] days: i64, #[arg(long)] dry_run: bool },
    /// Import transactions from CSV
    Import {
        #[arg(long, short)] file: PathBuf,
        #[arg(long)] account_id: Uuid,
        #[arg(long)] date_column: Option<String>,
        #[arg(long)] amount_column: Option<String>,
        #[arg(long)] description_column: Option<String>,
        #[arg(long)] debit_column: Option<String>,
        #[arg(long)] credit_column: Option<String>,
        #[arg(long)] flip_signs: bool,
        #[arg(long)] debit_negative: bool,
        #[arg(long)] preview: bool,
        #[arg(long)] json: bool,
    },
}

fn get_db_path() -> String {
    let demo_mode = std::env::var("TREELINE_DEMO_MODE").map(|v| matches!(v.to_lowercase().as_str(), "true" | "1" | "yes")).unwrap_or(false);
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    let db_dir = home.join(".treeline");
    if demo_mode { db_dir.join("demo.duckdb").to_string_lossy().to_string() }
    else { db_dir.join("treeline.duckdb").to_string_lossy().to_string() }
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();
    let cli = Cli::parse();

    let db_path = get_db_path();
    let repository: Arc<dyn Repository> = match DuckDBRepository::new(&db_path) {
        Ok(repo) => Arc::new(repo),
        Err(e) => { eprintln!("{}: {}", "Error".red().bold(), e); std::process::exit(1); }
    };

    let db_service = DbService::new(repository.clone());
    let result = db_service.initialize_db();
    if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }

    let account_service = Arc::new(AccountService::new(repository.clone()));
    let status_service = StatusService::new(repository.clone());
    let sync_service = SyncService::new(repository.clone(), account_service.clone());
    let backfill_service = BackfillService::new(repository.clone(), account_service.clone());
    let import_service = ImportService::new(repository.clone());

    match cli.command {
        Commands::Status { json } => {
            let result = status_service.get_status();
            if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
            let status = result.data.unwrap();
            if json { println!("{}", serde_json::to_string_pretty(&status).unwrap_or_default()); return; }

            println!("\n{}", "Treeline Status".bold());
            println!("{}", "═".repeat(50));
            println!("\n{}: {}", "Accounts".cyan(), status.total_accounts);
            println!("{}: {}", "Transactions".cyan(), status.total_transactions);
            println!("{}: {}", "Balance Snapshots".cyan(), status.total_snapshots);
            println!("{}: {}", "Integrations".cyan(), status.integration_names.join(", "));
            if let (Some(earliest), Some(latest)) = (&status.earliest_date, &status.latest_date) {
                println!("\n{}: {} to {}", "Date Range".cyan(), earliest, latest);
            }
            if !status.accounts.is_empty() {
                println!("\n{}", "Accounts".bold());
                let mut table = Table::new();
                table.load_preset(UTF8_FULL);
                table.set_header(vec!["Name", "Type", "Institution", "Balance", "Currency"]);
                for account in &status.accounts {
                    let balance_str = account.balance.map(|b| format!("{:.2}", b)).unwrap_or_else(|| "-".to_string());
                    let balance_cell = if let Some(b) = account.balance {
                        if b < Decimal::ZERO { Cell::new(&balance_str).fg(Color::Red) }
                        else { Cell::new(&balance_str).fg(Color::Green) }
                    } else { Cell::new(&balance_str) };
                    table.add_row(vec![
                        Cell::new(&account.name), Cell::new(account.account_type.as_deref().unwrap_or("-")),
                        Cell::new(account.institution_name.as_deref().unwrap_or("-")), balance_cell, Cell::new(&account.currency),
                    ]);
                }
                println!("{}", table);
            }
            println!();
        }

        Commands::Setup { integration, token } => {
            let integration_lower = integration.to_lowercase();
            match integration_lower.as_str() {
                "simplefin" | "demo" => {
                    println!("Setting up {} integration...", integration);
                    let mut options = HashMap::new();
                    if let Some(t) = token { options.insert("setupToken".to_string(), t); }
                    let result = sync_service.create_integration(&integration_lower, &options).await;
                    if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
                    println!("{} {} integration configured successfully!", "✓".green().bold(), integration);
                    println!("\nRun {} to sync your accounts.", "tl sync".cyan());
                }
                _ => { eprintln!("{}: Unknown integration: {}", "Error".red().bold(), integration); std::process::exit(1); }
            }
        }

        Commands::Sync { dry_run, json } => {
            if dry_run { println!("{} Running in dry-run mode (no changes will be saved)\n", "→".blue()); }
            let result = sync_service.sync_all_integrations(dry_run).await;
            if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
            let sync_result = result.data.unwrap();
            if json { println!("{}", serde_json::to_string_pretty(&sync_result).unwrap_or_default()); return; }

            for r in &sync_result.results {
                println!("\n{} {}", "Integration:".bold(), r.integration.cyan());
                if let Some(error) = &r.error { println!("  {}: {}", "Error".red().bold(), error); continue; }
                println!("  {}: {}", "Sync Type".cyan(), r.sync_type);
                if let Some(start_date) = &r.start_date {
                    if r.sync_type == "incremental" {
                        println!("  {}: {} {} (with 7-day overlap)", "Date Range".cyan(), start_date, "to now".dimmed());
                    } else {
                        println!("  {}: {} {} (last 90 days)", "Date Range".cyan(), start_date, "to now".dimmed());
                    }
                }
                println!("  {}: {}", "Accounts Synced".cyan(), r.accounts_synced);
                if let Some(stats) = &r.transaction_stats {
                    println!("  {}: {} discovered, {} new, {} skipped", "Transactions".cyan(), stats.discovered, stats.new, stats.skipped);
                }
                for warning in &r.provider_warnings { println!("  {}: {}", "Warning".yellow().bold(), warning); }
            }
            if !sync_result.new_accounts_without_type.is_empty() {
                println!("\n{}", "New accounts need type assignment:".yellow().bold());
                for account in &sync_result.new_accounts_without_type { println!("  - {} ({})", account.name, account.id); }
            }
            println!("\n{} {}!", "✓".green().bold(), if dry_run { "Dry run complete" } else { "Sync complete" });
        }

        Commands::Query { sql, format, file } => {
            let query = if let Some(sql_str) = sql { sql_str }
            else if let Some(file_path) = file { match std::fs::read_to_string(&file_path) { Ok(c) => c, Err(e) => { eprintln!("{}: {}", "Error".red().bold(), e); std::process::exit(1); } } }
            else { use std::io::{self, BufRead}; let stdin = io::stdin(); stdin.lock().lines().filter_map(|l| l.ok()).collect::<Vec<_>>().join("\n") };
            if query.is_empty() { eprintln!("{}: No SQL query provided", "Error".red().bold()); std::process::exit(1); }
            let result = db_service.execute_query(&query);
            if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
            let query_result = result.data.unwrap();
            match format.as_str() {
                "json" => {
                    let rows: Vec<serde_json::Value> = query_result.rows.iter().map(|row| {
                        let mut obj = serde_json::Map::new();
                        for (i, col) in query_result.columns.iter().enumerate() { if let Some(val) = row.get(i) { obj.insert(col.clone(), val.clone()); } }
                        serde_json::Value::Object(obj)
                    }).collect();
                    println!("{}", serde_json::to_string_pretty(&rows).unwrap_or_default());
                }
                "csv" => {
                    println!("{}", query_result.columns.join(","));
                    for row in &query_result.rows {
                        let values: Vec<String> = row.iter().map(|v| match v { serde_json::Value::String(s) => if s.contains(',') || s.contains('"') { format!("\"{}\"", s.replace('"', "\"\"")) } else { s.clone() }, serde_json::Value::Null => String::new(), _ => v.to_string() }).collect();
                        println!("{}", values.join(","));
                    }
                }
                _ => {
                    if query_result.rows.is_empty() { println!("No results"); return; }
                    let mut table = Table::new();
                    table.load_preset(UTF8_FULL);
                    table.set_header(&query_result.columns);
                    for row in &query_result.rows {
                        let cells: Vec<Cell> = row.iter().map(|v| Cell::new(match v { serde_json::Value::String(s) => s.clone(), serde_json::Value::Null => String::new(), _ => v.to_string() })).collect();
                        table.add_row(cells);
                    }
                    println!("{}\n{} rows returned", table, query_result.row_count);
                }
            }
        }

        Commands::New { resource_type, account_id, balance, date } => {
            match resource_type.as_str() {
                "balance" => {
                    let account_id = match account_id { Some(id) => id, None => { eprintln!("{}: --account-id is required", "Error".red().bold()); std::process::exit(1); } };
                    let balance_amount = match balance { Some(b) => b, None => { eprintln!("{}: --balance is required", "Error".red().bold()); std::process::exit(1); } };
                    let result = account_service.add_balance_snapshot(account_id, balance_amount, date);
                    if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
                    println!("{} Balance snapshot created!", "✓".green().bold());
                }
                _ => { eprintln!("{}: Unknown resource type: {}", "Error".red().bold(), resource_type); std::process::exit(1); }
            }
        }

        Commands::Backfill { resource_type, account_id, days, dry_run } => {
            match resource_type.as_str() {
                "balances" => {
                    if dry_run { println!("{} Running in dry-run mode\n", "→".blue()); }
                    let account_ids = account_id.map(|id| vec![id]);
                    let result = backfill_service.backfill_balances(account_ids, days, dry_run);
                    if !result.success { eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default()); std::process::exit(1); }
                    let r = result.data.unwrap();
                    println!("\n{} {}!", "✓".green().bold(), if dry_run { "Dry run complete" } else { "Backfill complete" });
                    println!("  Accounts processed: {}", r.accounts_processed);
                    println!("  Snapshots created: {}", r.snapshots_created);
                    println!("  Snapshots skipped: {}", r.snapshots_skipped);
                }
                _ => { eprintln!("{}: Unknown resource type: {}", "Error".red().bold(), resource_type); std::process::exit(1); }
            }
        }

        Commands::Import { file, account_id, date_column, amount_column, description_column, debit_column, credit_column, flip_signs, debit_negative, preview, json } => {
            let file_path = file.to_string_lossy().to_string();

            // Build column mapping - auto-detect if not specified
            let mapping = if date_column.is_some() || amount_column.is_some() || debit_column.is_some() {
                ColumnMapping {
                    date: date_column,
                    description: description_column,
                    amount: amount_column,
                    debit: debit_column,
                    credit: credit_column,
                    posted_date: None,
                }
            } else {
                // Auto-detect columns
                let detect_result = import_service.detect_columns(&file_path);
                if !detect_result.success {
                    eprintln!("{}: {}", "Error".red().bold(), detect_result.error.unwrap_or_default());
                    std::process::exit(1);
                }
                detect_result.data.unwrap()
            };

            // Validate we have required columns
            if mapping.date.is_none() {
                eprintln!("{}: Could not detect date column. Use --date-column to specify.", "Error".red().bold());
                std::process::exit(1);
            }
            if mapping.amount.is_none() && mapping.debit.is_none() && mapping.credit.is_none() {
                eprintln!("{}: Could not detect amount column. Use --amount-column or --debit-column/--credit-column.", "Error".red().bold());
                std::process::exit(1);
            }

            if preview {
                // Preview mode
                let result = import_service.preview(&file_path, &mapping, 5, flip_signs, debit_negative);
                if !result.success {
                    eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default());
                    std::process::exit(1);
                }
                let transactions = result.data.unwrap();

                if json {
                    println!("{}", serde_json::to_string_pretty(&transactions).unwrap_or_default());
                } else {
                    println!("\n{} (showing first {} rows)\n", "Preview".bold(), transactions.len());
                    let mut table = Table::new();
                    table.load_preset(UTF8_FULL);
                    table.set_header(vec!["Date", "Description", "Amount"]);
                    for tx in &transactions {
                        let amount_str = format!("{:.2}", tx.amount);
                        let amount_cell = if tx.amount < Decimal::ZERO {
                            Cell::new(&amount_str).fg(Color::Red)
                        } else {
                            Cell::new(&amount_str).fg(Color::Green)
                        };
                        table.add_row(vec![
                            Cell::new(tx.transaction_date.to_string()),
                            Cell::new(tx.description.as_deref().unwrap_or("-")),
                            amount_cell,
                        ]);
                    }
                    println!("{}", table);
                    println!("\nRun without --preview to import these transactions.");
                }
            } else {
                // Import mode
                let result = import_service.import_csv(&file_path, account_id, &mapping, flip_signs, debit_negative);
                if !result.success {
                    eprintln!("{}: {}", "Error".red().bold(), result.error.unwrap_or_default());
                    std::process::exit(1);
                }
                let import_result = result.data.unwrap();

                if json {
                    println!("{}", serde_json::to_string_pretty(&import_result).unwrap_or_default());
                } else {
                    println!("\n{} Import complete!", "✓".green().bold());
                    println!("  Transactions discovered: {}", import_result.transactions_discovered);
                    println!("  Transactions imported: {}", import_result.transactions_imported);
                    println!("  Transactions skipped: {}", import_result.transactions_skipped);
                }
            }
        }
    }
}
