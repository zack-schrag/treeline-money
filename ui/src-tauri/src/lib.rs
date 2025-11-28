use duckdb::Connection;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;

use tauri::Manager;

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
    let home_dir = dirs::home_dir().ok_or("Cannot find home directory")?;

    let treeline_dir = home_dir.join(".treeline");

    // Check for demo mode
    let demo_mode = std::env::var("TREELINE_DEMO_MODE")
        .map(|v| v.to_lowercase() == "true" || v == "1" || v == "yes")
        .unwrap_or(false);

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

    // Execute query and get arrow result
    let mut stmt = conn
        .prepare(&query)
        .map_err(|e| format!("Failed to prepare query: {}", e))?;

    let arrow = stmt.query_arrow([])
        .map_err(|e| format!("Failed to execute query: {}", e))?;

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
    let output = app
        .shell()
        .sidecar("tl")
        .unwrap() // TODO - handle error
        .args(["status", "--json"])
        .output()
        .await
        .map_err(|e| e.to_string())?;

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
        .invoke_handler(tauri::generate_handler![
            status,
            discover_plugins,
            get_plugins_dir,
            execute_query,
            read_plugin_config,
            write_plugin_config
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
