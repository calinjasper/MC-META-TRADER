#!/bin/bash

echo "================================================"
echo " MC-META-TRADER with PocketBase Integration"
echo "================================================"
echo ""

# Check if PocketBase exists
if [ ! -f "pocketbase/pocketbase" ]; then
    echo "WARNING: PocketBase not found in pocketbase/pocketbase"
    echo "Please download PocketBase from: https://github.com/pocketbase/pocketbase/releases"
    echo "Extract pocketbase to the pocketbase/ directory and make it executable:"
    echo "  chmod +x pocketbase/pocketbase"
    echo ""
    echo "Starting trading system WITHOUT database storage..."
    echo ""
    sleep 3
    python3 src/main.py
    exit 0
fi

# Start PocketBase Server in background
echo "Starting PocketBase Server..."
cd pocketbase
./pocketbase serve &
PB_PID=$!
cd ..

# Wait for PocketBase to start
echo "Waiting for PocketBase to initialize..."
sleep 5

# Start Trading System
echo ""
echo "Starting Trading System..."
echo ""
python3 src/main.py

# Cleanup: kill PocketBase when trading system exits
echo ""
echo "Shutting down PocketBase..."
kill $PB_PID 2>/dev/null

echo "System stopped."

