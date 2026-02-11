@echo off
REM 🎵 spotify-message Web App Startup Script for Windows
REM This script starts both the Flask backend and React frontend

echo 🎵 spotify-message Web App Startup
echo ==================================

REM Check if we're in the right directory
if not exist "package.json" (
    echo [ERROR] package.json not found. Please run this script from the web-react directory.
    pause
    exit /b 1
)

if not exist "server.py" (
    echo [ERROR] server.py not found. Please run this script from the web-react directory.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "..\venv" (
    echo [ERROR] Virtual environment not found. Please run from the project root: python -m venv venv
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules" (
    echo [WARNING] node_modules not found. Running npm install...
    npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
)

echo [INFO] Cleaning up existing processes...
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul

echo [INFO] Starting Flask backend...
start "Flask Backend" cmd /k "..\venv\Scripts\activate && python server.py"

REM Wait for backend to start
echo [INFO] Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Check if backend is running
:check_backend
curl -s http://localhost:8004/api/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] Still waiting for backend...
    timeout /t 2 /nobreak >nul
    goto check_backend
)

echo [SUCCESS] Backend started successfully on port 8004

echo [INFO] Starting React frontend...
start "React Frontend" cmd /k "set BROWSER=none && npm start"

REM Wait for frontend to start
echo [INFO] Waiting for React frontend to start...
timeout /t 10 /nobreak >nul

echo.
echo 🎉 Both servers are starting!
echo =============================
echo.
echo [SUCCESS] 📱 React App: http://localhost:3000
echo [SUCCESS] 🔧 API Endpoints: http://localhost:8004/api/
echo.
echo [INFO] React may take 30-60 seconds to fully compile...
echo [INFO] Press any key to stop both servers
echo.

pause

REM Cleanup
echo [INFO] Stopping servers...
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul
echo [SUCCESS] Servers stopped
