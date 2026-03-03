"""
log_rotate.py — Web Atlas Log Rotation & Compression

Compresses old log entries while keeping recent data readable.
Rotates by date: current day stays as JSONL, older days compressed to .gz

Usage: python log_rotate.py [--days 7] [--dry-run]

Compressed files can still be read:
  zcat events_2026-01-20.jsonl.gz | head
  zgrep "searchRequest" events_2026-01-20.jsonl.gz
  zcat *.gz | python -c "import sys,json; [print(json.loads(l)['type']) for l in sys.stdin]"
"""

import gzip
import json
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ---------- Setup ----------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("rotate")

BASE = Path(__file__).parent
LOG_FILE = BASE / "logs" / "events.jsonl"
ARCHIVE_DIR = BASE / "logs" / "archive"


def parse_date(timestamp_str: str) -> str:
    """Extract date (YYYY-MM-DD) from timestamp string."""
    try:
        return timestamp_str.split(" ")[0]
    except (AttributeError, IndexError):
        return None


def rotate_logs(keep_days: int = 7, dry_run: bool = False):
    """
    Rotate logs: keep recent days as JSONL, compress older days.
    
    Args:
        keep_days: Keep this many days uncompressed
        dry_run: If True, only show what would be done
    """
    if not LOG_FILE.exists():
        log.info("No log file found")
        return
    
    ARCHIVE_DIR.mkdir(exist_ok=True)
    cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    
    log.info(f"Rotating logs older than {cutoff_date} (keeping {keep_days} days)")
    
    # Group events by date
    events_by_date = defaultdict(list)
    recent_events = []
    
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                date = parse_date(ev.get("timestamp", ""))
                if date and date < cutoff_date:
                    events_by_date[date].append(line)
                else:
                    recent_events.append(line)
            except json.JSONDecodeError:
                recent_events.append(line)  # Keep malformed lines
    
    if not events_by_date:
        log.info("No old events to archive")
        return
    
    # Archive old events by date
    total_archived = 0
    for date, events in sorted(events_by_date.items()):
        archive_path = ARCHIVE_DIR / f"events_{date}.jsonl.gz"
        
        if dry_run:
            log.info(f"[DRY-RUN] Would archive {len(events)} events to {archive_path.name}")
        else:
            # Append to existing archive if it exists
            mode = "ab" if archive_path.exists() else "wb"
            with gzip.open(archive_path, mode) as gz:
                for event_line in events:
                    gz.write((event_line + "\n").encode("utf-8"))
            log.info(f"Archived {len(events)} events to {archive_path.name}")
        
        total_archived += len(events)
    
    # Rewrite main log with only recent events
    if not dry_run and total_archived > 0:
        # Backup before rewriting
        backup_path = LOG_FILE.with_suffix(".jsonl.bak")
        shutil.copy2(LOG_FILE, backup_path)
        
        with LOG_FILE.open("w", encoding="utf-8") as f:
            for line in recent_events:
                f.write(line + "\n")
        
        # Remove backup after successful write
        backup_path.unlink()
        
        log.info(f"Main log now has {len(recent_events)} events (archived {total_archived})")
    
    # Show compression stats
    if not dry_run:
        show_stats()


def show_stats():
    """Show log file statistics."""
    print("\n=== Log Statistics ===")
    
    if LOG_FILE.exists():
        size_mb = LOG_FILE.stat().st_size / 1024 / 1024
        line_count = sum(1 for _ in LOG_FILE.open("r", encoding="utf-8"))
        print(f"Current log: {line_count:,} events ({size_mb:.2f} MB)")
    
    if ARCHIVE_DIR.exists():
        archives = list(ARCHIVE_DIR.glob("*.gz"))
        if archives:
            total_compressed = sum(f.stat().st_size for f in archives)
            print(f"Archives: {len(archives)} files ({total_compressed / 1024 / 1024:.2f} MB compressed)")
            
            # Estimate uncompressed size (typical 10x ratio)
            print(f"Estimated original: ~{total_compressed * 10 / 1024 / 1024:.1f} MB")


def read_archive(date: str) -> list:
    """Read events from a specific date's archive."""
    archive_path = ARCHIVE_DIR / f"events_{date}.jsonl.gz"
    if not archive_path.exists():
        return []
    
    events = []
    with gzip.open(archive_path, "rt", encoding="utf-8") as gz:
        for line in gz:
            if line.strip():
                events.append(json.loads(line))
    return events


def search_archives(pattern: str, event_type: str = None) -> list:
    """Search across all archives for matching events."""
    results = []
    
    for archive_path in sorted(ARCHIVE_DIR.glob("*.gz")):
        with gzip.open(archive_path, "rt", encoding="utf-8") as gz:
            for line in gz:
                if pattern.lower() in line.lower():
                    try:
                        ev = json.loads(line)
                        if event_type is None or ev.get("type") == event_type:
                            results.append(ev)
                    except json.JSONDecodeError:
                        pass
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate and compress Web Atlas logs")
    parser.add_argument("--days", type=int, default=7, help="Keep this many days uncompressed (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--stats", action="store_true", help="Show log statistics only")
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    else:
        rotate_logs(keep_days=args.days, dry_run=args.dry_run)
