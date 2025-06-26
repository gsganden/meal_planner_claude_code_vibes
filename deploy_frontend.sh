#!/bin/bash

echo "🚀 Deploying Recipe Chat Frontend to Modal"
echo ""

# Check if Modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI not found. Please install with: pip install modal"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "modal_frontend_simple.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Build the frontend with production environment
echo "📦 Building frontend for production..."
cd frontend_app

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production not found!"
    echo "Please create frontend_app/.env.production with:"
    echo "VITE_API_URL=https://your-username--recipe-chat-assistant-fastapi-app.modal.run"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📥 Installing dependencies..."
    npm install
fi

# Build with production environment
echo "🔨 Building with production configuration..."
npm run build

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

# Return to project root
cd ..

# Deploy to Modal
echo ""
echo "☁️  Deploying to Modal..."
modal deploy modal_frontend_simple.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Your frontend should be available at:"
echo "https://<your-username>--recipe-chat-frontend-serve.modal.run"
echo ""
echo "Note: Replace <your-username> with your Modal username"