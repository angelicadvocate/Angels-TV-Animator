#!/bin/bash
# Docker entrypoint script for Angels-TV-Animator

set -e

echo "===================================================================================="
echo "Angels-TV-Animator Docker Container Starting..."
echo "===================================================================================="
echo "  ___                   _          _____ _   _         ___        _                 _             "
echo " / _ \                 | |        |_   _| | | |       / _ \      (_)               | |            "
echo "/ /_\ \_ __   __ _  ___| |___ ______| | | | | |______/ /_\ \_ __  _ _ __ ___   __ _| |_ ___  _ __ "
echo "|  _  | '_ \ / _\` |/ _ \ / __|______| | | | | |______|  _  | '_ \| | '_ \` _ \ / _\` | __/ _ \| '__|"
echo "| | | | | | | (_| |  __/ \__ \      | | \ \_/ /      | | | | | | | | | | | | | (_| | || (_) | |   "
echo "\_| |_/_| |_|\__, |\___|_|___/      \_/  \___/       \_| |_/_| |_|_|_| |_| |_|\__,_|\__\___/|_|   "
echo "              __/ |                                                                               "
echo "             |___/                                                                                "
echo ""
echo "===================================================================================="

# Create directories if they don't exist
mkdir -p /app/animations /app/videos /app/data /app/data/config /app/data/logs

# Set permissions
chmod 755 /app/animations /app/videos /app/data /app/data/config /app/data/logs

# Check if required directories are mounted
if [ ! -d "/app/animations" ]; then
    echo "WARNING: /app/animations directory not found. Creating default..."
    mkdir -p /app/animations
fi

if [ ! -d "/app/videos" ]; then
    echo "WARNING: /app/videos directory not found. Creating default..."
    mkdir -p /app/videos
fi

# Initialize state file if it doesn't exist
if [ ! -f "/app/data/state.json" ]; then
    echo "Initializing state.json..."
    echo '{"current_animation": "brb.html"}' > /app/data/state.json
fi

# Display startup information
echo "Docker Configuration:"
echo "  Port: ${PORT:-8080}"
echo "  Server: eventlet (production WSGI)"
echo "  Flask Environment: ${FLASK_ENV:-production}"
echo "  Python Version: $(python --version)"
echo ""
echo "Media Directories:"
echo "  Animations: $(find /app/animations -maxdepth 1 -type f ! -name '*.md' ! -name '*.txt' | wc -l) files"
echo "  Videos: $(find /app/videos -maxdepth 1 -type f ! -name '*.md' ! -name '*.txt' | wc -l) files"
echo ""
echo "Network Information:"
echo "  Container IP: $(hostname -i 2>/dev/null || echo 'Not available')"
echo "  Listening on: 0.0.0.0:${PORT:-8080}"
echo ""
echo "Access URLs (replace [HOST_IP] with your computer's IP address):"
echo "  Smart TV/Display: http://[HOST_IP]:${PORT:-8080}"
echo "  Admin Panel: http://[HOST_IP]:${PORT:-8080}/admin"
echo "  WebSocket: ws://[HOST_IP]:${PORT:-8080}/socket.io/"
echo ""
echo "Getting Started:"
echo "  1. Find your IP: Windows: 'ipconfig' | macOS/Linux: 'ifconfig'"
echo "  2. Open Smart TV browser and go to: http://[YOUR_IP]:${PORT:-8080}"
echo "  3. Admin login - Default: admin / admin123 (CHANGE THESE!)"
echo "  4. Visit admin panel for instructions and file management"
echo ""
echo "===================================================================================="

# Execute the main application
exec "$@"