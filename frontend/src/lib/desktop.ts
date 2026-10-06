/** True inside the desktop app's window (Tauri), never on the website. */
export const inDesktopWindow = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
