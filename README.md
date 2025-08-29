# spotify-imessage

Sync **Spotify** tracks shared in an **iMessage** group chat into a Spotify playlist.

- macOS only (reads your local `~/Library/Messages/chat.db`)
- Picks up **plain links** and **rich-link** attachments (`.webloc` / `.url`)
- Validates IDs, batches adds (100 per call), and **skips duplicates** by default
- Uses Spotify OAuth with a persistent local cache

---

## Requirements

- macOS, with **Full Disk Access** granted to your terminal/IDE  
  _System Settings → Privacy & Security → Full Disk Access → enable your Terminal/IDE_
- Python **3.9+**
- A Spotify developer app (Client ID/Secret) and Redirect URI (e.g. `http://127.0.0.1:8000/callback`)
- (Optional, recommended) `imessage-exporter` for more robust exports:
  ```bash
  brew install imessage-exporter
  ```

> **Privacy:** All iMessage data is processed **locally**. Only Spotify track IDs are sent to Spotify’s Web API.

---

## Install

From source (editable install):

```bash
# from the repo root (spotify-imessage/)
pip install -e .
```

> Tip: use `pipx install .` if you prefer an isolated CLI install.

---

## Configure Spotify credentials

Set environment variables (recommended):

```bash
export SPOTIPY_CLIENT_ID="YOUR_CLIENT_ID"
export SPOTIPY_CLIENT_SECRET="YOUR_CLIENT_SECRET"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000/callback"
```

The OAuth token cache is stored at `~/.cache/spotify-imessage/spotify_token.json` by default.

---

## Usage

Basic:

```bash
spotify-imessage \
  --chat "My daughter is dating Kodak Black" \
  --playlist 1c68uZNKCUx7a1l6wr97D3
```

Common options:

- `--dry-run` — discover tracks but don’t add them
- `--no-dedupe` — don’t skip tracks already present in the playlist
- `--db` — path to your Messages database (default: `~/Library/Messages/chat.db`)
- `--attachments-dir` — path to your `~/Library/Messages/Attachments`
- `--cache` — where to store the Spotify OAuth token  
  (default: `~/.cache/spotify-imessage/spotify_token.json`)
- `--client-id` / `--client-secret` / `--redirect-uri` — or set env vars

Full help:

```bash
spotify-imessage --help
```

---

## How it works

1. Finds your chat’s `ROWID` by `display_name` (case-insensitive fallback included).
2. Queries `message.text` for `open.spotify.com/track/...` links.
3. Queries `attachment.transfer_name` for `.webloc` / `.url` (and certain `.txt`) files in that chat and scans them for Spotify URLs.
4. Validates 22‑char Base62 track IDs, optionally dedupes against the target playlist, and adds in batches of 100.

> If you install `imessage-exporter`, you can first dump TXT to verify content:
>
> ```bash
> imessage-exporter --format txt --db-path ~/Library/Messages/chat.db --output-dir ./_dump
> grep -Eo 'open\.spotify\.com/track/[A-Za-z0-9]+' ./_dump/*My\ daughter\ is\ dating\ Kodak\ Black*.txt \
>   | sed 's#.*/##' | sort -u | wc -l
> ```

---

## Troubleshooting

- **No messages / permission errors**  
  Ensure your Terminal/IDE has **Full Disk Access**, then restart it.

- **Invalid base62 id**  
  The CLI validates IDs; if you still see the error, double‑check your **playlist ID** (it should be a 22‑char string like `1c68uZNKCUx7a1l6wr97D3`).

- **OAuth cache warnings**  
  We write to `~/.cache/spotify-imessage/spotify_token.json`. Make sure that folder exists; the CLI creates it automatically.

- **Can’t find chat by name**  
  Names can differ subtly. You can list chats via SQLite:
  ```bash
  sqlite3 ~/Library/Messages/chat.db "SELECT ROWID, display_name FROM chat WHERE display_name IS NOT NULL;"
  ```
  Then use the exact `display_name` with `--chat`.

---

## Development

- Editable install: `pip install -e .`
- Run with local changes:
  ```bash
  spotify-imessage --chat "…" --playlist <PLAYLIST_ID>
  ```
- Contributions welcome! Please include a short description, repro steps, and your macOS version.

---

## License

MIT © Matthew Lieb

