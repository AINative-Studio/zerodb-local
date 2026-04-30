use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, Runtime,
};

use crate::AppState;
use std::sync::Arc;

/// Build the system tray with its initial menu.
///
/// Menu layout:
///   Open Dashboard
///   ──────────────
///   Start Server
///   Stop Server
///   ──────────────
///   About ZeroDB
///   Quit
pub fn build_tray<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let open_item = MenuItem::with_id(app, "open", "Open Dashboard", true, None::<&str>)?;
    let sep1 = PredefinedMenuItem::separator(app)?;
    let start_item = MenuItem::with_id(app, "start_server", "Start Server", true, None::<&str>)?;
    let stop_item = MenuItem::with_id(app, "stop_server", "Stop Server", true, None::<&str>)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let about_item = MenuItem::with_id(app, "about", "About ZeroDB v0.2.0", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(
        app,
        &[
            &open_item,
            &sep1,
            &start_item,
            &stop_item,
            &sep2,
            &about_item,
            &quit_item,
        ],
    )?;

    TrayIconBuilder::with_id("main-tray")
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .tooltip("ZeroDB — local vector database")
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| handle_menu_event(app, event.id().as_ref()))
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                show_main_window(app);
            }
        })
        .build(app)?;

    Ok(())
}

/// Update the tray tooltip to reflect server health.
pub fn set_tray_status<R: Runtime>(app: &AppHandle<R>, running: bool) {
    if let Some(tray) = app.tray_by_id("main-tray") {
        let tooltip = if running {
            "ZeroDB — server running"
        } else {
            "ZeroDB — server stopped"
        };
        let _ = tray.set_tooltip(Some(tooltip));
    }
}

fn handle_menu_event<R: Runtime>(app: &AppHandle<R>, id: &str) {
    match id {
        "open" => show_main_window(app),
        "start_server" => {
            let app = app.clone();
            tauri::async_runtime::spawn(async move {
                let state = app.state::<Arc<AppState>>();
                let data_dir = crate::default_data_dir();
                match crate::sidecar::start_sidecar(&data_dir, 8000) {
                    Ok(_) => {
                        tokio::time::sleep(std::time::Duration::from_millis(800)).await;
                        let running = crate::sidecar::is_running_async().await;
                        state.server_running.store(running, std::sync::atomic::Ordering::Relaxed);
                        set_tray_status(&app, running);
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.emit("server-status-changed", running);
                        }
                    }
                    Err(e) => log::error!("Failed to start server from tray: {e}"),
                }
            });
        }
        "stop_server" => {
            let app = app.clone();
            tauri::async_runtime::spawn(async move {
                let state = app.state::<Arc<AppState>>();
                if let Err(e) = crate::sidecar::stop_sidecar() {
                    log::error!("Failed to stop server from tray: {e}");
                }
                state.server_running.store(false, std::sync::atomic::Ordering::Relaxed);
                set_tray_status(&app, false);
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.emit("server-status-changed", false);
                }
            });
        }
        "about" => show_main_window(app),
        "quit" => {
            let _ = crate::sidecar::stop_sidecar();
            app.exit(0);
        }
        _ => {}
    }
}

pub fn show_main_window<R: Runtime>(app: &AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}
