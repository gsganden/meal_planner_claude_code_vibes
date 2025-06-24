#!/bin/bash

# Start the Recipe Chat Assistant Frontend

echo "🚀 Starting Recipe Chat Assistant Frontend..."

cd frontend_app

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the dev server
echo "Starting frontend on http://localhost:3000"
echo "Make sure the backend is running on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev