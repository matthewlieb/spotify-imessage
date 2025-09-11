# 🪟 Windows Setup Guide for spotify-message

This guide will help Windows users set up and use the spotify-message web app.

## 🚀 Quick Setup

### Prerequisites
1. **Python 3.8+** - Download from [python.org](https://python.org)
2. **Node.js 16+** - Download from [nodejs.org](https://nodejs.org)
3. **Git** (optional) - Download from [git-scm.com](https://git-scm.com)

### Installation Steps

1. **Clone or download the project**:
   ```cmd
   git clone https://github.com/your-repo/spotify-imessage.git
   cd spotify-imessage
   ```

2. **Set up Python virtual environment**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -e .
   pip install flask flask-cors
   ```

3. **Set up React dependencies**:
   ```cmd
   cd web-react
   npm install
   ```

4. **Start the app**:
   ```cmd
   start.bat
   ```

## 📱 Using with Android Messages

### Step 1: Export Your Android Messages
1. Open **Google Messages** app on your Android phone
2. Tap the **three dots** menu → **Settings**
3. Go to **Advanced** → **Export messages**
4. Choose your date range and export format (TXT)
5. Download the file to your computer

### Step 2: Use the Web App
1. Start the app: `start.bat`
2. Open http://localhost:3000 in your browser
3. Go to the **File Upload** tab
4. Upload your Android Messages export file
5. Configure your Spotify playlist
6. Process the tracks!

## 🎵 Features Available on Windows

### ✅ **Available Features:**
- **File Upload**: Upload Android Messages exports
- **Chat Name Processing**: Process specific conversations
- **Playlist Management**: Search/create Spotify playlists
- **Track Processing**: Extract and add Spotify tracks
- **Metadata Display**: Show artist and album info
- **Dry Run Mode**: Preview tracks before adding

### ❌ **Not Available on Windows:**
- **Smart Detection**: iMessage scanning (macOS only)

## 🔧 Troubleshooting

### Common Issues

**"Python not found"**
- Make sure Python is installed and added to PATH
- Try: `python --version` to verify

**"npm not found"**
- Make sure Node.js is installed
- Try: `node --version` and `npm --version`

**"Virtual environment not found"**
- Run: `python -m venv venv` from the project root
- Then: `venv\Scripts\activate`

**"Port already in use"**
- Close other applications using ports 3000 or 8004
- Or restart your computer

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Look at `flask.log` and `react.log` files
3. Make sure all prerequisites are installed
4. Try running the backend and frontend separately

## 🎯 Alternative: Command Line Usage

If the web app doesn't work, you can use the command line:

```cmd
# Activate virtual environment
venv\Scripts\activate

# Process Android Messages export
spotify_message android --file "path\to\your\export.txt" --playlist "your-playlist-id"

# Or process any text file with Spotify links
spotify_message file --file "path\to\your\file.txt" --playlist "your-playlist-id"
```

## 📞 Support

For Windows-specific issues or questions, please check:
- The main README.md file
- The troubleshooting section
- GitHub issues for similar problems

The app is designed to work cross-platform, so most features should work the same on Windows as on macOS!
