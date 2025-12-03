use duckdb::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Value as JsonValue;
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri_plugin_shell::process::Output;
use tauri_plugin_shell::ShellExt;

#[cfg(debug_assertions)]
use tauri::Manager;

/// Run the CLI with the given arguments.
/// In dev mode (TL_DEV_CLI=1), runs `uv run tl` from the cli directory.
/// Otherwise uses the bundled sidecar binary.
async fn run_cli<I, S>(app: &AppHandle, args: I) -> Result<Output, String>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let args: Vec<String> = args.into_iter().map(|s| s.as_ref().to_string()).collect();

    let dev_cli = std::env::var("TL_DEV_CLI")
        .map(|v| v == "1" || v.to_lowercase() == "true")
        .unwrap_or(false);

    if dev_cli {
        // Dev mode: run `uv run tl` from the cli directory
        let cli_dir = std::env::var("TL_CLI_DIR")
            .unwrap_or_else(|_| {
                // Default: assume cli/ is sibling to ui/
                let manifest_dir = env!("CARGO_MANIFEST_DIR");
                PathBuf::from(manifest_dir)
                    .parent()  // ui/
                    .and_then(|p| p.parent())  // repo root
                    .map(|p| p.join("cli"))
                    .unwrap_or_else(|| PathBuf::from("../cli"))
                    .to_string_lossy()
                    .to_string()
            });

        app.shell()
            .command("uv")
            .args(["run", "tl"])
            .args(&args)
            .current_dir(&cli_dir)
            .output()
            .await
            .map_err(|e| format!("Failed to run dev CLI: {}", e))
    } else {
        // Production: use bundled sidecar
        app.shell()
            .sidecar("tl")
            .map_err(|e| format!("Failed to get sidecar: {}", e))?
            .args(&args)
            .output()
            .await
            .map_err(|e| format!("Failed to run CLI: {}", e))
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct PluginManifest {
    id: String,
    name: String,
    version: String,
    description: String,
    author: String,
    main: String,
}

#[derive(Debug, Serialize)]
struct ExternalPlugin {
    manifest: PluginManifest,
    path: String,
}

#[derive(Debug, Serialize)]
struct QueryResult {
    columns: Vec<String>,
    rows: Vec<Vec<serde_json::Value>>,
    row_count: usize,
}

/// Get the path to the DuckDB database file.
/// Centralized location for database path logic.
fn get_db_path() -> Result<PathBuf, String> {
    let treeline_dir = get_treeline_dir()?;

    // Check for demo mode (uses same logic as get_demo_mode)
    let demo_mode = get_demo_mode();

    let db_filename = if demo_mode {
        "demo.duckdb"
    } else {
        "treeline.duckdb"
    };
    let db_path = treeline_dir.join(db_filename);

    Ok(db_path)
}

#[tauri::command]
fn execute_query(query: String, readonly: Option<bool>) -> Result<String, String> {
    // Get database path
    let db_path = get_db_path()?;

    // Open connection with appropriate access mode
    let readonly = readonly.unwrap_or(true);
    let conn = if readonly {
        let config = duckdb::Config::default()
            .access_mode(duckdb::AccessMode::ReadOnly)
            .map_err(|e| format!("Failed to configure database: {}", e))?;
        Connection::open_with_flags(&db_path, config)
    } else {
        Connection::open(&db_path)
    }
    .map_err(|e| format!("Failed to open database: {}", e))?;

    // Check if this is a SELECT-like query or a write query (UPDATE/INSERT/DELETE)
    let trimmed = query.trim().to_uppercase();
    let _is_select = trimmed.starts_with("SELECT")
        || trimmed.starts_with("WITH")  // CTEs that return results
        || trimmed.starts_with("DESCRIBE")
        || trimmed.starts_with("SHOW");
    let is_write = trimmed.starts_with("UPDATE")
        || trimmed.starts_with("INSERT")
        || trimmed.starts_with("DELETE")
        || trimmed.starts_with("CREATE")
        || trimmed.starts_with("DROP")
        || trimmed.starts_with("ALTER");

    if is_write {
        // For write queries, use execute() which returns affected row count
        let affected = conn.execute(&query, [])
            .map_err(|e| e.to_string())?;

        let result = QueryResult {
            columns: vec!["affected_rows".to_string()],
            row_count: 1,
            rows: vec![vec![serde_json::json!(affected)]],
        };

        return serde_json::to_string(&result)
            .map_err(|e| format!("Failed to serialize result: {}", e));
    }

    // Execute query and get arrow result
    let mut stmt = conn
        .prepare(&query)
        .map_err(|e| e.to_string())?;

    let arrow = stmt.query_arrow([])
        .map_err(|e| e.to_string())?;

    // Get column names from schema
    let schema = arrow.get_schema();
    let columns: Vec<String> = schema.fields().iter()
        .map(|f| f.name().clone())
        .collect();

    // Convert arrow batches to JSON rows
    let mut rows: Vec<Vec<serde_json::Value>> = Vec::new();

    for batch in arrow {
        let num_rows = batch.num_rows();
        let num_cols = batch.num_columns();

        for row_idx in 0..num_rows {
            let mut row_values = Vec::new();
            for col_idx in 0..num_cols {
                let column = batch.column(col_idx);
                let value = arrow_value_to_json(column, row_idx);
                row_values.push(value);
            }
            rows.push(row_values);
        }
    }

    let result = QueryResult {
        columns,
        row_count: rows.len(),
        rows,
    };

    // Serialize to JSON string to match CLI format
    serde_json::to_string(&result)
        .map_err(|e| format!("Failed to serialize result: {}", e))
}

// Helper function to convert Arrow array value to JSON
fn arrow_value_to_json(column: &dyn arrow::array::Array, row_idx: usize) -> serde_json::Value {
    use arrow::array::*;
    use arrow::datatypes::*;

    if column.is_null(row_idx) {
        return serde_json::Value::Null;
    }

    match column.data_type() {
        DataType::Boolean => {
            let array = column.as_any().downcast_ref::<BooleanArray>().unwrap();
            serde_json::Value::Bool(array.value(row_idx))
        }
        DataType::Int8 | DataType::Int16 | DataType::Int32 | DataType::Int64 => {
            if let Some(array) = column.as_any().downcast_ref::<Int8Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<Int16Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<Int32Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<Int64Array>() {
                serde_json::json!(array.value(row_idx))
            } else {
                serde_json::Value::Null
            }
        }
        DataType::UInt8 | DataType::UInt16 | DataType::UInt32 | DataType::UInt64 => {
            if let Some(array) = column.as_any().downcast_ref::<UInt8Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<UInt16Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<UInt32Array>() {
                serde_json::json!(array.value(row_idx))
            } else if let Some(array) = column.as_any().downcast_ref::<UInt64Array>() {
                serde_json::json!(array.value(row_idx))
            } else {
                serde_json::Value::Null
            }
        }
        DataType::Float32 => {
            let array = column.as_any().downcast_ref::<Float32Array>().unwrap();
            serde_json::json!(array.value(row_idx))
        }
        DataType::Float64 => {
            let array = column.as_any().downcast_ref::<Float64Array>().unwrap();
            serde_json::json!(array.value(row_idx))
        }
        DataType::Decimal128(_, scale) | DataType::Decimal256(_, scale) => {
            // DuckDB uses Decimal128 for DECIMAL type
            if let Some(array) = column.as_any().downcast_ref::<arrow::array::Decimal128Array>() {
                let value = array.value(row_idx);
                let scale_factor = 10_i128.pow(*scale as u32);
                let float_value = value as f64 / scale_factor as f64;
                serde_json::json!(float_value)
            } else if let Some(array) = column.as_any().downcast_ref::<arrow::array::Decimal256Array>() {
                // For Decimal256, convert to string to avoid precision loss
                serde_json::Value::String(array.value(row_idx).to_string())
            } else {
                serde_json::Value::Null
            }
        }
        DataType::Utf8 | DataType::LargeUtf8 => {
            if let Some(array) = column.as_any().downcast_ref::<StringArray>() {
                serde_json::Value::String(array.value(row_idx).to_string())
            } else if let Some(array) = column.as_any().downcast_ref::<LargeStringArray>() {
                serde_json::Value::String(array.value(row_idx).to_string())
            } else {
                serde_json::Value::Null
            }
        }
        DataType::Date32 => {
            let array = column.as_any().downcast_ref::<arrow::array::Date32Array>().unwrap();
            let days_since_epoch = array.value(row_idx);
            // Convert days since epoch to date string
            let date = chrono::NaiveDate::from_ymd_opt(1970, 1, 1)
                .unwrap()
                .checked_add_signed(chrono::Duration::days(days_since_epoch as i64))
                .unwrap();
            serde_json::Value::String(date.format("%Y-%m-%d").to_string())
        }
        DataType::Date64 => {
            let array = column.as_any().downcast_ref::<arrow::array::Date64Array>().unwrap();
            let millis_since_epoch = array.value(row_idx);
            let date = chrono::DateTime::from_timestamp_millis(millis_since_epoch)
                .unwrap()
                .naive_utc()
                .date();
            serde_json::Value::String(date.format("%Y-%m-%d").to_string())
        }
        DataType::Timestamp(unit, _tz) => {
            if let Some(array) = column.as_any().downcast_ref::<arrow::array::TimestampSecondArray>() {
                let timestamp = array.value(row_idx);
                let dt = chrono::DateTime::from_timestamp(timestamp, 0).unwrap();
                serde_json::Value::String(dt.to_rfc3339())
            } else if let Some(array) = column.as_any().downcast_ref::<arrow::array::TimestampMillisecondArray>() {
                let timestamp = array.value(row_idx);
                let dt = chrono::DateTime::from_timestamp_millis(timestamp).unwrap();
                serde_json::Value::String(dt.to_rfc3339())
            } else if let Some(array) = column.as_any().downcast_ref::<arrow::array::TimestampMicrosecondArray>() {
                let timestamp = array.value(row_idx);
                let dt = chrono::DateTime::from_timestamp_micros(timestamp).unwrap();
                serde_json::Value::String(dt.to_rfc3339())
            } else if let Some(array) = column.as_any().downcast_ref::<arrow::array::TimestampNanosecondArray>() {
                let timestamp = array.value(row_idx);
                let dt = chrono::DateTime::from_timestamp_nanos(timestamp);
                serde_json::Value::String(dt.to_rfc3339())
            } else {
                serde_json::Value::String(format!("Timestamp({:?})", unit))
            }
        }
        DataType::List(_) | DataType::LargeList(_) => {
            if let Some(array) = column.as_any().downcast_ref::<ListArray>() {
                let list_value = array.value(row_idx);
                let list_as_string_array = list_value.as_any().downcast_ref::<StringArray>();

                if let Some(string_array) = list_as_string_array {
                    let values: Vec<String> = (0..string_array.len())
                        .map(|i| string_array.value(i).to_string())
                        .collect();
                    serde_json::json!(values)
                } else {
                    // Fallback: convert to debug string
                    serde_json::Value::String(format!("{:?}", list_value))
                }
            } else {
                serde_json::Value::Null
            }
        }
        _ => {
            // For unsupported types, return as debug string
            serde_json::Value::String(format!("{:?}", column))
        }
    }
}

#[tauri::command]
async fn status(app: AppHandle) -> Result<String, String> {
    let output = run_cli(&app, &["status", "--json"]).await?;

    // Return raw JSON string, let frontend parse it
    String::from_utf8(output.stdout).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_plugins_dir() -> Result<String, String> {
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;

    let plugins_dir = home_dir.join(".treeline").join("plugins");

    // Create directory if it doesn't exist
    if !plugins_dir.exists() {
        fs::create_dir_all(&plugins_dir)
            .map_err(|e| format!("Failed to create plugins directory: {}", e))?;
    }

    plugins_dir
        .to_str()
        .map(|s| s.to_string())
        .ok_or_else(|| "Invalid plugins directory path".to_string())
}

/// Get the path to the treeline directory (~/.treeline)
fn get_treeline_dir() -> Result<PathBuf, String> {
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;
    Ok(home_dir.join(".treeline"))
}

/// Read the unified settings.json file
#[tauri::command]
fn read_settings() -> Result<String, String> {
    let treeline_dir = get_treeline_dir()?;
    let settings_path = treeline_dir.join("settings.json");

    if !settings_path.exists() {
        // Return default settings structure
        let default_settings = serde_json::json!({
            "app": {
                "theme": "dark",
                "lastSyncDate": null,
                "autoSyncOnStartup": true
            },
            "plugins": {}
        });
        return Ok(default_settings.to_string());
    }

    fs::read_to_string(&settings_path)
        .map_err(|e| format!("Failed to read settings: {}", e))
}

/// Write the unified settings.json file
#[tauri::command]
fn write_settings(content: String) -> Result<(), String> {
    let treeline_dir = get_treeline_dir()?;

    // Ensure treeline directory exists
    if !treeline_dir.exists() {
        fs::create_dir_all(&treeline_dir)
            .map_err(|e| format!("Failed to create treeline directory: {}", e))?;
    }

    let settings_path = treeline_dir.join("settings.json");

    // Validate JSON before writing
    serde_json::from_str::<JsonValue>(&content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    fs::write(&settings_path, content)
        .map_err(|e| format!("Failed to write settings: {}", e))
}

/// Read plugin-specific state file (for runtime state, not user settings)
#[tauri::command]
fn read_plugin_state(plugin_id: String) -> Result<String, String> {
    let treeline_dir = get_treeline_dir()?;
    let state_path = treeline_dir
        .join("plugins")
        .join(&plugin_id)
        .join("state.json");

    if !state_path.exists() {
        return Ok("null".to_string());
    }

    fs::read_to_string(&state_path)
        .map_err(|e| format!("Failed to read plugin state: {}", e))
}

/// Write plugin-specific state file (for runtime state, not user settings)
#[tauri::command]
fn write_plugin_state(plugin_id: String, content: String) -> Result<(), String> {
    let treeline_dir = get_treeline_dir()?;
    let plugin_dir = treeline_dir.join("plugins").join(&plugin_id);

    // Create plugin directory if it doesn't exist
    if !plugin_dir.exists() {
        fs::create_dir_all(&plugin_dir)
            .map_err(|e| format!("Failed to create plugin directory: {}", e))?;
    }

    let state_path = plugin_dir.join("state.json");

    fs::write(&state_path, content)
        .map_err(|e| format!("Failed to write plugin state: {}", e))
}

/// Get current demo mode status from config.json
#[tauri::command]
fn get_demo_mode() -> bool {
    // First check env var (for CI/testing)
    if let Ok(env_val) = std::env::var("TREELINE_DEMO_MODE") {
        let lower = env_val.to_lowercase();
        if lower == "true" || lower == "1" || lower == "yes" {
            return true;
        }
        if lower == "false" || lower == "0" || lower == "no" {
            return false;
        }
    }

    // Fall back to config file (same as CLI)
    let config_path = match get_treeline_dir() {
        Ok(dir) => dir.join("config.json"),
        Err(_) => return false,
    };

    if !config_path.exists() {
        return false;
    }

    match fs::read_to_string(&config_path) {
        Ok(content) => {
            if let Ok(config) = serde_json::from_str::<JsonValue>(&content) {
                config.get("demo_mode").and_then(|v| v.as_bool()).unwrap_or(false)
            } else {
                false
            }
        }
        Err(_) => false,
    }
}

/// Set demo mode in config.json (same file the CLI uses)
#[tauri::command]
fn set_demo_mode(enabled: bool) -> Result<(), String> {
    let treeline_dir = get_treeline_dir()?;

    // Ensure directory exists
    if !treeline_dir.exists() {
        fs::create_dir_all(&treeline_dir)
            .map_err(|e| format!("Failed to create treeline directory: {}", e))?;
    }

    let config_path = treeline_dir.join("config.json");

    // Read existing config or create new
    let mut config: serde_json::Map<String, JsonValue> = if config_path.exists() {
        let content = fs::read_to_string(&config_path)
            .map_err(|e| format!("Failed to read config: {}", e))?;
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        serde_json::Map::new()
    };

    // Update demo_mode
    config.insert("demo_mode".to_string(), JsonValue::Bool(enabled));

    // Write back
    let content = serde_json::to_string_pretty(&config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;
    fs::write(&config_path, content)
        .map_err(|e| format!("Failed to write config: {}", e))?;

    Ok(())
}

/// Run the sync command via CLI
#[tauri::command]
async fn run_sync(app: AppHandle, dry_run: Option<bool>) -> Result<String, String> {
    let mut args = vec!["sync", "--json"];
    if dry_run.unwrap_or(false) {
        args.push("--dry-run");
    }

    let output = run_cli(&app, &args).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Sync failed: {}", stderr));
    }

    String::from_utf8(output.stdout)
        .map_err(|e| format!("Failed to parse sync output: {}", e))
}

/// Enable demo mode via CLI (sets up demo integration and syncs demo data)
#[tauri::command]
async fn enable_demo(app: AppHandle) -> Result<(), String> {
    let output = run_cli(&app, &["demo", "on"]).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let error_msg = if !stdout.is_empty() { stdout } else { stderr };
        return Err(format!("Failed to enable demo mode: {}", error_msg));
    }

    Ok(())
}

/// Disable demo mode via CLI
#[tauri::command]
async fn disable_demo(app: AppHandle) -> Result<(), String> {
    let output = run_cli(&app, &["demo", "off"]).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let error_msg = if !stdout.is_empty() { stdout } else { stderr };
        return Err(format!("Failed to disable demo mode: {}", error_msg));
    }

    Ok(())
}

/// Preview CSV import via CLI
/// Returns JSON with detected columns and preview transactions
#[tauri::command]
async fn import_csv_preview(
    app: AppHandle,
    file_path: String,
    account_id: String,
    date_column: Option<String>,
    amount_column: Option<String>,
    description_column: Option<String>,
    debit_column: Option<String>,
    credit_column: Option<String>,
    flip_signs: bool,
    debit_negative: bool,
) -> Result<String, String> {
    let mut args = vec![
        "import".to_string(),
        file_path,
        "--account-id".to_string(),
        account_id,
        "--preview".to_string(),
        "--json".to_string(),
    ];

    if let Some(col) = date_column {
        args.push("--date-column".to_string());
        args.push(col);
    }
    if let Some(col) = amount_column {
        args.push("--amount-column".to_string());
        args.push(col);
    }
    if let Some(col) = description_column {
        args.push("--description-column".to_string());
        args.push(col);
    }
    if let Some(col) = debit_column {
        args.push("--debit-column".to_string());
        args.push(col);
    }
    if let Some(col) = credit_column {
        args.push("--credit-column".to_string());
        args.push(col);
    }
    if flip_signs {
        args.push("--flip-signs".to_string());
    }
    if debit_negative {
        args.push("--debit-negative".to_string());
    }

    let output = run_cli(&app, &args).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Import preview failed: {}", stderr));
    }

    String::from_utf8(output.stdout)
        .map_err(|e| format!("Failed to parse import output: {}", e))
}

/// Execute CSV import via CLI
#[tauri::command]
async fn import_csv_execute(
    app: AppHandle,
    file_path: String,
    account_id: String,
    date_column: Option<String>,
    amount_column: Option<String>,
    description_column: Option<String>,
    debit_column: Option<String>,
    credit_column: Option<String>,
    flip_signs: bool,
    debit_negative: bool,
) -> Result<String, String> {
    let mut args = vec![
        "import".to_string(),
        file_path,
        "--account-id".to_string(),
        account_id,
        "--json".to_string(),
    ];

    if let Some(col) = date_column {
        args.push("--date-column".to_string());
        args.push(col);
    }
    if let Some(col) = amount_column {
        args.push("--amount-column".to_string());
        args.push(col);
    }
    if let Some(col) = description_column {
        args.push("--description-column".to_string());
        args.push(col);
    }
    if let Some(col) = debit_column {
        args.push("--debit-column".to_string());
        args.push(col);
    }
    if let Some(col) = credit_column {
        args.push("--credit-column".to_string());
        args.push(col);
    }
    if flip_signs {
        args.push("--flip-signs".to_string());
    }
    if debit_negative {
        args.push("--debit-negative".to_string());
    }

    let output = run_cli(&app, &args).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Import failed: {}", stderr));
    }

    String::from_utf8(output.stdout)
        .map_err(|e| format!("Failed to parse import output: {}", e))
}

/// Open file picker dialog for CSV files
#[tauri::command]
async fn pick_csv_file(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    let file = app
        .dialog()
        .file()
        .add_filter("CSV Files", &["csv"])
        .blocking_pick_file();

    Ok(file.map(|f| f.to_string()))
}

/// Get CSV headers for column mapping
#[tauri::command]
async fn get_csv_headers(file_path: String) -> Result<Vec<String>, String> {
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    let file = File::open(&file_path)
        .map_err(|e| format!("Failed to open file: {}", e))?;

    let reader = BufReader::new(file);
    let first_line = reader.lines().next()
        .ok_or("CSV file is empty")?
        .map_err(|e| format!("Failed to read first line: {}", e))?;

    // Parse CSV header line
    let headers: Vec<String> = first_line
        .split(',')
        .map(|h| h.trim().trim_matches('"').to_string())
        .collect();

    Ok(headers)
}

/// Setup SimpleFIN integration via CLI
#[tauri::command]
async fn setup_simplefin(app: AppHandle, token: String) -> Result<String, String> {
    let output = run_cli(&app, &["setup", "simplefin", "--token", &token]).await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        // CLI outputs error messages to stdout with rich formatting
        let error_msg = if !stdout.is_empty() {
            stdout.to_string()
        } else {
            stderr.to_string()
        };
        return Err(format!("Setup failed: {}", error_msg));
    }

    Ok("SimpleFIN integration configured successfully".to_string())
}

#[tauri::command]
fn read_plugin_config(plugin_id: String, filename: String) -> Result<String, String> {
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;
    let config_path = home_dir
        .join(".treeline")
        .join("plugins")
        .join(&plugin_id)
        .join(&filename);

    if !config_path.exists() {
        return Ok("null".to_string());
    }

    fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to read config: {}", e))
}

#[tauri::command]
fn write_plugin_config(plugin_id: String, filename: String, content: String) -> Result<(), String> {
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;
    let plugin_dir = home_dir
        .join(".treeline")
        .join("plugins")
        .join(&plugin_id);

    // Create plugin directory if it doesn't exist
    if !plugin_dir.exists() {
        fs::create_dir_all(&plugin_dir)
            .map_err(|e| format!("Failed to create plugin directory: {}", e))?;
    }

    let config_path = plugin_dir.join(&filename);

    // Create parent directories if filename contains subdirectories (e.g., "months/2025-12.json")
    if let Some(parent) = config_path.parent() {
        if !parent.exists() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create config directory: {}", e))?;
        }
    }

    fs::write(&config_path, content)
        .map_err(|e| format!("Failed to write config: {}", e))
}

#[tauri::command]
fn discover_plugins() -> Result<Vec<ExternalPlugin>, String> {
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;

    let plugins_dir = home_dir.join(".treeline").join("plugins");

    // Create directory if it doesn't exist
    if !plugins_dir.exists() {
        fs::create_dir_all(&plugins_dir)
            .map_err(|e| format!("Failed to create plugins directory: {}", e))?;
        return Ok(Vec::new());
    }

    let mut plugins = Vec::new();

    // Read all subdirectories in plugins directory
    let entries = fs::read_dir(&plugins_dir)
        .map_err(|e| format!("Failed to read plugins directory: {}", e))?;

    for entry in entries {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();

        if path.is_dir() {
            let manifest_path = path.join("manifest.json");

            if manifest_path.exists() {
                // Read and parse manifest
                let manifest_content = fs::read_to_string(&manifest_path).map_err(|e| {
                    format!("Failed to read manifest at {:?}: {}", manifest_path, e)
                })?;

                let manifest: PluginManifest =
                    serde_json::from_str(&manifest_content).map_err(|e| {
                        format!("Failed to parse manifest at {:?}: {}", manifest_path, e)
                    })?;

                // Get the plugin directory name
                let plugin_dir_name = path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .ok_or_else(|| format!("Invalid plugin directory name: {:?}", path))?;

                plugins.push(ExternalPlugin {
                    manifest,
                    path: format!("plugins/{}/{}", plugin_dir_name, "index.js"),
                });
            }
        }
    }

    Ok(plugins)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|_app| {
            #[cfg(debug_assertions)] // This line ensures DevTools only opens in debug builds
            {
                let window = _app.get_webview_window("main").unwrap();
                window.open_devtools();
                // window.close_devtools();
            }
            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            status,
            discover_plugins,
            get_plugins_dir,
            execute_query,
            read_plugin_config,
            write_plugin_config,
            read_settings,
            write_settings,
            read_plugin_state,
            write_plugin_state,
            run_sync,
            get_demo_mode,
            set_demo_mode,
            enable_demo,
            disable_demo,
            import_csv_preview,
            import_csv_execute,
            pick_csv_file,
            get_csv_headers,
            setup_simplefin
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
