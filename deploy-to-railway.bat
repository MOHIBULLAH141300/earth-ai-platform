@echo off
REM EarthAI Platform - Railway Deployment Script (Windows)
REM This script helps deploy your EarthAI platform to Railway

echo 🚀 EarthAI Platform - Railway Deployment
echo ========================================
echo.

REM Check if Railway CLI is installed
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Railway CLI not found. Installing...
    powershell -Command "Invoke-WebRequest -Uri 'https://railway.app/install.sh' -OutFile 'install-railway.sh'"
    bash install-railway.sh
    del install-railway.sh
)

REM Login to Railway
echo 🔐 Logging into Railway...
railway login

REM Create new project
echo 📦 Creating Railway project...
railway init earthai-platform

REM Link to current directory
echo 🔗 Linking to current directory...
railway link

REM Set environment variables
echo ⚙️ Setting up environment variables...
for /f %%i in ('openssl rand -hex 32 2^>nul ^|^| powershell -Command "$bytes = New-Object Byte[] 32; (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); [System.BitConverter]::ToString($bytes).Replace('-','').ToLower()"') do set SECRET_KEY=%%i
railway variables set ENVIRONMENT=production
railway variables set SECRET_KEY=%SECRET_KEY%

REM Deploy
echo 🚀 Deploying to Railway...
railway up

REM Get the URL
echo 🌐 Getting your app URL...
for /f %%i in ('railway domain') do set URL=%%i

echo.
echo 🎉 Deployment Complete!
echo ======================
echo Your EarthAI Platform is now live at:
echo 🌍 Frontend: https://%URL%
echo 🔗 API: https://%URL%/api
echo.
echo Next steps:
echo 1. Set up a custom domain in Railway dashboard (optional)
echo 2. Configure any additional environment variables
echo 3. Monitor your app in the Railway dashboard
echo.
echo Happy deploying! 🚀
pause