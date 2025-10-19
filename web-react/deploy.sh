#!/bin/bash

# 🚀 Zingaroo Deployment Script
echo "🦘 Deploying Zingaroo..."

# Build the React app
echo "📦 Building React app..."
npm run build

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📁 Build files created in ./build/"
    
    # Create deployment package
    echo "📦 Creating deployment package..."
    tar -czf zingaroo-deploy.tar.gz build/
    
    echo "🎉 Ready for deployment!"
    echo ""
    echo "🌐 Deployment Options:"
    echo "1. Netlify (Recommended):"
    echo "   - Go to https://netlify.com"
    echo "   - Drag the 'build' folder to deploy"
    echo "   - Get instant URL: zingaroo.netlify.app"
    echo ""
    echo "2. Railway (Backend):"
    echo "   - Go to https://railway.app"
    echo "   - Connect GitHub repo"
    echo "   - Deploy Flask backend"
    echo ""
    echo "3. Custom Domain:"
    echo "   - Check zingaroo.com availability"
    echo "   - Use free subdomain: zingaroo.netlify.app"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Deploy frontend to Netlify"
    echo "2. Deploy backend to Railway"
    echo "3. Update API URLs in production"
    echo "4. Test Spotify OAuth flow"
    echo "5. Share your live app!"
    
else
    echo "❌ Build failed!"
    exit 1
fi
