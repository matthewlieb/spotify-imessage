# Release description (paste into GitHub Release)

**Brief description** (for the release title or summary):

> SpotifiMessage for Mac — Extract Spotify links from iMessage and create playlists. Download the DMG for your chip (Apple Silicon or Intel), right‑click → Open the first time, then sign in with Spotify and scan your messages.

---

**Full description** (paste into the release body). Replace `1.0.0` with your version if different.

## SpotifiMessage for Mac

Extract Spotify links from your iMessage chats and create playlists in one flow.

### Download

- **Apple Silicon (M1/M2/M3):** download `SpotifiMessage-1.0.0-arm64.dmg`
- **Intel Mac:** download `SpotifiMessage-1.0.0.dmg`

### First-time setup

1. Open the DMG and drag **SpotifiMessage** to Applications (or run from the DMG).
2. **First time only:** do **not** double‑click. **Right‑click** the app → **Open** → click **Open** in the dialog. (macOS blocks unsigned apps until you do this once.)
3. **If macOS says the app is "damaged"** or Right‑click → Open doesn’t work, open **Terminal** and run (adjust the path if you put the app elsewhere):
   ```bash
   xattr -dr com.apple.quarantine ~/Downloads/SpotifiMessage.app
   ```
   Then double‑click the app. The app is not actually damaged; this removes the download quarantine.
4. Sign in with Spotify when the app opens.
5. For **Scan Messages**, grant **Full Disk Access**: **System Settings → Privacy & Security → Full Disk Access** → add SpotifiMessage. Install `imessage-exporter` if needed: `brew install imessage-exporter`.

The full build includes Python; no separate install required. For more detail, see the [README](https://github.com/matthewlieb/spotify-imessage#readme).
