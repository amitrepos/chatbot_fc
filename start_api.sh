#!/bin/bash
# Start FlexCube AI Assistant API Server

cd /var/www/chatbot_FC
source venv/bin/activate

echo "Starting FlexCube AI Assistant API..."
echo "Web interface will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

