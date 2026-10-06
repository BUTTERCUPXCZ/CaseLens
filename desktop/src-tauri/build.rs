fn main() {
    // The app's own commands get permissions ("allow-check-update", ...), so capabilities/default.json can name exactly
    // which ones the library page may call.
    tauri_build::try_build(
        tauri_build::Attributes::new()
            .app_manifest(tauri_build::AppManifest::new().commands(&["check_update", "install_update"])),
    )
    .expect("failed to run the Tauri build step")
}
