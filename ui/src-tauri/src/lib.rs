use tauri::AppHandle;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

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


#[tauri::command]
async fn status(app: AppHandle) -> Result<String, String> {
    let output = app.shell()
        .sidecar("tl")
        .unwrap() // TODO - handle error
        .args(["status", "--json"])
        .output()
        .await
        .map_err(|e| e.to_string())?;

    // Return raw JSON string, let frontend parse it
    String::from_utf8(output.stdout)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_plugins_dir() -> Result<String, String> {
    let home_dir = dirs::home_dir()
        .ok_or("Cannot find home directory")?;

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
fn discover_plugins() -> Result<Vec<ExternalPlugin>, String> {
    let home_dir = dirs::home_dir()
        .ok_or("Cannot find home directory")?;

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
                let manifest_content = fs::read_to_string(&manifest_path)
                    .map_err(|e| format!("Failed to read manifest at {:?}: {}", manifest_path, e))?;

                let manifest: PluginManifest = serde_json::from_str(&manifest_content)
                    .map_err(|e| format!("Failed to parse manifest at {:?}: {}", manifest_path, e))?;

                // Get the plugin directory name
                let plugin_dir_name = path.file_name()
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
        .setup(|app| {
            #[cfg(debug_assertions)] // This line ensures DevTools only opens in debug builds
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
                // window.close_devtools();
            }
            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![status, discover_plugins, get_plugins_dir])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
