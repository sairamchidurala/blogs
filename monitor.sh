#!/bin/bash

# Simple monitoring script
check_status() {
    if [ -f "app.pid" ]; then
        PID=$(cat app.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "✅ App is running (PID: $PID)"
            curl -s http://localhost:8000/health > /dev/null && echo "✅ Health check passed" || echo "❌ Health check failed"
        else
            echo "❌ App is not running (stale PID file)"
            rm app.pid
        fi
    else
        echo "❌ App is not running (no PID file)"
    fi
}

case "$1" in
    status)
        check_status
        ;;
    logs)
        tail -f logs/app.log
        ;;
    restart)
        ./stop_bot.sh
        sleep 2
        ./start_bot.sh
        ;;
    *)
        echo "Usage: $0 {status|logs|restart}"
        exit 1
        ;;
esac