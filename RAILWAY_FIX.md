# Railway Fix: Use Correct Dockerfile

## Problem Found
Railway was using the **root Dockerfile** (Python-only) instead of `web-react/Dockerfile` (multi-stage React + Python).

## Solution Applied

1. ✅ **Deleted root `Dockerfile`** - This was causing Railway to skip the multi-stage build
2. ✅ **Updated `railway.json`** - Changed `dockerfilePath` from `"web-react/Dockerfile"` to `"Dockerfile"`

## Critical Railway Setting

**You MUST set Railway Root Directory to `web-react`:**

1. Go to Railway → Your Service → **Settings**
2. Find **"Root Directory"** setting
3. Set it to: `web-react`
4. Save

This ensures:
- Railway uses `web-react/Dockerfile` (which becomes `Dockerfile` relative to root directory)
- Build context is `web-react/` (so `COPY . .` works correctly)
- React build files are created in the right location

## What Happens Now

After setting Root Directory to `web-react` and pushing:

1. ✅ Railway will use `web-react/Dockerfile`
2. ✅ Stage 1: Builds React frontend (Node.js)
3. ✅ Stage 2: Copies React build → Installs Python → Starts Flask
4. ✅ Flask serves React app from `build/` directory

## Next Steps

1. **Set Railway Root Directory** to `web-react` (in Railway Settings)
2. **Commit and push**:
   ```bash
   git add railway.json
   git commit -m "Fix: Remove root Dockerfile, update railway.json for web-react root directory"
   git push
   ```
3. **Watch Railway Build Logs** - Should see:
   - Node.js stage building React
   - Python stage copying build files
   - Flask starting successfully

## Verify

After deployment, visit: `https://spotify-imessage-production.up.railway.app`

Should see React app (not 404 error).
