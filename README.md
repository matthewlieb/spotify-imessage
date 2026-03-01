# ♫ SpotifiMessage

**Extract Spotify tracks from your iMessage chats and create playlists automatically.**

Mac app (Electron) that signs in with Spotify, scans your iMessage for Spotify links, and creates a playlist in one flow.

## Download

- **Download page (GitHub Pages):** [matthewlieb.github.io/spotify-imessage](https://matthewlieb.github.io/spotify-imessage/) — pick Apple Silicon or Intel DMG.
- **Releases:** [github.com/matthewlieb/spotify-imessage/releases](https://github.com/matthewlieb/spotify-imessage/releases) — attach your built DMGs to a release so the download page can link to them.

**First time opening the app:** Right‑click the app → **Open** (then click Open in the dialog). See the release notes for setup (Full Disk Access, etc.).

## What it does

- 🔍 **Scan iMessage** for Spotify links (uses `imessage-exporter` on your Mac)
- 🎵 **Extract tracks** and pick which to add
- 📱 **Create playlists** on your Spotify account
- 🔐 **OAuth** – sign in with Spotify, no API key setup in the app

## Quick start

### Prerequisites

- **macOS** (for iMessage access)
- **Python 3** (e.g. `/usr/bin/python3` or `brew install python`)
- **Node.js 16+**
- **imessage-exporter**: `brew install imessage-exporter`
- **Spotify Developer App** – [docs/SPOTIFY_OAUTH_SETUP.md](docs/SPOTIFY_OAUTH_SETUP.md) (redirect URI: `http://127.0.0.1:8004/callback`)

### Run the app

From the project root:

```bash
./start-dev.sh
```

This will:

- Clear ports 8004 and 8005
- Build the React app (clean)
- Start Electron (Flask on 8004, Express on 8005, then open the app window)

**First time:** Configure Spotify in `web-react/.env` (Client ID, Client Secret). See [docs/SPOTIFY_OAUTH_SETUP.md](docs/SPOTIFY_OAUTH_SETUP.md).

**iMessage scan:** Grant **Full Disk Access** to SpotifiMessage in **System Settings → Privacy & Security** so it can read Messages.

## Project layout

- **electron/** – Mac app (Electron main process, Express for native iMessage API)
- **web-react/** – React UI + Flask backend (Spotify OAuth, playlists); served by Flask when running the app
- **docs/index.html** – Download page for GitHub Pages (theme matches the app; links to latest release DMGs)
- **docs/PACKAGING.md** – How to build a DMG for distribution
- **docs/DISTRIBUTION.md** – Releases, GitHub Pages, and distribution steps
- **docs/SPOTIFY_OAUTH_SETUP.md** – Spotify app and redirect URI setup
- **docs/SIGNING_AND_NOTARIZATION.md** – Why you see "damaged", user workaround (`xattr`), and how to sign + notarize with Apple Developer
- **docs/LIGHTWEIGHT_BUILD.md** – Smaller app: lite build (no bundled Python), DMG compression, trimming the bundle

## Packaging for distribution

See **[docs/PACKAGING.md](docs/PACKAGING.md)** and **[docs/DISTRIBUTION.md](docs/DISTRIBUTION.md)** for:

- Pre-packaging checklist and building the DMG (`npm run build:mac:unsigned` or `npm run build:mac` from repo root)
- Creating a GitHub Release and **attaching the DMG files** (required for the download page to offer direct links)
- Enabling GitHub Pages (Settings → Pages → source: branch `main`, folder `/docs`) so the download page is live at `https://<username>.github.io/spotify-imessage/`
- User requirements (Python 3, dependencies, Full Disk Access, `imessage-exporter`)

## Configuration

- **Spotify:** `web-react/.env` – `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`; redirect URI must be `http://127.0.0.1:8004/callback`.
- **Full Disk Access:** Required for iMessage scan (System Settings → Privacy & Security).

## License

MIT – see [LICENSE](LICENSE).

## Acknowledgments

- **imessage-exporter** – iMessage data access  
- **Spotipy** – Spotify API  
- **Electron, React, Flask** – app stack  
