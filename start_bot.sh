#!/bin/bash

# Activate your virtual environment
source ~/venv/bin/activate

# Run the app using uvicorn in background with nohup
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

echo "Telegram bot is now running in the background. Logs: app.log"

