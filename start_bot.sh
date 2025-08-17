#!/bin/bash

# Check if virtual environment exists
source ~/venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
fi

# Create logs directory
mkdir -p logs

# Kill existing process if running
if [ -f "app.pid" ]; then
    kill $(cat app.pid) 2>/dev/null || true
    rm app.pid
fi

# Run the app
nohup uvicorn main_clean:app --host 0.0.0.0 --port 8000 --log-level info > logs/app.log 2>&1 &
echo $! > app.pid

echo "Blog app started successfully!"
echo "PID: $(cat app.pid)"
echo "Logs: logs/app.log"
echo "Health check: http://localhost:8000/health"

