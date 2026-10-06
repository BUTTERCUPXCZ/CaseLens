//! The CaseLens window. It starts the bundled backend (`caselens-server`) on a free local port, shows a loading screen
//! until the backend answers, then opens the library. Closing the app stops the backend.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::webview::DownloadEvent;
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

fn start_backend(app: &AppHandle, port: u16, data_dir: &Path) -> std::io::Result<Child> {
    let mut command = Command::new(server_program(app));
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
        .on_download(|webview, event| {
            if let DownloadEvent::Requested { destination, .. } = event {
                let downloads = webview.path().download_dir().unwrap_or_else(|_| std::env::temp_dir());
                *destination = download_target(downloads, destination);
            }
            true
        })
        .build()
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
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();
            let window = open_window(&handle)?;
            let data_dir = handle.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir)?;
            let port = free_port();
            match start_backend(&handle, port, &data_dir) {
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
                        let url = Url::parse(&format!("http://127.0.0.1:{port}/")).expect("local address");
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
                if let Some(mut child) = app.state::<Backend>().0.lock().unwrap().take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        });
}
