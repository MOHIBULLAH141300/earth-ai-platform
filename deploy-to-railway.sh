#!/bin/bash

# EarthAI Platform - Railway Deployment Script
# This script helps deploy your EarthAI platform to Railway

echo "🚀 EarthAI Platform - Railway Deployment"
echo "========================================"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    curl -fsSL https://railway.app/install.sh | sh
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Create new project
echo "📦 Creating Railway project..."
railway init earthai-platform

# Link to current directory
echo "🔗 Linking to current directory..."
railway link

# Set environment variables
echo "⚙️ Setting up environment variables..."
railway variables set ENVIRONMENT=production
railway variables set SECRET_KEY=$(openssl rand -hex 32)

# Deploy
echo "🚀 Deploying to Railway..."
railway up

# Get the URL
echo "🌐 Getting your app URL..."
URL=$(railway domain)

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "Your EarthAI Platform is now live at:"
echo "🌍 Frontend: https://$URL"
echo "🔗 API: https://$URL/api"
echo ""
echo "Next steps:"
echo "1. Set up a custom domain in Railway dashboard (optional)"
echo "2. Configure any additional environment variables"
echo "3. Monitor your app in the Railway dashboard"
echo ""
echo "Happy deploying! 🚀"