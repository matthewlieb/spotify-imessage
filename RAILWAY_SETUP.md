# Railway Full-Stack Setup Guide

## ✅ What We Just Did

Updated `nixpacks.toml` to build both React frontend and Flask backend together on Railway.

## 🚀 Next Steps (5 minutes)

### Step 1: Update Railway Environment Variables

Go to Railway → Your Service → **Variables** tab and set:

```
FRONTEND_URL=https://spotify-imessage-production.up.railway.app
SPOTIFY_REDIRECT_URI=https://spotify-imessage-production.up.railway.app/callback
```

(Keep your existing `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, etc.)

### Step 2: Verify Railway Service Settings

In Railway → Your Service → **Settings**:
- **Root Directory**: Leave blank (uses repo root) - `nixpacks.toml` handles `web-react/` paths
- **Builder**: Should be "NIXPACKS" (we updated `railway.json` to ensure this)
- Build and Start commands will use `nixpacks.toml` automatically

### Step 3: Update Spotify Redirect URIs

Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):
1. Select your app "Message Fetcher"
2. Go to "Basic Information"
3. Under "Redirect URIs", make sure you have:
   - `https://spotify-imessage-production.up.railway.app/callback` ✅ (already there)
   - `http://127.0.0.1:8004/callback` (for local dev)

### Step 4: Commit and Push

```bash
git add nixpacks.toml
git commit -m "Deploy React frontend + Flask backend together on Railway"
git push
```

Railway will automatically rebuild and deploy!

### Step 5: Test

After deployment completes:
1. Visit: `https://spotify-imessage-production.up.railway.app`
2. You should see your React app (no more 404!)
3. Click "Sign in with Spotify" - should work!

## 🎯 What This Achieves

- ✅ **One URL** for everything: `https://spotify-imessage-production.up.railway.app`
- ✅ **No CORS issues** - same origin
- ✅ **No proxy needed** - Flask serves React directly
- ✅ **Simpler OAuth** - same domain
- ✅ **Lower cost** - one service instead of two

## 🔧 How It Works

1. Railway builds React frontend (`npm run build`)
2. Railway sets up Python environment
3. Flask server starts and serves:
   - `/api/*` → Flask API endpoints
   - `/*` → React app (from `build/` directory)

## 🐛 Troubleshooting

**Build fails?**
- Check Railway build logs
- Make sure `package.json` and `requirements.txt` are in `web-react/`

**404 on root URL?**
- Verify `build/index.html` exists after build
- Check Railway logs for Flask startup messages

**Spotify login fails?**
- Verify `FRONTEND_URL` matches your Railway URL
- Check Spotify redirect URI matches exactly

## 📝 Notes

- Your Flask server already has code to serve React build files (lines 1553-1569 in `server.py`)
- No code changes needed - just configuration!
- You can still develop locally with `./start.sh` (uses separate React dev server)
