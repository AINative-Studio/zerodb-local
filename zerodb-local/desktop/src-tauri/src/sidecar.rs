use std::process::{Child, Command};
use std::sync::Mutex;

/// Global handle to the spawned sidecar process.
static SIDECAR: Mutex<Option<Child>> = Mutex::new(None);

const API_HEALTH_URL: &str = "http://127.0.0.1:8000/health";

/// Spawn the zerodb API server.
///
/// Resolution order:
///   1. `<resource_dir>/binaries/zerodb-server`   (PyInstaller release build)
///   2. `python3 -m uvicorn api.main:app`          (dev fallback)
pub fn start_sidecar(data_dir: &str, port: u16) -> Result<(), String> {
    let mut guard = SIDECAR.lock().map_err(|e| e.to_string())?;

    if guard.is_some() {
        return Err("Sidecar is already running".to_string());
    }

    let bin_path = {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        exe.parent()
            .map(|p| p.join("binaries").join("zerodb-server"))
    };

    let child = if let Some(ref path) = bin_path {
        if path.exists() {
            log::info!("Starting zerodb-server from binary: {:?}", path);
            Command::new(path)
                .env("ZERODB_DATA_DIR", data_dir)
                .env("ZERODB_PORT", port.to_string())
                .env("ZERODB_HOST", "127.0.0.1")
                .spawn()
                .map_err(|e| format!("Failed to spawn binary: {e}"))?
        } else {
            log::warn!("Binary not found at {:?}, falling back to uvicorn", path);
            start_dev_fallback(data_dir, port)?
        }
    } else {
        start_dev_fallback(data_dir, port)?
    };

    *guard = Some(child);
    Ok(())
}

/// Dev-mode fallback: run the API via uvicorn.
fn start_dev_fallback(data_dir: &str, port: u16) -> Result<Child, String> {
    log::info!("Starting zerodb API via uvicorn (dev mode) on port {port}");
    Command::new("python3")
        .args([
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ])
        .env("ZERODB_DATA_DIR", data_dir)
        .current_dir(
            std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from(".")),
        )
        .spawn()
        .map_err(|e| format!("Failed to spawn uvicorn: {e}"))
}

/// Kill the sidecar process if it is running.
pub fn stop_sidecar() -> Result<(), String> {
    let mut guard = SIDECAR.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        child.kill().map_err(|e| format!("Failed to kill sidecar: {e}"))?;
        let _ = child.wait();
        log::info!("Sidecar stopped");
    }
    Ok(())
}

/// Returns `true` if the sidecar process is alive AND the health endpoint
/// responds with HTTP 200.
pub fn is_running() -> bool {
    // Quick process-level check first.
    {
        let mut guard = match SIDECAR.lock() {
            Ok(g) => g,
            Err(_) => return false,
        };
        if let Some(ref mut child) = *guard {
            match child.try_wait() {
                Ok(Some(_)) => {
                    // Process has exited.
                    *guard = None;
                    return false;
                }
                Ok(None) => {} // Still running — fall through to HTTP check.
                Err(_) => return false,
            }
        } else {
            return false;
        }
    }

    // HTTP health check (synchronous via reqwest blocking).
    match reqwest::blocking::get(API_HEALTH_URL) {
        Ok(resp) => resp.status().is_success(),
        Err(_) => false,
    }
}

/// Async variant of `is_running` for use inside Tokio contexts.
pub async fn is_running_async() -> bool {
    match reqwest::get(API_HEALTH_URL).await {
        Ok(resp) => resp.status().is_success(),
        Err(_) => false,
    }
}
