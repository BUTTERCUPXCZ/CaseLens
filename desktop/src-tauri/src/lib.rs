//! The CaseLens window. It starts the bundled backend (`caselens-server`) on a free local port, shows a loading screen
//! until the backend answers, then opens the library. Closing the app stops the backend.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

mod downloads;
mod updates;

use tauri::webview::{DownloadEvent, NewWindowResponse};
use tauri::{AppHandle, Manager, RunEvent, Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

/// The running backend, so it can be stopped when the app closes.
struct Backend(Mutex<Option<Child>>);

/// The first start copies the case catalog into a new library, so allow a generous wait.
const START_TIMEOUT: Duration = Duration::from_secs(120);

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0").and_then(|l| l.local_addr()).map(|a| a.port()).unwrap_or(8765)
}

fn server_program(app: &AppHandle) -> PathBuf {
    let name = if cfg!(windows) { "caselens-server.exe" } else { "caselens-server" };
    app.path().resource_dir().expect("resource folder").join("caselens-server").join(name)
}

/// A new secret each time the app opens: only this window gets into the backend (see `create_desktop_app` in server.py).
fn launch_token() -> String {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).expect("the system's random numbers");
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn start_backend(app: &AppHandle, port: u16, data_dir: &Path, token: &str) -> std::io::Result<Child> {
    let mut command = Command::new(server_program(app));
    command.env("CASELENS_LAUNCH_TOKEN", token); // in the environment, not the command line other programs can list
    command.arg("--app-version").arg(app.package_info().version.to_string()); // the backend copies the library on a new version
    command.arg("--port").arg(port.to_string()).arg("--data-dir").arg(data_dir).arg("--app-pid").arg(std::process::id().to_string());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    command.spawn()
}

/// True once `GET /api/health` answers 200.
fn backend_ready(port: u16) -> bool {
    let Ok(mut stream) = TcpStream::connect_timeout(&([127, 0, 0, 1], port).into(), Duration::from_secs(1)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(5)));
    let request = format!("GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut head = [0u8; 16];
    matches!(stream.read(&mut head), Ok(n) if n >= 12 && head[..n].starts_with(b"HTTP/1.1 200"))
}

fn show_problem(window: &WebviewWindow, message: &str) {
    let script = format!(
        "document.body.classList.add('problem'); document.getElementById('message').textContent = {:?};",
        message
    );
    let _ = window.eval(&script);
}

/// A file the library offers (a backup, a Word digest) goes to Downloads; an existing file is never overwritten.
fn download_target(downloads: PathBuf, suggested: &Path) -> PathBuf {
    let name = suggested.file_name().map(|n| n.to_owned()).unwrap_or_else(|| "CaseLens download".into());
    let mut target = downloads.join(&name);
    let stem = Path::new(&name).file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
    let ext = Path::new(&name).extension().map(|e| format!(".{}", e.to_string_lossy())).unwrap_or_default();
    let mut n = 1;
    while target.exists() {
        target = downloads.join(format!("{stem} ({n}){ext}"));
        n += 1;
    }
    target
}

fn open_window(app: &AppHandle) -> tauri::Result<WebviewWindow> {
    let builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .title("CaseLens")
        .inner_size(1280.0, 840.0)
        .min_inner_size(900.0, 600.0);
    // The page draws a title bar in the app's colours. A Mac keeps its own window buttons, laid over that bar.
    #[cfg(target_os = "macos")]
    let builder = builder.title_bar_style(tauri::TitleBarStyle::Overlay).hidden_title(true);
    #[cfg(not(target_os = "macos"))]
    let builder = builder.decorations(false);
    builder
        // A link to another website (Lawphil, an AI's key page) opens in the computer's own browser, never inside this window.
        .on_navigation(|url| {
            if downloads::is_app_url(url) {
                return true;
            }
            downloads::open_outside(url);
            false
        })
        .on_new_window(|url, _features| {
            downloads::open_outside(&url); // "open in a new tab" links: the window has no tabs
            NewWindowResponse::Deny
        })
        .on_download(|webview, event| match event {
            DownloadEvent::Requested { url, destination } => {
                if !downloads::first_request(&url) {
                    return false; // the same click asked twice: one file, not two copies
                }
                let folder = webview.path().download_dir().unwrap_or_else(|_| std::env::temp_dir());
                *destination = download_target(folder, destination);
                true
            }
            DownloadEvent::Finished { path, success, .. } => {
                downloads::finished(webview.app_handle(), path, success);
                true
            }
            _ => true,
        })
        .build()
}

/// Stop the backend (the app is closing, or an update is about to replace it).
pub(crate) fn stop_backend(app: &AppHandle) {
    if let Some(mut child) = app.state::<Backend>().0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // A second launch just brings the open window forward.
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(Backend(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            updates::check_update,
            updates::install_update,
            downloads::open_download,
            downloads::reveal_download
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            updates::manage(&handle);
            let window = open_window(&handle)?;
            let data_dir = handle.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir)?;
            let port = free_port();
            let token = launch_token();
            match start_backend(&handle, port, &data_dir, &token) {
                Ok(child) => *handle.state::<Backend>().0.lock().unwrap() = Some(child),
                Err(error) => {
                    show_problem(&window, &format!("CaseLens could not start ({error}). Please reinstall it."));
                    return Ok(());
                }
            }
            std::thread::spawn(move || {
                let started = Instant::now();
                while started.elapsed() < START_TIMEOUT {
                    if backend_ready(port) {
                        let url = Url::parse(&format!("http://127.0.0.1:{port}/?launch={token}")).expect("local address");
                        let _ = window.navigate(url);
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(300));
                }
                let log = data_dir.join("logs").join("server.log");
                show_problem(&window, &format!("CaseLens took too long to open. Close it and try again. Details: {}", log.display()));
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("CaseLens could not start")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_backend(app);
            }
        });
}
