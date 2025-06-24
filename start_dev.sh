#!/bin/bash

# Start the Recipe Chat Assistant in development mode

echo "🚀 Starting Recipe Chat Assistant..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Initialize database if it doesn't exist
if [ ! -f "local_dev.db" ]; then
    echo "Initializing database..."
    python -c "
import asyncio
from src.db.database import init_db
asyncio.run(init_db())
print('✅ Database initialized!')
"
fi

# Start the server
echo "Starting server on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run with uvicorn for better development experience
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000