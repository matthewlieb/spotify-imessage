#!/bin/bash

# 🎵 spotify-message Web App Startup Script
# This script starts both the Flask backend and React frontend with comprehensive error handling

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8004
FRONTEND_PORT=3000
MAX_PORT_ATTEMPTS=10
BACKEND_STARTUP_TIMEOUT=30
FRONTEND_STARTUP_TIMEOUT=120

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find an available port
find_available_port() {
    local start_port=$1
    local port=$start_port
    local attempts=0
    
    while [ $attempts -lt $MAX_PORT_ATTEMPTS ]; do
        if ! check_port $port; then
            echo $port
            return 0
        fi
        print_warning "Port $port is in use, trying $((port + 1))..."
        ((port++))
        ((attempts++))
    done
    
    print_error "No available ports found between $start_port and $((start_port + MAX_PORT_ATTEMPTS - 1))"
    return 1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local timeout=$2
    local service_name=$3
    local attempts=0
    
    print_status "Waiting for $service_name to start..."
    
    while [ $attempts -lt $timeout ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        sleep 1
        ((attempts++))
        if [ $((attempts % 10)) -eq 0 ]; then
            print_status "Still waiting for $service_name... (${attempts}s)"
        fi
    done
    
    print_error "$service_name failed to start within ${timeout}s"
    return 1
}

# Function to cleanup processes
cleanup() {
    print_status "Cleaning up processes..."
    
    # Kill backend processes
    pkill -f "python.*server" 2>/dev/null || true
    pkill -f "flask" 2>/dev/null || true
    
    # Kill frontend processes
    pkill -f "react-scripts" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    
    # Kill any processes on our ports
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [ ! -f "package.json" ]; then
        print_error "package.json not found. Please run this script from the web-react directory."
        exit 1
    fi
    
    if [ ! -f "server.py" ]; then
        print_error "server.py not found. Please run this script from the web-react directory."
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "../venv" ]; then
        print_error "Virtual environment not found. Please run from the project root: python3 -m venv venv"
        exit 1
    fi
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found. Running npm install..."
        npm install
        if [ $? -ne 0 ]; then
            print_error "npm install failed"
            exit 1
        fi
    fi
    
    # Check for React-specific issues
    print_status "Checking React setup..."
    
    # Check if there are conflicting App files
    if [ -f "src/App.tsx" ] && [ -f "src/App.js" ]; then
        print_warning "Found both App.tsx and App.js. Removing App.tsx to avoid conflicts..."
        rm -f src/App.tsx
    fi
    
    # Check if index.tsx exists and imports App correctly
    if [ -f "src/index.tsx" ]; then
        if grep -q "import App from './App.js'" src/index.tsx; then
            if [ ! -f "src/App.js" ]; then
                print_error "index.tsx imports App.js but App.js doesn't exist"
                exit 1
            fi
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to start backend
start_backend() {
    print_status "Starting Flask backend..."
    
    # Find available port
    local backend_port=$(find_available_port $BACKEND_PORT)
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Start backend in background
    print_status "Activating virtual environment and starting Flask..."
    source ../venv/bin/activate
    python3 server.py > flask.log 2>&1 &
    local backend_pid=$!
    
    # Give Flask a moment to start
    sleep 3
    
    # Wait for backend to be ready
    print_status "Waiting for Flask backend to be ready..."
    if wait_for_service "http://localhost:$backend_port/api/health" $BACKEND_STARTUP_TIMEOUT "Backend"; then
        print_success "Backend started successfully on port $backend_port"
        echo $backend_pid
        return 0
    else
        print_error "Backend failed to start. Check flask.log for details."
        kill $backend_pid 2>/dev/null || true
        return 1
    fi
}

# Function to start frontend
start_frontend() {
    print_status "Starting React frontend..."
    
    # Check if frontend port is available
    if check_port $FRONTEND_PORT; then
        print_warning "Port $FRONTEND_PORT is in use. Trying to free it..."
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Start frontend with BROWSER=none to prevent auto-opening browser
    print_status "Starting React development server..."
    BROWSER=none npm start > react.log 2>&1 &
    local frontend_pid=$!
    
    # Give React time to start compiling
    print_status "React is compiling... This may take 30-60 seconds..."
    
    # Wait for React to be ready with a longer timeout and more patience
    local attempts=0
    local max_attempts=120  # 2 minutes
    
    while [ $attempts -lt $max_attempts ]; do
        # Check if the process is still running
        if ! kill -0 $frontend_pid 2>/dev/null; then
            print_error "React process died unexpectedly"
            return 1
        fi
        
        # Check if React is responding
        if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
            print_success "Frontend started successfully on port $FRONTEND_PORT"
            echo $frontend_pid
            return 0
        fi
        
        sleep 1
        ((attempts++))
        
        # Show progress every 15 seconds
        if [ $((attempts % 15)) -eq 0 ]; then
            print_status "Still waiting for React... (${attempts}s elapsed)"
        fi
    done
    
    print_error "React failed to start within ${max_attempts} seconds"
    kill $frontend_pid 2>/dev/null || true
    return 1
}

# Main function
main() {
    print_header "🎵 spotify-message Web App Startup"
    print_header "=================================="
    
    # Set up cleanup trap
    trap cleanup EXIT INT TERM
    
    # Check prerequisites
    check_prerequisites
    
    # Clean up any existing processes
    cleanup
    sleep 2
    
    # Start backend
    local backend_pid=$(start_backend)
    if [ $? -ne 0 ]; then
        print_error "Failed to start backend"
        exit 1
    fi
    
    # Start frontend
    local frontend_pid=$(start_frontend)
    if [ $? -ne 0 ]; then
        print_error "Failed to start frontend"
        kill $backend_pid 2>/dev/null || true
        exit 1
    fi
    
    # Success!
    echo ""
    print_header "🎉 Both servers started successfully!"
    print_header "====================================="
    echo ""
    print_success "📱 React App: http://localhost:$FRONTEND_PORT"
    print_success "🔧 API Endpoints: http://localhost:$BACKEND_PORT/api/"
    echo ""
    print_status "Press Ctrl+C to stop both servers"
    echo ""
    
    # Keep script running and monitor services
    while true; do
        sleep 10
        
        # Check if backend is still running
        if ! kill -0 $backend_pid 2>/dev/null; then
            print_error "Backend process died unexpectedly"
            break
        fi
        
        # Check if frontend is still running
        if ! kill -0 $frontend_pid 2>/dev/null; then
            print_error "Frontend process died unexpectedly"
            break
        fi
        
        # Check if services are responding
        if ! curl -s "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
            print_warning "Backend not responding to health checks"
        fi
        
        if ! curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
            print_warning "Frontend not responding"
        fi
    done
}

# Run main function
main "$@"
