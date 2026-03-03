#!/bin/bash
# =============================================================================
# Web Atlas Menu Bar Status App
# =============================================================================
# Starts the menu bar status indicator showing server status and stats.
# Add to Login Items for automatic startup with visual feedback.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS_DIR="$SCRIPT_DIR/analytics"

cd "$ANALYTICS_DIR"

# Activate virtual environment
if [[ -d ".venv" ]]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run start_logger.sh first."
    exit 1
fi

# Start menu bar app
python3 menubar_status.py
