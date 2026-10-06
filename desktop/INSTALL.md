# Installing CaseLens

CaseLens runs on your own computer. Your cases, digests and uploads stay on it; only the AI requests go to Google.

## 1. Download the right file

From the CaseLens release page, download **one** file:

| Your computer | File |
|---|---|
| Windows 10 or 11 | `CaseLens_x.y.z_x64-setup.exe` |
| Mac with Apple chip (M1, M2, M3, M4…) | `CaseLens_x.y.z_aarch64.dmg` |
| Mac with Intel chip | `CaseLens_x.y.z_x64.dmg` |

Not sure which Mac you have? Apple menu  → **About This Mac**. "Chip: Apple M…" means Apple chip; "Processor: Intel" means Intel.

## 2. Install and open it the first time

CaseLens is not signed with a paid Apple or Microsoft certificate, so the computer asks once if you trust it. This is normal.

### Windows
1. Double-click `CaseLens_…_x64-setup.exe`.
2. If a blue box says **"Windows protected your PC"**: click **More info**, then **Run anyway**.
3. Follow the installer. Open CaseLens from the Start menu.

### Mac
1. Double-click the `.dmg` file, then drag **CaseLens** into **Applications**.
2. Open **Applications** and double-click **CaseLens**. A message says it cannot be checked: click **Done** (or **OK**).
3. Open **System Settings → Privacy & Security**. Scroll down to the message about CaseLens and click **Open Anyway**. Enter your Mac password if asked.
4. Open CaseLens again and click **Open**.

You only do this once per version.

## 3. Add your AI key (once)

1. In CaseLens, click **Settings** in the menu on the left.
2. Paste your Gemini API key under **AI key** and click **Save key**.

Get a key at **aistudio.google.com → Get API key**. Turn on **billing** for the key's project
(**Set up billing**): without it Google allows only about 3 digests a day.

## 4. Keep a backup

**Settings → Download a backup** saves your whole library as one file. Keep a copy on a USB drive or in cloud storage, for example
once a week. **Restore from a backup** brings it back on this or a new computer (CaseLens finishes the restore the next time it opens).

## Good to know

- Keep CaseLens open while a Bulk upload is being digested. Ready cases can be read while the others are still being written.
- A new version: download and install it the same way. Your library and AI key are kept.
- Your library is in: Windows `%APPDATA%\ph.caselens.desktop`, Mac `~/Library/Application Support/ph.caselens.desktop`
  (also shown in **Settings**).

## If something goes wrong

- **Mac says "CaseLens is damaged and can't be opened"**: open the **Terminal** app, paste
  `xattr -cr /Applications/CaseLens.app`, press Enter, then open CaseLens again.
- **CaseLens stays on "Opening your library…"**: close it and open it again. If it still does not open, send the file
  `logs/server.log` from the library folder above.
- **"The writing service did not answer"** on many digests: the AI key has reached Google's limit. Check billing on the key's
  project, then click **Try again**.
