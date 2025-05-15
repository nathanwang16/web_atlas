/*********************************************************************
 * bg.js  — Self-Analytics (Arc / Chrome)   2025-05-15
 * - captures tab switches & dwell
 * - logs Arc omnibox searches        (internalSearch)
 * - logs outgoing search requests    (searchRequest)
 *********************************************************************/

// ---------- CONFIG ----------
const ENDPOINT = "http://127.0.0.1:5000/event";   // FastAPI
const SEARCH_PATTERNS = [
  "*://*.google.*/*q=*",
  "*://duckduckgo.com/*q=*",
  "*://*.bing.com/search*",
  "*://search.brave.com/search*"
];

// ---------- tiny utils ----------
function isInteresting(url) {
  return url &&
         !url.startsWith("chrome://") &&
         !url.startsWith("arc://") &&
         !url.startsWith("chrome-extension://");
}

async function postEvent(ev) {
  try {
    await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...ev, t: Date.now() })
    });
  } catch (e) {
    console.warn("postEvent failed:", e.message);
  }
}

// ---------- dwell timers ----------
const timers = {};          // tabId → {url, start}
function flush(tabId) {
  const rec = timers[tabId];
  if (!rec) return;
  postEvent({ type: "dwell", url: rec.url, ms: Date.now() - rec.start });
  delete timers[tabId];
}

// ---------- 1. Tab activated ----------
let currentTabId = null;
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  if (currentTabId !== null) flush(currentTabId);

  const tab = await chrome.tabs.get(tabId);
  currentTabId = tabId;

  if (!isInteresting(tab.url)) {
    // Arc command bar / NTP → use title as query
    postEvent({ type: "internalSearch", query: tab.title || "(blank)" });
    return;
  }
  timers[tabId] = { url: tab.url, start: Date.now() };
  postEvent({ type: "tabSwitch", url: tab.url });
});

// ---------- 2. Page finished loading ----------
chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.status === "complete" && isInteresting(tab.url)) {
    flush(tabId);
    timers[tabId] = { url: tab.url, start: Date.now() };
  }
});
chrome.tabs.onRemoved.addListener(flush);

// ---------- 3. Content-script messages ----------
chrome.runtime.onMessage.addListener((msg) => postEvent(msg));

// ---------- 4. Outgoing SEARCH requests ----------
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    try {
      const url = new URL(details.url);
      const q = url.searchParams.get("q") || url.searchParams.get("text");
      if (!q) return;
      postEvent({
        type:   "searchRequest",
        engine: url.hostname,
        query:  q,
        url:    details.url
      });
    } catch (_) {
      /* ignore malformed URLs (chrome://, about:blank, etc.) */
    }
  },
  { urls: SEARCH_PATTERNS, types: ["main_frame"] }
);

console.log("Self-Analytics service-worker ready");