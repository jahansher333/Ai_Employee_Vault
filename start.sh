#!/bin/bash

# Start backend API on port 5000 (background)
echo "Starting API server on port 5000..."
uvicorn scripts.api_server:app --host 0.0.0.0 --port 5000 &

# Wait for API to be ready
sleep 2

# Start Next.js dashboard on port 3000 (foreground)
echo "Starting Dashboard on port 3000..."
cd /app/dashboard
API_URL=http://localhost:5000 node server.js
