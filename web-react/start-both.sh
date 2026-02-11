#!/bin/bash

echo "🎵 Starting spotify-message Web App..."

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python.*server" 2>/dev/null
pkill -f "react-scripts" 2>/dev/null
pkill -f "npm start" 2>/dev/null
sleep 2

# Navigate to the correct directory
cd /Users/matthewlieb/Desktop/CODING/Projects/spotify-imessage/web-react

# Start Flask backend in background
echo "🚀 Starting Flask backend..."
source ../venv/bin/activate
python3 server.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8004/api/health >/dev/null 2>&1; then
    echo "✅ Flask backend started successfully on port 8004"
    
    # Start React frontend in background
    echo "🚀 Starting React frontend..."
    npm start &
    FRONTEND_PID=$!
    
    echo ""
    echo "🎉 Both servers are starting!"
    echo "📱 React app: http://localhost:3000"
    echo "🔧 API endpoints: http://localhost:8004/api/"
    echo ""
    echo "⏳ React may take 30-60 seconds to fully start..."
    echo "Press Ctrl+C to stop both servers"
    
    # Function to cleanup on exit
    cleanup() {
        echo ""
        echo "🛑 Stopping servers..."
        kill $BACKEND_PID 2>/dev/null
        kill $FRONTEND_PID 2>/dev/null
        pkill -f "python.*server" 2>/dev/null
        pkill -f "react-scripts" 2>/dev/null
        echo "✅ Servers stopped"
        exit 0
    }
    
    # Trap Ctrl+C
    trap cleanup INT
    
    # Wait for processes
    wait
else
    echo "❌ Failed to start Flask backend"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi