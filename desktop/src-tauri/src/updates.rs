//! Updates over the internet ("OTA"): the page asks if a newer CaseLens is out, and installs it when the student clicks
//! "Install and restart". Every update must carry CaseLens's own signature (the public key in tauri.conf.json); any other
//! file is refused. The library is copied by the backend before a new version first opens it (see server.py).

use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_updater::{Update, UpdaterExt};

/// The update found by the last check, kept until it is installed.
#[derive(Default)]
pub struct PendingUpdate(Mutex<Option<Update>>);

#[derive(Serialize)]
pub struct UpdateInfo {
    version: String,
    notes: Option<String>,
}

#[derive(Clone, Serialize)]
struct Progress {
    downloaded: u64,
    total: Option<u64>,
}

/// Is a newer version out? Nothing when CaseLens is up to date (or offline: then it simply asks again later).
#[tauri::command]
pub async fn check_update(app: AppHandle, pending: State<'_, PendingUpdate>) -> Result<Option<UpdateInfo>, String> {
    let update = app.updater().map_err(|e| e.to_string())?.check().await.map_err(|e| e.to_string())?;
    let info = update.as_ref().map(|u| UpdateInfo { version: u.version.clone(), notes: u.body.clone() });
    *pending.0.lock().unwrap() = update;
    Ok(info)
}

/// Download the update (progress goes to the page as "update-progress"), stop the backend (Windows cannot replace a
/// program that is running), install, and open the new version.
#[tauri::command]
pub async fn install_update(app: AppHandle, pending: State<'_, PendingUpdate>) -> Result<(), String> {
    let update = pending.0.lock().unwrap().take().ok_or("No update to install.")?;
    let mut downloaded = 0u64;
    let window = app.clone();
    let bytes = update
        .download(
            move |chunk, total| {
                downloaded += chunk as u64;
                let _ = window.emit("update-progress", Progress { downloaded, total });
            },
            || {},
        )
        .await
        .map_err(|e| e.to_string())?;
    crate::stop_backend(&app);
    update.install(bytes).map_err(|e| e.to_string())?;
    app.restart();
}

/// Room for the update a check finds (the two commands above are registered in lib.rs; the page may call only them).
pub fn manage(app: &AppHandle) {
    app.manage(PendingUpdate::default());
}
