// Prevents an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

pub mod sidecar;
pub mod tray;

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde::Serialize;
use tauri::{Emitter, Manager, State};
use tokio::time;

// ---------------------------------------------------------------------------
// Shared app state
// ---------------------------------------------------------------------------

#[derive(Default)]
pub struct AppState {
    pub server_running: AtomicBool,
}

// ---------------------------------------------------------------------------
// Tauri commands exposed to the frontend
// ---------------------------------------------------------------------------

#[derive(Serialize)]
pub struct ServerStatus {
    running: bool,
    url: String,
    backend: String,
}

#[tauri::command]
async fn get_server_status(state: State<'_, Arc<AppState>>) -> Result<ServerStatus, String> {
    let running = sidecar::is_running_async().await;
    state.server_running.store(running, Ordering::Relaxed);
    Ok(ServerStatus {
        running,
        url: "http://127.0.0.1:8000".to_string(),
        backend: "zerodb-server".to_string(),
    })
}

#[tauri::command]
async fn start_server(state: State<'_, Arc<AppState>>) -> Result<String, String> {
    if state.server_running.load(Ordering::Relaxed) {
        return Ok("Server is already running".to_string());
    }

    let data_dir = default_data_dir();
    sidecar::start_sidecar(&data_dir, 8000)?;

    // Give the process a moment to bind the port before we mark it healthy.
    time::sleep(Duration::from_millis(800)).await;

    let running = sidecar::is_running_async().await;
    state.server_running.store(running, Ordering::Relaxed);

    if running {
        Ok("Server started".to_string())
    } else {
        Err("Server process started but health check failed".to_string())
    }
}

#[tauri::command]
async fn stop_server(state: State<'_, Arc<AppState>>) -> Result<String, String> {
    sidecar::stop_sidecar()?;
    state.server_running.store(false, Ordering::Relaxed);
    Ok("Server stopped".to_string())
}

#[tauri::command]
fn get_data_dir() -> String {
    default_data_dir()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

pub fn default_data_dir() -> String {
    dirs_sys::home_dir()
        .map(|h| h.join(".zerodb").to_string_lossy().into_owned())
        .unwrap_or_else(|| ".zerodb".to_string())
}

// ---------------------------------------------------------------------------
// Health-polling background task
// ---------------------------------------------------------------------------

fn spawn_health_monitor(app_handle: tauri::AppHandle, state: Arc<AppState>) {
    tauri::async_runtime::spawn(async move {
        let mut interval = time::interval(Duration::from_secs(5));
        loop {
            interval.tick().await;
            let running = sidecar::is_running_async().await;
            let was_running = state.server_running.swap(running, Ordering::Relaxed);

            if running != was_running {
                // Status changed — update tray icon tooltip.
                tray::set_tray_status(&app_handle, running);

                // Notify the frontend window if visible.
                if let Some(window) = app_handle.get_webview_window("main") {
                    let _ = window.emit("server-status-changed", running);
                }
            }
        }
    });
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    env_logger::init();

    let state = Arc::new(AppState::default());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(state.clone())
        .setup(move |app| {
            // Build system tray.
            tray::build_tray(&app.handle())?;

            // Auto-start the API sidecar.
            let data_dir = default_data_dir();
            match sidecar::start_sidecar(&data_dir, 8000) {
                Ok(_) => log::info!("ZeroDB API sidecar started"),
                Err(e) => log::warn!("Could not auto-start sidecar: {e}"),
            }

            // Launch health monitor.
            spawn_health_monitor(app.handle().clone(), state.clone());

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Hide to tray instead of quitting.
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_server_status,
            start_server,
            stop_server,
            get_data_dir,
        ])
        .run(tauri::generate_context!())
        .expect("error while running zerodb desktop");
}
