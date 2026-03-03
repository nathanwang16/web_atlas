"""
logger_server.py — Web Atlas Event Ingestion Server

FastAPI server that receives browser events and writes them to JSONL log.
Events are enriched with readable timestamps.

DATA PROTECTION: Log file is opened in APPEND mode only. Restarts never delete data.

Run: uvicorn logger_server:app --host 127.0.0.1 --port 5000
"""

import json
import logging
import datetime
import shutil
from pathlib import Path

from fastapi import FastAPI, Request
import uvicorn

# ---------- Logging Setup ----------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("webatlas")

# ---------- Paths ----------
BASE = Path(__file__).parent
LOG_FILE = BASE / "logs" / "events.jsonl"
BACKUP_DIR = BASE / "logs" / "backups"
LOG_FILE.parent.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)


def backup_log_if_large(threshold_mb: float = 100):
    """Create timestamped backup if log exceeds threshold."""
    if not LOG_FILE.exists():
        return
    size_mb = LOG_FILE.stat().st_size / 1024 / 1024
    if size_mb > threshold_mb:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"events_{timestamp}.jsonl"
        shutil.copy2(LOG_FILE, backup_path)
        log.info(f"Backup created: {backup_path} ({size_mb:.1f} MB)")


# Run backup check on startup
backup_log_if_large()

# ---------- App ----------
app = FastAPI(title="Web Atlas Logger", version="0.2")


def format_timestamp(ms_epoch: int) -> str:
    """Convert millisecond epoch to readable timestamp."""
    try:
        dt = datetime.datetime.fromtimestamp(ms_epoch / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except (ValueError, OSError):
        return "invalid"


@app.post("/event")
async def ingest(req: Request):
    """Ingest a single event from the browser extension."""
    try:
        data = await req.json()
    except Exception as e:
        log.warning(f"Invalid JSON payload: {e}")
        return {"ok": False, "error": "invalid_json"}

    # Enrich with timestamp
    if "t" in data:
        data["timestamp"] = format_timestamp(data["t"])
        data["t_original"] = data.pop("t")
    else:
        now = datetime.datetime.now()
        data["timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        data["t_original"] = "generated"

    # Write to log file
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False) + "\n")
    except IOError as e:
        log.error(f"Failed to write event: {e}")
        return {"ok": False, "error": "write_failed"}

    log.debug(f"Event: {data.get('type', 'unknown')}")
    return {"ok": True}


@app.get("/ping")
def ping():
    """Health check endpoint."""
    return {"status": "alive", "log_file": str(LOG_FILE)}


@app.get("/stats")
def stats():
    """Return basic log file statistics."""
    if not LOG_FILE.exists():
        return {"events": 0, "size_bytes": 0}
    
    line_count = sum(1 for _ in LOG_FILE.open("r", encoding="utf-8"))
    size = LOG_FILE.stat().st_size
    return {
        "events": line_count,
        "size_bytes": size,
        "size_mb": round(size / 1024 / 1024, 2)
    }


if __name__ == "__main__":
    # Verify data persistence on startup
    if LOG_FILE.exists():
        line_count = sum(1 for _ in LOG_FILE.open("r", encoding="utf-8"))
        log.info(f"Existing log found: {line_count:,} events preserved")
    else:
        log.info("Starting fresh log file")
    
    log.info(f"Writing to {LOG_FILE} (append mode - data never deleted)")
    uvicorn.run("logger_server:app", host="127.0.0.1", port=5000, reload=False)
