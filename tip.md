# Bugs & Solutions

## v0.1 → v0.2

### Bug: `internalSearch` events with "(blank)" query
**Cause**: `tab.title` used as query when switching to `arc://` or `chrome://` URLs, but title often empty or unhelpful.  
**Fix**: Removed false `internalSearch` triggers. Now uses `webNavigation.onCommitted` to detect actual omnibox→search flows via `transitionType: "typed"` + query extraction from URL.

### Bug: URLs stale for `input` events
**Cause**: Content script sent `location.href` which could be from previous page before SPA navigation.  
**Fix**: Background script now enriches events with `sender.tab.url` from the message sender context.

### Bug: Input event spam
**Cause**: Every keystroke generated a separate event.  
**Fix**: Throttled input events to 2-second batches with cumulative length and count.

### Bug: Missing search queries
**Cause**: Some search engines use different query params (`text`, `p`, `query` vs `q`).  
**Fix**: Extended query param extraction to cover multiple patterns.

## Notes

- Arc's command bar searches cannot be directly intercepted; detected via navigation type + URL query params
- Omnibox API requires keyword activation (`wa ` prefix) for direct input capture
- Window focus events help track Arc space switching

## Data Protection

- `events.jsonl` opened in append mode (`"a"`) — never truncated
- Automatic backup to `logs/backups/` when file exceeds 100MB
- Startup logs existing event count to confirm data preservation
- Server restart, system reboot, or crash will not delete data

## Log Compression

Use `log_rotate.py` to compress old logs:
- Keeps recent N days as readable JSONL
- Compresses older days to `archive/events_YYYY-MM-DD.jsonl.gz`
- Typical compression: 10-20x
- Compressed files searchable with `zgrep`, readable with `zcat`

## Safari Extension

Safari uses `browser.*` API (WebExtension standard) instead of `chrome.*`.
Key differences:
- No `webRequest` blocking mode
- No `omnibox` API  
- Stricter permission prompts
- Requires Xcode project wrapper for distribution
