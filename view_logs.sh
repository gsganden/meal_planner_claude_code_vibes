#!/bin/bash

# Simple script to view server logs

if [ "$1" = "backend" ]; then
    echo "📋 Viewing backend logs (Ctrl+C to stop)..."
    tail -f logs/backend.log
elif [ "$1" = "frontend" ]; then
    echo "📋 Viewing frontend logs (Ctrl+C to stop)..."
    tail -f logs/frontend.log
elif [ "$1" = "both" ]; then
    echo "📋 Viewing both logs (Ctrl+C to stop)..."
    # Use multitail if available, otherwise fall back to basic approach
    if command -v multitail &> /dev/null; then
        multitail logs/backend.log logs/frontend.log
    else
        echo "Backend logs:" 
        tail -f logs/backend.log &
        BACKEND_TAIL_PID=$!
        echo ""
        echo "Frontend logs:"
        tail -f logs/frontend.log &
        FRONTEND_TAIL_PID=$!
        
        # Wait for Ctrl+C
        trap "kill $BACKEND_TAIL_PID $FRONTEND_TAIL_PID 2>/dev/null; exit" INT
        wait
    fi
else
    echo "Usage: ./view_logs.sh [backend|frontend|both]"
    echo ""
    echo "Examples:"
    echo "  ./view_logs.sh backend   - View backend logs"
    echo "  ./view_logs.sh frontend  - View frontend logs"
    echo "  ./view_logs.sh both      - View both logs"
fi