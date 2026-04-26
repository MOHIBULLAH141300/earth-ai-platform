@echo off
REM EarthAI Platform - Domain & Launch Checker
REM Helps you check domain availability and prepare for launch

echo.
echo 🌍 EarthAI Platform - Launch Preparation
echo ========================================
echo.

echo 🔍 Checking domain availability for earthai.com...
echo.

REM Try multiple ways to check domain
powershell -Command "& {try { $response = Invoke-WebRequest -Uri 'https://www.godaddy.com/domainsearch/find?domainToCheck=earthai.com' -Method GET; if ($response.Content -match 'available') { echo '✅ earthai.com appears to be AVAILABLE!' } else { echo '❌ earthai.com may not be available' } } catch { echo '❓ Could not check domain - check manually at godaddy.com' }}"

echo.
echo 📋 Next Steps:
echo =============
echo.
echo 1. 📝 Create GitHub repository:
echo    • Go to github.com
echo    • New repository: 'earth-ai-platform'
echo    • Make it PUBLIC
echo    • Don't add README/license
echo.
echo 2. 🚀 Push your code:
echo    cd C:\Users\Administrator\CascadeProjects\earth-ai-platform
echo    git remote set-url origin https://github.com/YOUR_USERNAME/earth-ai-platform.git
echo    git push -u origin master
echo.
echo 3. 🚂 Deploy to Railway:
echo    • Go to railway.app
echo    • Sign up with GitHub
echo    • Deploy from GitHub repo
echo    • Wait 5-10 minutes
echo.
echo 4. 🌐 Get custom domain:
echo    • Buy earthai.com ($10-15/year)
echo    • Configure DNS in Railway
echo.
echo 5. 🎉 Launch!
echo    www.earthai.com will be live!
echo.

echo 💡 Pro Tips:
echo ===========
echo • Railway Hobby plan: $5/month (perfect for starting)
echo • Domain registration: $12/year at GoDaddy
echo • Total cost: ~$17/month to change the world!
echo.

echo 🚀 Ready to launch EarthAI worldwide?
echo Check LAUNCH_EARTHAI_COM.md for detailed instructions!
echo.
pause