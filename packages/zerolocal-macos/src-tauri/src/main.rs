#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod docker;

use docker::{DockerManager, DockerStatus, PrerequisiteCheck};
use std::path::PathBuf;
use std::sync::Arc;
use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem,
};
use tokio::sync::Mutex;

struct AppState {
    docker_manager: Arc<Mutex<DockerManager>>,
}

#[tauri::command]
async fn check_prerequisites(state: tauri::State<'_, AppState>) -> Result<PrerequisiteCheck, String> {
    let manager = state.docker_manager.lock().await;
    manager
        .check_prerequisites()
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_status(state: tauri::State<'_, AppState>) -> Result<DockerStatus, String> {
    let manager = state.docker_manager.lock().await;
    manager.get_status().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn start_services(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let manager = state.docker_manager.lock().await;
    manager.start_services().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn stop_services(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let manager = state.docker_manager.lock().await;
    manager.stop_services().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn restart_services(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let manager = state.docker_manager.lock().await;
    manager.restart_services().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_logs(
    state: tauri::State<'_, AppState>,
    service: Option<String>,
) -> Result<String, String> {
    let manager = state.docker_manager.lock().await;
    manager.get_logs(service).await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn open_dashboard() -> Result<(), String> {
    open::that("http://localhost:3000").map_err(|e| e.to_string())
}

fn create_system_tray() -> SystemTray {
    let dashboard = CustomMenuItem::new("dashboard".to_string(), "Dashboard");
    let status = CustomMenuItem::new("status".to_string(), "Status: Checking...").disabled();
    let start = CustomMenuItem::new("start".to_string(), "Start Services");
    let stop = CustomMenuItem::new("stop".to_string(), "Stop Services");
    let restart = CustomMenuItem::new("restart".to_string(), "Restart Services");
    let logs = CustomMenuItem::new("logs".to_string(), "View Logs...");
    let preferences = CustomMenuItem::new("preferences".to_string(), "Preferences...");
    let update = CustomMenuItem::new("update".to_string(), "Check for Updates");
    let quit = CustomMenuItem::new("quit".to_string(), "Quit ZeroLocal");

    let tray_menu = SystemTrayMenu::new()
        .add_item(dashboard)
        .add_item(status)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(start)
        .add_item(stop)
        .add_item(restart)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(logs)
        .add_item(preferences)
        .add_item(update)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);

    SystemTray::new().with_menu(tray_menu)
}

fn handle_system_tray_event(app: &tauri::AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
            "dashboard" => {
                if let Err(e) = open::that("http://localhost:3000") {
                    log::error!("Failed to open dashboard: {}", e);
                }
            }
            "start" => {
                let app = app.clone();
                tauri::async_runtime::spawn(async move {
                    let state: tauri::State<AppState> = app.state();
                    if let Err(e) = start_services(state).await {
                        log::error!("Failed to start services: {}", e);
                    }
                });
            }
            "stop" => {
                let app = app.clone();
                tauri::async_runtime::spawn(async move {
                    let state: tauri::State<AppState> = app.state();
                    if let Err(e) = stop_services(state).await {
                        log::error!("Failed to stop services: {}", e);
                    }
                });
            }
            "restart" => {
                let app = app.clone();
                tauri::async_runtime::spawn(async move {
                    let state: tauri::State<AppState> = app.state();
                    if let Err(e) = restart_services(state).await {
                        log::error!("Failed to restart services: {}", e);
                    }
                });
            }
            "logs" => {
                if let Some(window) = app.get_window("main") {
                    window.show().unwrap();
                    window.set_focus().unwrap();
                }
            }
            "preferences" => {
                if let Some(window) = app.get_window("main") {
                    window.show().unwrap();
                    window.set_focus().unwrap();
                    window.emit("show-preferences", ()).unwrap();
                }
            }
            "update" => {
                if let Some(window) = app.get_window("main") {
                    window.show().unwrap();
                    window.set_focus().unwrap();
                    window.emit("check-updates", ()).unwrap();
                }
            }
            "quit" => {
                std::process::exit(0);
            }
            _ => {}
        },
        _ => {}
    }
}

fn main() {
    env_logger::init();

    let compose_path = PathBuf::from("../../zerodb-local/docker-compose.yml");
    let docker_manager = DockerManager::new(compose_path).expect("Failed to initialize Docker manager");

    let app_state = AppState {
        docker_manager: Arc::new(Mutex::new(docker_manager)),
    };

    let system_tray = create_system_tray();

    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(handle_system_tray_event)
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            check_prerequisites,
            get_status,
            start_services,
            stop_services,
            restart_services,
            get_logs,
            open_dashboard,
        ])
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            window.hide().unwrap();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
