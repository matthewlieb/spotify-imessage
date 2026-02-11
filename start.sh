#!/bin/bash
# Single script to launch the spotify-imessage web app locally

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting spotify-imessage Web App${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ============================================================================
# STEP 1: Clean up all existing processes on ports 3000 and 8004
# ============================================================================
echo -e "${BLUE}📋 Step 1: Cleaning up existing processes...${NC}"

# Kill all processes on port 3000 (React)
echo -e "${YELLOW}   → Killing processes on port 3000 (React)...${NC}"
PIDS_3000=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$PIDS_3000" ]; then
    echo "$PIDS_3000" | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}   ✅ Killed processes on port 3000${NC}"
else
    echo -e "${GREEN}   ✅ Port 3000 is already free${NC}"
fi

# Kill all processes on port 8004 (Flask)
echo -e "${YELLOW}   → Killing processes on port 8004 (Flask)...${NC}"
PIDS_8004=$(lsof -ti:8004 2>/dev/null || true)
if [ -n "$PIDS_8004" ]; then
    echo "$PIDS_8004" | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}   ✅ Killed processes on port 8004${NC}"
else
    echo -e "${GREEN}   ✅ Port 8004 is already free${NC}"
fi

# Kill any react-scripts processes that might be hanging
echo -e "${YELLOW}   → Killing any hanging react-scripts processes...${NC}"
pkill -f "react-scripts" 2>/dev/null || true
pkill -f "node.*start.js" 2>/dev/null || true

# Kill any python server.py processes
echo -e "${YELLOW}   → Killing any hanging Flask server processes...${NC}"
pkill -f "python.*server.py" 2>/dev/null || true

# Wait a moment for ports to be fully released
sleep 2

# Verify ports are free
if lsof -ti:3000 >/dev/null 2>&1 || lsof -ti:8004 >/dev/null 2>&1; then
    echo -e "${RED}   ⚠️  Warning: Some ports may still be in use${NC}"
    echo -e "${YELLOW}   → Attempting force cleanup...${NC}"
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8004 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# ============================================================================
# STEP 2: Setup Python environment
# ============================================================================
echo -e "${BLUE}📋 Step 2: Setting up Python environment...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}   → Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}   ✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}   → Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies if needed
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}   → Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    [ -f setup.py ] || [ -f pyproject.toml ] && pip install -e . || true
    echo -e "${GREEN}   ✅ Python dependencies installed${NC}"
else
    echo -e "${GREEN}   ✅ Python dependencies already installed${NC}"
fi

echo -e "${GREEN}✅ Python environment ready${NC}"
echo ""

# ============================================================================
# STEP 3: Setup Node.js environment
# ============================================================================
echo -e "${BLUE}📋 Step 3: Setting up Node.js environment...${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js 16+ to continue.${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}   ✅ Node.js found: $NODE_VERSION${NC}"

# Navigate to web-react directory
cd web-react

# Install Node dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   → Installing Node.js dependencies - this may take a minute...${NC}"
    npm install
    echo -e "${GREEN}   ✅ Node.js dependencies installed${NC}"
else
    echo -e "${GREEN}   ✅ Node.js dependencies already installed${NC}"
fi

echo -e "${GREEN}✅ Node.js environment ready${NC}"
echo ""

# ============================================================================
# STEP 4: Check configuration
# ============================================================================
echo -e "${BLUE}📋 Step 4: Checking configuration...${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}   → .env file not found. Creating template...${NC}"
    cat > .env << EOF
# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8004/callback

# Flask Session Secret (optional - will auto-generate if not provided)
FLASK_SECRET_KEY=
EOF
    echo -e "${YELLOW}   ⚠️  Please edit .env file with your Spotify credentials${NC}"
    echo -e "${YELLOW}   → See README.md for Spotify OAuth setup instructions${NC}"
else
    echo -e "${GREEN}   ✅ .env file found${NC}"
fi

echo -e "${GREEN}✅ Configuration check complete${NC}"
echo ""

# ============================================================================
# STEP 5: Start Flask backend
# ============================================================================
echo -e "${BLUE}📋 Step 5: Starting Flask backend server...${NC}"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down servers...${NC}"
    if [ -n "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null || true
    fi
    if [ -n "$REACT_PID" ]; then
        kill $REACT_PID 2>/dev/null || true
    fi
    # Also kill by process name to be sure
    pkill -f "python.*server.py" 2>/dev/null || true
    pkill -f "react-scripts" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Flask backend in background
echo -e "${YELLOW}   → Starting Flask server on port 8004...${NC}"
cd "$SCRIPT_DIR/web-react"
python server.py > /tmp/flask_output.log 2>&1 &
FLASK_PID=$!

# Wait for Flask to be listening (poll up to 10s so we proceed as soon as ready)
echo -e "${YELLOW}   → Waiting for Flask to initialize...${NC}"
FLASK_READY=false
for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if lsof -ti:8004 >/dev/null 2>&1; then
    FLASK_READY=true
    break
  fi
  if ! kill -0 $FLASK_PID 2>/dev/null; then
    break
  fi
done

# Check if Flask started successfully
if ! kill -0 $FLASK_PID 2>/dev/null; then
    echo -e "${RED}   ❌ Failed to start Flask server${NC}"
    echo -e "${YELLOW}   → Check /tmp/flask_output.log for errors:${NC}"
    cat /tmp/flask_output.log
    exit 1
fi

# Verify Flask is listening on port 8004
if lsof -ti:8004 >/dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Flask server is running on port 8004${NC}"
else
    echo -e "${RED}   ❌ Flask server is not listening on port 8004${NC}"
    echo -e "${YELLOW}   → Check /tmp/flask_output.log for errors:${NC}"
    tail -20 /tmp/flask_output.log
    exit 1
fi

echo -e "${GREEN}✅ Flask backend started successfully${NC}"
echo ""

# ============================================================================
# STEP 6: Start React frontend
# ============================================================================
echo -e "${BLUE}📋 Step 6: Starting React frontend...${NC}"

# Start React frontend
echo -e "${YELLOW}   → Starting React development server on port 3000...${NC}"
cd "$SCRIPT_DIR/web-react"
BROWSER=none HOST=0.0.0.0 npm start > /tmp/react_output.log 2>&1 &
REACT_PID=$!

# Wait for React to compile (poll every 2s, up to 24s)
echo -e "${YELLOW}   → Waiting for React to compile...${NC}"
REACT_READY=false
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    sleep 2
    if lsof -ti:3000 >/dev/null 2>&1; then
        REACT_READY=true
        echo -e "${GREEN}   ✅ React server is running on port 3000${NC}"
        break
    fi
    if ! kill -0 $REACT_PID 2>/dev/null; then
        echo -e "${RED}   ❌ React process died${NC}"
        tail -20 /tmp/react_output.log 2>/dev/null
        kill $FLASK_PID 2>/dev/null || true
        exit 1
    fi
    [ $((i % 3)) -eq 0 ] && echo -e "${YELLOW}   → Compiling... ${i}0s${NC}"
done
[ "$REACT_READY" = false ] && echo -e "${YELLOW}   ⚠️  React may still be starting. Open http://localhost:3000 in a moment.${NC}"
echo -e "${GREEN}✅ React frontend started${NC}"
echo ""

# ============================================================================
# STEP 7: Display status and wait
# ============================================================================
echo -e "${GREEN}✅ Both servers are running!${NC}"
echo ""
echo -e "${GREEN}📱 Web App:${NC}    http://localhost:3000"
echo -e "${GREEN}🔧 API:${NC}       http://localhost:8004/api/"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for user interrupt
wait
