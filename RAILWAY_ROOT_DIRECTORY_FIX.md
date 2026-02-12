# Railway Root Directory Issue - Fix

## Problem
Railway build logs show:
- `found 'Dockerfile' at 'Dockerfile'` - Railway looking at repo root
- `skipping 'Dockerfile' at 'web-react/Dockerfile'` - Railway skipping correct Dockerfile
- `root_dir=` - Root Directory is blank/not set
- Build is using Python-only Dockerfile (no React build)

## Root Cause
Railway's **Root Directory** setting is **NOT set to `web-react`**, so Railway:
1. Looks for Dockerfile at repo root (where we deleted it)
2. May be using cached build from before deletion
3. Skips `web-react/Dockerfile` because it's not at the root

## Solution Options

### Option A: Set Railway Root Directory (RECOMMENDED)

1. Go to Railway → Your Service → **Settings**
2. Find **"Root Directory"** field
3. Set it to: `web-react`
4. Save

Then update `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  }
}
```

### Option B: Use Explicit Path (CURRENT FIX)

I've updated `railway.json` to explicitly use `web-react/Dockerfile`:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "web-react/Dockerfile"
  }
}
```

**However**, this may still fail if Railway's build context is wrong. The Dockerfile expects build context to be `web-react/`, but Railway might use repo root as context.

## Best Solution: Set Root Directory + Update Dockerfile

If Railway Root Directory is set to `web-react`:
- Build context becomes `web-react/`
- `dockerfilePath: "Dockerfile"` works (points to `web-react/Dockerfile`)
- `COPY . .` in Dockerfile works correctly

## Next Steps

1. **Try Option B first** (already applied):
   ```bash
   git add railway.json
   git commit -m "Fix: Explicitly point to web-react/Dockerfile in railway.json"
   git push
   ```

2. **If that fails**, set Railway Root Directory to `web-react` and update `railway.json` back to `"Dockerfile"`

3. **Watch build logs** - Should see:
   - `FROM node:20-alpine AS frontend-builder` (React build stage)
   - `npm run build` executing
   - `build/index.html` being created

## Why This Matters

Without the React build stage:
- ❌ No `build/` directory created
- ❌ Flask returns 404 for `/`
- ❌ App doesn't work

With correct Dockerfile:
- ✅ React builds in Node.js stage
- ✅ Build copied to Python stage
- ✅ Flask serves React app correctly
