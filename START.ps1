# EarthAI Platform - PowerShell Startup Script
# ============================================

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       🌍 EarthAI Platform - Startup                          ║" -ForegroundColor Cyan
Write-Host "║       Fully AI-based Platform for Earth Science Analysis     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/4] Checking Docker Desktop..." -ForegroundColor Yellow

try {
    $docker = docker ps 2>&1
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure Docker Desktop is installed and running:" -ForegroundColor Yellow
    Write-Host "  → Download: https://www.docker.com/products/docker-desktop" 
    Write-Host "  → Start Docker Desktop and wait 30 seconds"
    Write-Host "  → Then run this script again"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Start Services
Write-Host ""
Write-Host "[2/4] Starting services..." -ForegroundColor Yellow
Write-Host "Building and starting all services (this may take 2-3 minutes on first run)"
Write-Host ""

Set-Location $PSScriptRoot
docker-compose up -d

Start-Sleep -Seconds 5

# Check if services started
$status = docker-compose ps
if ($status -notmatch "Up") {
    Write-Host "❌ Services failed to start. Checking logs..." -ForegroundColor Red
    docker-compose logs
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/4] Waiting for services to be ready..." -ForegroundColor Yellow
Write-Host "Waiting up to 60 seconds for all services to initialize..."

# Wait for API
$count = 0
$maxTries = 60
while ($count -lt $maxTries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/system/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Services are ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Still loading
    }
    $count++
    Start-Sleep -Seconds 1
}

if ($count -eq $maxTries) {
    Write-Host "⚠️  Services are starting but may not be fully ready yet" -ForegroundColor Yellow
}

# Step 4: Display URLs
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       🚀 EarthAI Platform is Running!                        ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 Frontend:       " -ForegroundColor Cyan -NoNewLine
Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host "🔧 API Docs:       " -ForegroundColor Cyan -NoNewLine
Write-Host "http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📊 Grafana:        " -ForegroundColor Cyan -NoNewLine
Write-Host "http://localhost:3001  (admin/admin)" -ForegroundColor Green
Write-Host "💾 PgAdmin:        " -ForegroundColor Cyan -NoNewLine
Write-Host "http://localhost:5050  (admin@earthai.com/admin)" -ForegroundColor Green
Write-Host "🧪 MLflow:         " -ForegroundColor Cyan -NoNewLine
Write-Host "http://localhost:5000" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   • Quick Start:    GETTING_STARTED.md"
Write-Host "   • Full Setup:     DEPLOYMENT_GUIDE.md"
Write-Host "   • Features:       BUILD_SUMMARY.md"
Write-Host "   • Architecture:   README.md"
Write-Host ""
Write-Host "🎯 Try Now:" -ForegroundColor Cyan
Write-Host "   1. Open http://localhost:3000 in your browser"
Write-Host "   2. Go to ""Chatbot"" tab"
Write-Host "   3. Type: ""Predict landslide risk for mountains"""
Write-Host "   4. Watch the magic happen!"
Write-Host ""
Write-Host "⏹️  To Stop Services:" -ForegroundColor Cyan
Write-Host "   Run:  docker-compose down"
Write-Host ""
Write-Host "Press Enter to keep the terminal open and monitor services..." -ForegroundColor Yellow
Read-Host

# Keep monitoring
Write-Host ""
Write-Host "Monitoring services. Press Ctrl+C to stop." -ForegroundColor Yellow
docker-compose logs -f
