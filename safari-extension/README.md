# Web Atlas Safari Extension

Safari Web Extension version of Web Atlas logger.

## Building the Extension

Safari Web Extensions require an Xcode project wrapper. Use Apple's converter tool:

### Option 1: Convert from Chrome Extension (Recommended)

```bash
# Use Apple's conversion tool (requires Xcode 12+)
xcrun safari-web-extension-converter ../extension --project-location . --app-name "Web Atlas"
```

This creates a complete Xcode project from the Chrome extension.

### Option 2: Manual Xcode Project

1. Open Xcode → File → New → Project
2. Choose "Safari Extension App"
3. Copy the files from `WebAtlas/Resources/` into the extension's Resources folder
4. Build and run

## Installation

1. Build the project in Xcode (⌘B)
2. Run the app once to register the extension
3. Open Safari → Settings → Extensions
4. Enable "Web Atlas Logger"
5. Grant permissions when prompted

## Differences from Chrome Version

| Feature | Chrome/Arc | Safari |
|---------|------------|--------|
| API namespace | `chrome.*` | `browser.*` |
| webRequest API | Full support | Limited (no blocking) |
| Omnibox API | Supported | Not available |
| Permissions | Auto-grant | User must approve |
| Distribution | Direct install | App Store or notarized |

## Permissions Required

- **Tabs**: Track tab switches and URLs
- **Web Navigation**: Detect navigation types
- **All URLs**: Access page content

Safari will prompt users to allow each permission.

## Events Captured

Same as Chrome version:
- `tabSwitch`, `tabCreated`, `tabClosed`
- `dwell`, `navigation`, `urlTyped`, `pageReload`
- `omniboxSearch` (detected via URL patterns)
- `windowFocus`
- `input`, `copy`, `cut`, `paste`, `scroll`, `linkClick`

All events include `browser: "safari"` field for identification.

## Troubleshooting

### Extension not appearing
- Ensure the app is built and run at least once
- Check Safari → Settings → Extensions → Developer

### Events not logging
- Verify logger server is running: `curl http://127.0.0.1:5000/ping`
- Check Safari's Web Inspector for console errors
- Ensure permissions are granted in Safari settings

### "Allow for one day" prompts
Safari requires periodic permission re-approval. For persistent access:
1. Safari → Settings → Websites → Web Atlas
2. Set to "Allow" for all websites
