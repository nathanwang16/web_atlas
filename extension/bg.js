/*********************************************************************
 * bg.js — Web Atlas Self-Analytics (Arc / Chrome / Safari)
 * 
 * Event Types Captured:
 *   - tabSwitch:      User switches to a different tab
 *   - tabCreated:     New tab opened
 *   - tabClosed:      Tab closed
 *   - dwell:          Time spent on a page before leaving
 *   - navigation:     Page navigation (typed, link, reload, back/forward)
 *   - searchRequest:  Outgoing search engine query (Google, DuckDuckGo, etc.)
 *   - omniboxSearch:  Direct search from browser omnibox/command bar
 *   - windowFocus:    Browser window focus changed
 *   - arcCommand:     Arc-specific command bar activation (best effort)
 * 
 * Browser Compatibility:
 *   - Chrome/Arc: Uses chrome.* API
 *   - Safari: Uses browser.* API (WebExtension standard)
 *********************************************************************/

// ---------- Browser API Compatibility ----------
// Safari uses 'browser', Chrome uses 'chrome'. Normalize to 'browser'.
const browser = globalThis.browser || globalThis.chrome;
const IS_SAFARI = typeof globalThis.browser !== 'undefined' && !globalThis.chrome;
const IS_CHROME = typeof globalThis.chrome !== 'undefined';
const BROWSER_NAME = IS_SAFARI ? 'safari' : (navigator.userAgent.includes('Arc') ? 'arc' : 'chrome');

// ---------- CONFIG ----------
const ENDPOINT = "http://127.0.0.1:5000/event";
const SEARCH_PATTERNS = [
  "*://*.google.*/*q=*",
  "*://duckduckgo.com/*q=*",
  "*://*.bing.com/search*",
  "*://search.brave.com/search*",
  "*://www.ecosia.org/search*",
  "*://search.yahoo.com/search*"
];

// ---------- Logging ----------
const LOG_LEVEL = { ERROR: 0, WARN: 1, INFO: 2, DEBUG: 3 };
let currentLogLevel = LOG_LEVEL.INFO;

const log = {
  error: (...args) => currentLogLevel >= LOG_LEVEL.ERROR && console.error("[WebAtlas]", ...args),
  warn:  (...args) => currentLogLevel >= LOG_LEVEL.WARN  && console.warn("[WebAtlas]", ...args),
  info:  (...args) => currentLogLevel >= LOG_LEVEL.INFO  && console.log("[WebAtlas]", ...args),
  debug: (...args) => currentLogLevel >= LOG_LEVEL.DEBUG && console.log("[WebAtlas:DEBUG]", ...args)
};

// ---------- Utils ----------
function isInteresting(url) {
  return url &&
         !url.startsWith("chrome://") &&
         !url.startsWith("arc://") &&
         !url.startsWith("chrome-extension://") &&
         !url.startsWith("safari-web-extension://") &&
         !url.startsWith("about:") &&
         !url.startsWith("data:");
}

function extractDomain(url) {
  try {
    return new URL(url).hostname;
  } catch { return null; }
}

function extractSearchQuery(url) {
  try {
    const u = new URL(url);
    return u.searchParams.get("q") || u.searchParams.get("query") || u.searchParams.get("text") || null;
  } catch { return null; }
}

async function postEvent(ev) {
  const payload = { ...ev, t: Date.now(), browser: BROWSER_NAME };
  log.debug("Event:", ev.type, ev);
  try {
    await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    log.warn("postEvent failed:", e.message);
  }
}

// ---------- Dwell Tracking ----------
const timers = {};  // tabId → { url, start }
let currentTabId = null;
let currentWindowId = null;

function flushDwell(tabId) {
  const rec = timers[tabId];
  if (!rec) return;
  const ms = Date.now() - rec.start;
  if (ms > 500) {  // Only log if > 500ms to filter noise
    postEvent({ type: "dwell", url: rec.url, ms });
  }
  delete timers[tabId];
}

function startDwell(tabId, url) {
  if (isInteresting(url)) {
    timers[tabId] = { url, start: Date.now() };
  }
}

// ---------- 1. Tab Activation (Switching) ----------
browser.tabs.onActivated.addListener(async ({ tabId, windowId }) => {
  // Flush previous tab's dwell time
  if (currentTabId !== null) {
    flushDwell(currentTabId);
  }

  currentTabId = tabId;
  currentWindowId = windowId;

  try {
    const tab = await browser.tabs.get(tabId);
    
    if (!isInteresting(tab.url)) {
      // Arc command bar or internal page - log as arcCommand
      if (tab.url?.startsWith("arc://")) {
        postEvent({ 
          type: "arcCommand", 
          action: "commandBar",
          title: tab.title || "(untitled)"
        });
      }
      log.debug("Skipping non-interesting URL:", tab.url);
      return;
    }

    postEvent({ 
      type: "tabSwitch", 
      url: tab.url,
      title: tab.title || null,
      domain: extractDomain(tab.url)
    });
    startDwell(tabId, tab.url);
  } catch (e) {
    log.warn("Failed to get tab info:", e.message);
  }
});

// ---------- 2. Tab Created ----------
browser.tabs.onCreated.addListener((tab) => {
  if (isInteresting(tab.url || tab.pendingUrl)) {
    postEvent({
      type: "tabCreated",
      url: tab.url || tab.pendingUrl || null,
      openerTabId: tab.openerTabId || null
    });
  }
});

// ---------- 3. Tab Closed ----------
browser.tabs.onRemoved.addListener((tabId) => {
  flushDwell(tabId);
  postEvent({ type: "tabClosed", tabId });
});

// ---------- 4. Page Navigation Completed ----------
browser.webNavigation.onCompleted.addListener((details) => {
  if (details.frameId !== 0) return;  // Only main frame
  if (!isInteresting(details.url)) return;
  
  // Reset dwell timer on navigation
  flushDwell(details.tabId);
  startDwell(details.tabId, details.url);

  postEvent({
    type: "navigation",
    url: details.url,
    domain: extractDomain(details.url),
    transitionType: null  // Set by onCommitted
  });
});

// ---------- 5. Navigation Type Detection ----------
browser.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId !== 0) return;
  if (!isInteresting(details.url)) return;

  const transitionType = details.transitionType;
  const query = extractSearchQuery(details.url);

  // Map Chrome transition types to semantic event types
  if (transitionType === "typed" || transitionType === "generated") {
    postEvent({
      type: "urlTyped",
      url: details.url,
      domain: extractDomain(details.url)
    });
  } else if (transitionType === "reload") {
    postEvent({
      type: "pageReload",
      url: details.url
    });
  } else if (details.transitionQualifiers?.includes("forward_back")) {
    postEvent({
      type: "historyNavigation",
      url: details.url,
      direction: "back_forward"
    });
  }

  // Detect search from URL bar (Arc command bar → search engine)
  if ((transitionType === "typed" || transitionType === "generated") && query) {
    postEvent({
      type: "omniboxSearch",
      query: query,
      url: details.url,
      engine: extractDomain(details.url)
    });
  }
});

// ---------- 6. Page URL Updated (SPA navigation, etc.) ----------
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && isInteresting(tab.url)) {
    // Update dwell tracking for current URL
    if (tabId === currentTabId && timers[tabId]?.url !== tab.url) {
      flushDwell(tabId);
      startDwell(tabId, tab.url);
    }
  }
});

// ---------- 7. Window Focus (Space/Window Switching) ----------
browser.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === browser.windows.WINDOW_ID_NONE) {
    // Browser lost focus
    if (currentTabId !== null) {
      flushDwell(currentTabId);
    }
    postEvent({ type: "windowFocus", focused: false });
    return;
  }

  postEvent({ type: "windowFocus", focused: true, windowId });
  currentWindowId = windowId;

  // Resume dwell on current tab when window regains focus
  try {
    const [tab] = await browser.tabs.query({ active: true, windowId });
    if (tab && isInteresting(tab.url)) {
      startDwell(tab.id, tab.url);
    }
  } catch (e) {
    log.warn("Failed to query active tab:", e.message);
  }
});

// ---------- 8. Outgoing Search Requests (Chrome/Arc only) ----------
// Safari doesn't support webRequest in the same way
if (browser.webRequest?.onBeforeRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    (details) => {
      try {
        const url = new URL(details.url);
        const q = url.searchParams.get("q") || 
                  url.searchParams.get("query") ||
                  url.searchParams.get("text") ||
                  url.searchParams.get("p");  // Yahoo
        if (!q) return;
        
        postEvent({
          type: "searchRequest",
          engine: url.hostname,
          query: q,
          url: details.url
        });
      } catch (e) {
        log.debug("Malformed URL in search request:", e.message);
      }
    },
    { urls: SEARCH_PATTERNS, types: ["main_frame"] }
  );
}

// ---------- 9. Omnibox API (Chrome/Arc only, not Safari) ----------
if (browser.omnibox?.onInputEntered) {
  browser.omnibox.onInputEntered.addListener((text, disposition) => {
    postEvent({
      type: "omniboxInput",
      query: text,
      disposition  // "currentTab", "newForegroundTab", "newBackgroundTab"
    });
  });

  browser.omnibox.onInputStarted.addListener(() => {
    log.debug("Omnibox input started");
  });
}

// ---------- 10. Content Script Messages ----------
browser.runtime.onMessage.addListener((msg, sender) => {
  // Enrich with sender tab info
  if (sender.tab && isInteresting(sender.tab.url)) {
    msg.url = sender.tab.url;
    msg.domain = extractDomain(sender.tab.url);
  }
  postEvent(msg);
});

// ---------- Startup ----------
log.info("Web Atlas service-worker ready");
