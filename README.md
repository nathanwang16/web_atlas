# Web Atlas

Build an atlas of the online world YOU have explored.

**Privacy Note**: All data stays local. You own your data.

## Overview

Web Atlas is a self-analytics toolkit that captures rich metadata about your browsing behavior:
- Chromium extension (Chrome, Arc, Brave, Edge)
- Local logging server (FastAPI)
- Analysis/visualization scripts

## Quick Start

```bash
# 1. Install dependencies
cd analytics && pip install -r requirements.txt

# 2. Start logger server
python logger_server.py

# 3. Load extension in browser
#    - Open chrome://extensions or arc://extensions
#    - Enable "Developer mode"
#    - Click "Load unpacked" → select extension/ folder

# 4. Browse the web — events are logged automatically

# 5. Analyze your data
python analyse.py
```

## Auto-Start on Login (macOS)

```bash
# Install LaunchAgents
cp com.webatlas.logger.plist ~/Library/LaunchAgents/
cp com.webatlas.menubar.plist ~/Library/LaunchAgents/  # Optional: menu bar status

# Activate
launchctl load ~/Library/LaunchAgents/com.webatlas.logger.plist
launchctl load ~/Library/LaunchAgents/com.webatlas.menubar.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.webatlas.logger.plist
```

## Menu Bar Status App

The optional menu bar app (`menubar_status.py`) shows:
- 🌐 Green globe = server running
- ⚠️ Warning = server offline
- Event count and log size
- Quick actions: refresh, open logs, run analysis

Start manually: `python analytics/menubar_status.py`

## Data Protection

**Your data is never deleted by restarts.** Safeguards:
- Log file opened in **append mode only**
- Automatic backup when log exceeds 100MB
- Startup logs existing event count to confirm preservation
- Backups stored in `analytics/logs/backups/`

## Log Rotation & Compression

When logs grow large, use the rotation tool to compress old data:

```bash
cd analytics

# Preview what will be rotated (dry run)
python log_rotate.py --dry-run

# Rotate: keep 7 days uncompressed, compress older
python log_rotate.py --days 7

# Show statistics
python log_rotate.py --stats
```

Compressed files remain readable:
```bash
# Read compressed archive
zcat logs/archive/events_2026-01-20.jsonl.gz | head

# Search across archives
zgrep "searchRequest" logs/archive/*.gz

# Count events by type in archive
zcat logs/archive/*.gz | jq -r '.type' | sort | uniq -c
```

## Safari Extension

A Safari Web Extension is available in `safari-extension/`. To build:

```bash
# Convert Chrome extension to Safari (requires Xcode)
xcrun safari-web-extension-converter extension --project-location safari-extension --app-name "Web Atlas"
```

Then build in Xcode and enable in Safari → Settings → Extensions.

See `safari-extension/README.md` for details.

## Event Types

### Background Script Events (bg.js)

| Event | Description | Fields |
|-------|-------------|--------|
| `tabSwitch` | User switches to a tab | `url`, `title`, `domain` |
| `tabCreated` | New tab opened | `url`, `openerTabId` |
| `tabClosed` | Tab closed | `tabId` |
| `dwell` | Time spent on page before leaving | `url`, `ms` |
| `navigation` | Page navigation completed | `url`, `domain` |
| `urlTyped` | URL typed in address bar | `url`, `domain` |
| `pageReload` | Page reloaded | `url` |
| `historyNavigation` | Back/forward navigation | `url`, `direction` |
| `searchRequest` | Outgoing search engine query | `engine`, `query`, `url` |
| `omniboxSearch` | Search via browser URL bar | `query`, `url`, `engine` |
| `omniboxInput` | Direct omnibox input (keyword: `wa`) | `query`, `disposition` |
| `windowFocus` | Browser window focus changed | `focused`, `windowId` |
| `arcCommand` | Arc command bar activation | `action`, `title` |

### Content Script Events (cs.js)

| Event | Description | Fields |
|-------|-------------|--------|
| `input` | Text input (throttled, 2s) | `len`, `eventCount`, `url` |
| `copy` | Clipboard copy | `len`, `url` |
| `cut` | Clipboard cut | `len`, `url` |
| `paste` | Clipboard paste | `len`, `url` |
| `scroll` | Page scroll depth (on unload) | `maxDepthPercent`, `url` |
| `linkClick` | Link clicked | `targetUrl`, `isExternal`, `linkText` |

## Arc Browser Specifics

Arc browser uses Chromium but has unique UI elements:

- **Command Bar**: `arc://` URLs indicate command bar activation
- **Spaces**: Window focus events track space switching  
- **Little Arc**: Captured as new window focus
- **Boosts**: Standard page events (no special detection yet)

The extension best-effort captures Arc-specific behavior via:
- `arcCommand` events for command bar activation
- `windowFocus` events for space/window switching
- `omniboxSearch` for command bar → search engine flows

## File Structure

```
web_atlas/
├── extension/                  # Chrome/Arc extension
│   ├── manifest.json
│   ├── bg.js                   # Background service worker
│   └── cs.js                   # Content script
├── safari-extension/           # Safari Web Extension
│   ├── WebAtlas/Resources/     # Extension JS files
│   └── README.md               # Safari-specific instructions
├── analytics/
│   ├── logger_server.py        # FastAPI event ingestion
│   ├── menubar_status.py       # Menu bar status app (macOS)
│   ├── log_rotate.py           # Log rotation & compression
│   ├── analyse.py              # Event analysis + visualization
│   ├── requirements.txt
│   └── logs/
│       ├── events.jsonl        # Current log (append-only)
│       └── archive/            # Compressed old logs (.gz)
├── start_logger.sh             # Server startup script
├── start_menubar.sh            # Menu bar app startup
├── com.webatlas.logger.plist   # LaunchAgent: server
└── com.webatlas.menubar.plist  # LaunchAgent: menu bar
```

## Log Format

Events are stored as JSONL (one JSON object per line):

```json
{"type": "tabSwitch", "url": "https://...", "title": "...", "domain": "...", "timestamp": "2026-01-25 12:34:56.789", "t_original": 1769402096789}
{"type": "dwell", "url": "https://...", "ms": 15432, "timestamp": "..."}
{"type": "searchRequest", "engine": "www.google.com", "query": "web atlas", "url": "https://..."}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/event` | POST | Ingest event from extension |
| `/ping` | GET | Health check |
| `/stats` | GET | Log file statistics |

## Analysis

```python
# Load and explore events
import pandas as pd, json, pathlib
events = [json.loads(l) for l in pathlib.Path("logs/events.jsonl").read_text().splitlines()]
df = pd.DataFrame(events)

# Event distribution
df["type"].value_counts()

# Top domains by dwell time
dwell = df[df.type == "dwell"]
dwell.groupby(dwell.url.apply(lambda u: urlparse(u).netloc))["ms"].sum().sort_values(ascending=False)

# Recent searches
df[df.type.isin(["searchRequest", "omniboxSearch"])][["timestamp", "query"]].tail(20)
```

## Known Limitations

1. **Arc Command Bar**: Cannot directly intercept command bar text input; detected via navigation patterns
2. **Omnibox API**: Requires keyword prefix (`wa `) for direct capture
3. **Iframes**: Content script cannot access iframe content
4. **Private Windows**: Extension must be explicitly enabled

## Privacy

- All data stored locally in `analytics/logs/events.jsonl`
- No external servers, no telemetry
- Exclude sensitive URLs by modifying `isInteresting()` in `bg.js`