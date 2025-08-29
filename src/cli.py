# cli.py
import os, re, glob, sqlite3, plistlib
import click
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

@click.command()
@click.option('--chat',     'chat_name',  required=True, help='iMessage group name')
@click.option('--playlist', 'playlist_id',required=True, help='Target Spotify playlist ID')
@click.option('--db',       'db_path',    default='~/Library/Messages/chat.db',
              help='Path to your Messages chat.db')
@click.option('--cache',    'cache_path', default='~/.cache/spotify_token.json',
              help='Where to store Spotify OAuth cache')
@click.option('--client-id',     envvar='SPOTIPY_CLIENT_ID',     help='Spotify Client ID')
@click.option('--client-secret', envvar='SPOTIPY_CLIENT_SECRET', help='Spotify Client Secret')
@click.option('--redirect-uri',  envvar='SPOTIPY_REDIRECT_URI',  default='http://127.0.0.1:8000/callback',
              help='Spotify Redirect URI')
def main(chat_name, playlist_id, db_path, cache_path,
         client_id, client_secret, redirect_uri):
    """Extracts Spotify tracks from an iMessage group and adds them to a playlist."""
    # Expand paths
    db_path    = os.path.expanduser(db_path)
    cache_path = os.path.expanduser(cache_path)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    # 1) Find chat_id
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ROWID FROM chat WHERE display_name = ?", (chat_name,))
    row = cursor.fetchone()
    if not row:
        raise click.ClickException(f"No iMessage chat named '{chat_name}'")
    chat_id = row[0]

    # 2) Pull all .webloc/.url attachments & text links
    cursor.execute("""
      SELECT m.text
      FROM message m
      JOIN chat_message_join cmj ON m.ROWID=cmj.message_id
      WHERE cmj.chat_id=? AND m.text LIKE '%open.spotify.com/track/%'
    """, (chat_id,))
    text_rows = [t for (t,) in cursor.fetchall() if t]

    cursor.execute("""
      SELECT a.transfer_name
      FROM attachment a
      JOIN message_attachment_join maj ON a.ROWID=maj.attachment_id
      JOIN chat_message_join cmj ON maj.message_id=cmj.message_id
      WHERE cmj.chat_id=? AND (a.transfer_name LIKE '%.webloc' OR a.transfer_name LIKE '%.url')
    """, (chat_id,))
    file_rows = [fn for (fn,) in cursor.fetchall()]

    conn.close()

    # 3) Extract IDs from text
    track_ids = { m.group(1)
                  for text in text_rows
                  for m in re.finditer(r'https?://open\.spotify\.com/track/([A-Za-z0-9]{22})', text) }

    # 4) Extract IDs from attachments
    attachments_dir = os.path.expanduser('~/Library/Messages/Attachments')
    for fname in file_rows:
        pattern = os.path.join(attachments_dir, '**', fname)
        for path in glob.glob(pattern, recursive=True):
            try:
                data = plistlib.load(open(path, 'rb'))
                url  = data.get('URL') or data.get('URLString', '')
                m    = re.search(r'https?://open\.spotify\.com/track/([A-Za-z0-9]{22})', url)
                if m: track_ids.add(m.group(1))
            except Exception:
                continue

    click.echo(f"Found {len(track_ids)} Spotify tracks in '{chat_name}'")

    # 5) Authenticate & add to playlist
    sp = Spotify(auth_manager=SpotifyOAuth(
        client_id     = client_id,
        client_secret = client_secret,
        redirect_uri  = redirect_uri,
        scope         = "playlist-modify-public playlist-modify-private",
        cache_path    = cache_path
    ))
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist_id, uris[i:i+100])

    click.echo("✅ Done!")

if __name__ == '__main__':
    main()
