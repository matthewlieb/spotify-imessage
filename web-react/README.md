# 🎵 spotify-message Web App

A web interface for extracting Spotify tracks from your message exports and creating playlists. **Now with Spotify OAuth authentication** - no more manual API key setup!

## 🔐 Spotify Authentication

The app now supports **one-click Spotify sign-in**! Users can connect their Spotify accounts directly through OAuth, eliminating the need for manual API key configuration.

### For Users
- Simply click "Sign in with Spotify" when you first open the app
- Grant permissions to create and manage playlists
- Start creating playlists immediately!

### For Developers
- See [SPOTIFY_OAUTH_SETUP.md](../docs/SPOTIFY_OAUTH_SETUP.md) for detailed setup instructions
- Set up your own Spotify app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Configure environment variables with your app credentials

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Virtual environment set up in the project root
- **Spotify Developer App** (see [SPOTIFY_OAUTH_SETUP.md](../docs/SPOTIFY_OAUTH_SETUP.md) for setup)

### Starting the App

**macOS/Linux:**
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
./start.sh
```

**Windows:**
```cmd
cd C:\path\to\spotify-imessage\web-react
start.bat
```

That's it! The script will:
- ✅ Check all prerequisites
- ✅ Clean up any existing processes
- ✅ Start the Flask backend (port 8004)
- ✅ Start the React frontend (port 3000)
- ✅ Monitor both services
- ✅ Provide clear status updates

### Access Points
- **Web App**: http://localhost:3000
- **API**: http://localhost:8004/api/

## 🛠️ Features

### Smart Message Detection (macOS/iOS only)
- Automatically scans your iMessage for conversations with Spotify links
- Shows track counts and last activity for each conversation
- One-click processing to add tracks to playlists

### Android Messages Support (All Platforms)
- Process Android Messages exports on any platform
- Upload Android Messages export files
- Extract Spotify links from Android conversations

### Chat Name Processing
- Enter specific chat names to process
- Works with both iMessage and Android Messages exports

### File Upload
- Upload exported message files (TXT format)
- Process tracks from any message export
- Supports multiple message formats

### Playlist Management
- Search for existing Spotify playlists by name
- Create new playlists automatically
- Add tracks with metadata and dry-run options

## 🌍 Cross-Platform Support

### **macOS/iOS Users:**
- ✅ Full iMessage Smart Detection
- ✅ Android Messages support
- ✅ File upload support

### **Windows/Android Users:**
- ✅ Android Messages export processing
- ✅ File upload support
- ✅ All playlist management features
- ❌ iMessage Smart Detection (not available on Windows)

### **Linux Users:**
- ✅ Android Messages support
- ✅ File upload support
- ❌ iMessage Smart Detection (not available on Linux)

## 🔧 Technical Details

### Backend (Flask)
- **Port**: 8004 (auto-detected if busy)
- **API Endpoints**: `/api/health`, `/api/scan-imessage`, `/api/playlist/search`, etc.
- **Features**: CORS enabled, comprehensive logging, error handling

### Frontend (React)
- **Port**: 3000
- **Framework**: React 18 with modern hooks
- **Styling**: Tailwind CSS
- **Features**: Responsive design, real-time updates, error handling

### Error Handling
The startup script includes comprehensive error handling:
- ✅ Prerequisites checking
- ✅ Port conflict resolution
- ✅ Service health monitoring
- ✅ Automatic cleanup on exit
- ✅ Detailed status reporting

## 🐛 Troubleshooting

### Common Issues

**"Port already in use"**
- The script automatically finds available ports
- If issues persist, run: `pkill -f "python.*server" && pkill -f "react-scripts"`

**"Virtual environment not found"**
- Run from project root: `python3 -m venv venv`
- Then: `source venv/bin/activate && pip install -e .`

**"React takes too long to start"**
- This is normal for the first startup (30-60 seconds)
- Subsequent starts are faster
- The script will wait and show progress

**"Backend not responding"**
- Check if virtual environment is activated
- Ensure all dependencies are installed: `pip install flask flask-cors spotipy`

### Manual Start (if needed)

**Backend only:**
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
source ../venv/bin/activate
python3 server.py
```

**Frontend only:**
```bash
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react
npm start
```

## 📁 Project Structure

```
web-react/
├── start.sh              # Main startup script (macOS/Linux)
├── start.bat             # Main startup script (Windows)
├── server.py             # Flask backend
├── package.json          # React dependencies
├── src/
│   ├── App.js           # Main React component
│   ├── index.tsx        # React entry point
│   └── services/        # API service layer
├── .env                  # Environment variables (create from env.example)
├── env.example           # Environment variables template
└── README.md            # This file
```

## 🎯 Usage

1. **Start the app**: 
   - macOS/Linux: `./start.sh`
   - Windows: `start.bat`
2. **Open browser**: http://localhost:3000
3. **Sign in with Spotify**: One-click authentication
4. **Choose method**:
   - **Smart Detection** (macOS only): Auto-scan for Spotify links
   - **Chat Name**: Enter specific chat name
   - **File Upload**: Upload message export file
5. **Configure playlist**: Search or create Spotify playlist
6. **Process tracks**: Add tracks to your playlist

## 📱 Getting Your Messages Data

### **Android Users (All Platforms):**
1. **Export Android Messages**:
   - Open Google Messages app
   - Go to Settings → Advanced → Export messages
   - Choose date range and export format (TXT)
   - Download the export file

2. **Use the File Upload feature**:
   - Upload your Android Messages export file
   - The app will extract all Spotify links
   - Process them into your playlist

### **iPhone Users (macOS only):**
- Use the **Smart Detection** feature for automatic scanning
- Or export iMessage data and use **File Upload**

### **Other Message Apps:**
- Export your messages as text files
- Use the **File Upload** feature to process them

## 🔒 Security Notes

- This is a development server
- For production, use proper web servers (nginx, Apache)
- Spotify API credentials should be stored securely
- Message data is processed locally

## 📝 License

See the main project LICENSE file for details.
