#!/bin/bash
# =============================================================================
# Web Atlas Personal Analytics Server Startup Script
# =============================================================================
# This is YOUR OWN analytics server that runs locally on your machine.
# It receives browsing data from your browser extension and logs it to a file.
# ALL DATA STAYS ON YOUR COMPUTER - nothing is sent to external services.
#
# DATA PROTECTION: Log file is NEVER deleted. Server uses append-only writes.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS_DIR="$SCRIPT_DIR/analytics"
LOG_DIR="$ANALYTICS_DIR/logs"
LOG_FILE="$LOG_DIR/events.jsonl"

# Ensure log directory exists (never delete existing data)
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "🌐 Web Atlas Personal Analytics Server"
echo "=========================================="
echo "Data location: $LOG_FILE"
echo "Server endpoint: http://127.0.0.1:5000"
echo "Process ID: $$"
echo "Started at: $(date)"

# Show existing data stats
if [[ -f "$LOG_FILE" ]]; then
    EVENT_COUNT=$(wc -l < "$LOG_FILE" | tr -d ' ')
    FILE_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo "📊 Existing data: $EVENT_COUNT events ($FILE_SIZE)"
    echo "[$(date)] Server starting with $EVENT_COUNT existing events" >> "$LOG_DIR/server.log"
else
    echo "📊 Starting fresh (no existing data)"
fi
echo "=========================================="

cd "$ANALYTICS_DIR"

# Check if virtual environment exists
if [[ ! -d ".venv" ]]; then
    echo "📦 Setting up Python environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    echo "[$(date)] Virtual environment created" >> "$LOG_DIR/server.log"
else
    source .venv/bin/activate
fi

# macOS notification on startup
if command -v osascript &> /dev/null; then
    osascript -e 'display notification "Server running on port 5000" with title "🌐 Web Atlas" subtitle "Analytics server started"' 2>/dev/null || true
fi

# Start the server
echo "🚀 Starting Web Atlas Logger Server..."
echo "[$(date)] Server started on http://127.0.0.1:5000" >> "$LOG_DIR/server.log"
python3 logger_server.py