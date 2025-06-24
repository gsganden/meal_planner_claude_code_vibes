#!/bin/bash

echo "🔄 Restarting Recipe Chat Assistant servers..."

# Create logs directory if it doesn't exist
mkdir -p /Users/greg/repos/meal_planner_claude_code_vibes/logs

# Kill existing processes
echo "Stopping existing servers..."
pkill -f "uvicorn src.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

# Start backend with logging
echo "Starting backend server..."
cd /Users/greg/repos/meal_planner_claude_code_vibes
source venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..10}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8000"
    break
  fi
  sleep 1
done

# Start frontend with logging
echo "Starting frontend server..."
cd /Users/greg/repos/meal_planner_claude_code_vibes/frontend_app
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 3
for i in {1..10}; do
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running on http://localhost:3000"
    break
  elif curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo "✅ Frontend is running on http://localhost:3001"
    break
  fi
  sleep 1
done

echo ""
echo "🚀 Both servers are running!"
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000 or http://localhost:3001"
echo ""
echo "📋 Logs are being written to:"
echo "  Backend: logs/backend.log"
echo "  Frontend: logs/frontend.log"
echo ""
echo "To view logs in real-time:"
echo "  tail -f logs/backend.log"
echo "  tail -f logs/frontend.log"
echo ""
echo "To stop servers, run: pkill -f 'uvicorn' && pkill -f 'vite'"
echo ""
echo "Server PIDs:"
echo "Backend: $BACKEND_PID"
echo "Frontend: $FRONTEND_PID"