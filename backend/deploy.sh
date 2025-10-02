#!/bin/bash

echo "🚀 Deploying GPU Cloud Platform Backend..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "Installing DigitalOcean CLI..."
    brew install doctl
fi

# Authenticate (you'll need to add your DO token)
echo "Authenticating with DigitalOcean..."
doctl auth init

# Create app
echo "Creating DigitalOcean App..."
doctl apps create --spec .do/app.yaml

# Get app ID
APP_ID=$(doctl apps list --format ID --no-header | head -1)

echo "✅ App created with ID: $APP_ID"
echo "📊 View your app at: https://cloud.digitalocean.com/apps/$APP_ID"

# Deploy
echo "Deploying..."
doctl apps create-deployment $APP_ID

echo "🎉 Deployment initiated!"
echo ""
echo "Next steps:"
echo "1. Check deployment status: doctl apps get $APP_ID"
echo "2. Get app URL: doctl apps get $APP_ID --format LiveURL"
echo "3. View logs: doctl apps logs $APP_ID"