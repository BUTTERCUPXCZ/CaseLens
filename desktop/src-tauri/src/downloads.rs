//! Links and downloads in the CaseLens window, which has no browser around it: a link to another website (Lawphil, an AI's key page)
//! opens in the computer's own browser, and a file the library offers (a Word digest, a backup) is saved to Downloads and the page is
//! told so ("download-finished"), so it can say where the file went and offer to open it.

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Url};

/// The same file asked for again this soon is the same click: the window's engine can ask more than once for one download.
const SAME_CLICK: Duration = Duration::from_secs(3);

static LAST_REQUEST: Mutex<Option<(String, Instant)>> = Mutex::new(None);

/// The files this app saved since it opened: the only ones the page may open or show.
static SAVED: Mutex<Option<HashSet<PathBuf>>> = Mutex::new(None);

/// Only documents are opened with their program (never a program or script, whatever the page asks).
const OPENABLE: &[&str] = &["docx", "pdf"];

/// The app's own pages: the loading screen and the local library. Everything else is another website.
pub fn is_app_url(url: &Url) -> bool {
    match url.scheme() {
        "tauri" | "about" | "data" | "blob" => true,
        "http" | "https" => matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "tauri.localhost")),
        _ => false,
    }
}

/// A link to another website (or an e-mail address) opens in the computer's own browser or mail program.
pub fn open_outside(url: &Url) {
    if matches!(url.scheme(), "http" | "https" | "mailto") {
        let _ = tauri_plugin_opener::open_url(url.as_str(), None::<&str>);
    }
}

/// False when this is a repeat of the download just started (one click, asked for twice by the engine).
pub fn first_request(url: &Url) -> bool {
    let mut last = LAST_REQUEST.lock().unwrap();
    let now = Instant::now();
    if let Some((previous, at)) = last.as_ref() {
        if previous == url.as_str() && now.duration_since(*at) < SAME_CLICK {
            return false;
        }
    }
    *last = Some((url.as_str().to_owned(), now));
    true
}

#[derive(Clone, Serialize)]
struct Finished {
    name: String,
    path: Option<String>,
    success: bool,
}

/// Tell the page a download is done, with the file's name and where it was saved.
pub fn finished(app: &AppHandle, path: Option<PathBuf>, success: bool) {
    if let (true, Some(saved)) = (success, path.as_ref().and_then(|p| p.canonicalize().ok())) {
        SAVED.lock().unwrap().get_or_insert_with(HashSet::new).insert(saved);
    }
    let name = path.as_ref().and_then(|p| p.file_name()).map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let path = path.map(|p| p.to_string_lossy().into_owned());
    let _ = app.emit("download-finished", Finished { name, path, success });
}

/// Only a file this app itself saved to the Downloads folder (since it opened) may be opened or shown from the page: the page cannot
/// reach any other file on the computer.
fn saved_by_us(app: &AppHandle, path: &str) -> Result<PathBuf, String> {
    let downloads = app.path().download_dir().map_err(|e| e.to_string())?;
    let downloads = downloads.canonicalize().unwrap_or(downloads);
    let file = Path::new(path).canonicalize().map_err(|_| "That file is no longer there.".to_string())?;
    let ours = SAVED.lock().unwrap().as_ref().is_some_and(|saved| saved.contains(&file));
    if file.starts_with(&downloads) && ours {
        Ok(file)
    } else {
        Err("Only files CaseLens just saved can be opened from here.".into())
    }
}

/// Open a downloaded file with the program the computer uses for it (Word for a .docx).
#[tauri::command]
pub fn open_download(app: AppHandle, path: String) -> Result<(), String> {
    let file = saved_by_us(&app, &path)?;
    let kind = file.extension().and_then(|e| e.to_str()).map(|e| e.to_ascii_lowercase()).unwrap_or_default();
    if !OPENABLE.contains(&kind.as_str()) {
        return Err("This kind of file is not opened from here. Use Show in folder.".into());
    }
    tauri_plugin_opener::open_path(file, None::<&str>).map_err(|e| e.to_string())
}

/// Show a downloaded file in its folder.
#[tauri::command]
pub fn reveal_download(app: AppHandle, path: String) -> Result<(), String> {
    let file = saved_by_us(&app, &path)?;
    tauri_plugin_opener::reveal_item_in_dir(file).map_err(|e| e.to_string())
}
