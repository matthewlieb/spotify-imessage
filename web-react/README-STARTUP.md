# 🎵 spotify-message Web App Startup Guide

## Current Status
- ✅ **Flask Backend**: Working perfectly on port 8004
- ⚠️ **React Frontend**: Takes a long time to start (30-60+ seconds)

## Quick Start (Recommended)

### Option 1: Start Backend Only (Fastest)
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
./start-backend.sh
```
- Backend will be available at: http://localhost:8004/api/
- You can test API endpoints directly

### Option 2: Start Both Services
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
./start-both.sh
```
- Backend: http://localhost:8004/api/
- Frontend: http://localhost:3000 (may take 30-60 seconds)

### Option 3: Manual Start (Two Terminals)

**Terminal 1 - Backend:**
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
source ../venv/bin/activate
python3 server.py
```

**Terminal 2 - Frontend:**
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
npm start
```

## Testing the Backend

The backend is fully functional. You can test it with:

```bash
# Health check
curl http://localhost:8004/api/health

# Scan for iMessage chats
curl -X POST http://localhost:8004/api/scan-imessage

# Search for playlists
curl -X POST http://localhost:8004/api/playlist/search \
  -H "Content-Type: application/json" \
  -d '{"name": "My Playlist"}'
```

## Troubleshooting

### React Takes Too Long
- This is normal for the first startup
- Subsequent starts should be faster
- You can use the backend API directly while React loads

### Port Conflicts
- Backend automatically finds available ports starting from 8004
- Frontend uses port 3000 (standard React port)

### Stop All Services
```bash
pkill -f "python.*server"
pkill -f "react-scripts"
pkill -f "npm start"
```

## Features Working
- ✅ Smart Message Detection (scans iMessage for Spotify links)
- ✅ Chat Name processing
- ✅ Playlist search and creation
- ✅ File upload processing
- ✅ All API endpoints functional
