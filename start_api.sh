#!/bin/bash
# Start API Server Script
# Starts the FastAPI application server

cd /var/www/chatbot_FC
source venv/bin/activate

# Kill any existing server
pkill -f "uvicorn src.api.main:app" 2>/dev/null
sleep 2

# Start server in background
nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &

# Wait for server to start
sleep 3

# Check if server started successfully
if ps aux | grep -q "[u]vicorn src.api.main:app"; then
    echo "✅ API server started successfully"
    echo "📝 Logs: /tmp/api.log"
    echo "🌐 URL: http://localhost:8000"
    echo "📊 Health: http://localhost:8000/health"
    echo ""
    echo "To view logs: tail -f /tmp/api.log"
    echo "To stop server: pkill -f 'uvicorn src.api.main:app'"
else
    echo "❌ Failed to start server"
    echo "Check logs: tail -20 /tmp/api.log"
    exit 1
fi
