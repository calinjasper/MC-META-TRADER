#!/bin/bash
# Start PocketBase on Network IP
# This script starts PocketBase to accept connections from network IP 192.168.173.112

echo "================================================================================"
echo "  Starting PocketBase on Network Interface"
echo "================================================================================"
echo ""
echo "This will start PocketBase to accept connections from:"
echo "  - Localhost: http://127.0.0.1:8090"
echo "  - Network IP: http://192.168.173.112:8090"
echo "  - All network interfaces: http://0.0.0.0:8090"
echo ""
echo "Press Ctrl+C to stop PocketBase"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT/pocketbase"

# Start PocketBase with network binding
./pocketbase serve --http=0.0.0.0:8090

