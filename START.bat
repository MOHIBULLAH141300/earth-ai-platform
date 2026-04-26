@echo off
REM EarthAI Platform - Startup Script
REM ===================================

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║       🌍 EarthAI Platform - Startup                          ║
echo ║       Fully AI-based Platform for Earth Science Analysis     ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check if Docker is running
echo [1/4] Checking Docker Desktop...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Docker is not running or not installed.
    echo.
    echo Please ensure Docker Desktop is installed and running:
    echo   → Download: https://www.docker.com/products/docker-desktop
    echo   → Start Docker Desktop and wait 30 seconds
    echo   → Then run this script again
    echo.
    pause
    exit /b 1
)
echo ✅ Docker is running

REM Navigate to project directory
cd /d "%~dp0"
echo.
echo [2/4] Starting services...
echo Building and starting all services (this may take 2-3 minutes on first run)
echo.

REM Start services
docker-compose up -d

REM Check if startup was successful
timeout /t 5 /nobreak
docker-compose ps | find "Up" >nul
if errorlevel 1 (
    echo ❌ Services failed to start. Checking logs...
    docker-compose logs
    pause
    exit /b 1
)

echo.
echo ✅ All services started successfully!
echo.
echo [3/4] Waiting for services to be ready...
echo Waiting up to 60 seconds for all services to initialize...

REM Wait for API to be ready
set max_tries=60
set count=0
:wait_loop
timeout /t 1 /nobreak >nul
set /a count=%count%+1

curl -s http://localhost:8000/api/system/health >nul 2>&1
if errorlevel 1 (
    if %count% lss %max_tries% (
        goto wait_loop
    ) else (
        echo ⚠️  Services are starting but may not be fully ready yet
    )
)

echo.
echo [4/4] Platform ready!
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║       🚀 EarthAI Platform is Running!                        ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 📱 Frontend:       http://localhost:3000
echo 🔧 API Docs:       http://localhost:8000/api/docs
echo 📊 Grafana:        http://localhost:3001  (admin/admin)
echo 💾 PgAdmin:        http://localhost:5050  (admin@earthai.com/admin)
echo 🧪 MLflow:         http://localhost:5000
echo.
echo 📚 Documentation:
echo   • Quick Start:    GETTING_STARTED.md
echo   • Full Setup:     DEPLOYMENT_GUIDE.md
echo   • Features:       BUILD_SUMMARY.md
echo   • Architecture:   README.md
echo.
echo 🎯 Try Now:
echo   1. Open http://localhost:3000 in your browser
echo   2. Go to "Chatbot" tab
echo   3. Type: "Predict landslide risk for mountains"
echo   4. Watch the magic happen!
echo.
echo ⏹️  To Stop Services:
echo   Run:  docker-compose down
echo.
pause
