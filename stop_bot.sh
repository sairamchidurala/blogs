#!/bin/bash

# Stop the bot using PID file
if [ -f "app.pid" ]; then
    PID=$(cat app.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "Blog app stopped (PID: $PID)"
    else
        echo "Process not running"
    fi
    rm app.pid
else
    # Fallback: kill by process name
    pkill -f "uvicorn main:app"
    echo "Blog app stopped (fallback method)"
fi

