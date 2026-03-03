/*********************************************************************
 * cs.js — Web Atlas Content Script (Chrome / Arc / Safari)
 * Injected into every page to capture user interactions.
 * 
 * Events:
 *   - input:   Text input in editable fields (throttled)
 *   - copy:    Clipboard copy action
 *   - cut:     Clipboard cut action
 *   - paste:   Clipboard paste action
 *   - scroll:  Significant page scroll (throttled)
 *   - click:   Link clicks (for navigation tracking)
 *********************************************************************/

// ---------- Browser API Compatibility ----------
const browser = globalThis.browser || globalThis.chrome;

// ---------- Throttle Utility ----------
function throttle(fn, delay) {
  let lastCall = 0;
  let pending = null;
  return function(...args) {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      fn.apply(this, args);
    } else if (!pending) {
      pending = setTimeout(() => {
        lastCall = Date.now();
        pending = null;
        fn.apply(this, args);
      }, delay - (now - lastCall));
    }
  };
}

// ---------- Send Event to Background ----------
function send(evtType, extra = {}) {
  browser.runtime.sendMessage({ 
    type: evtType, 
    url: location.href,
    ...extra 
  });
}

// ---------- Input Events (Throttled) ----------
let inputBuffer = { len: 0, count: 0 };
const flushInput = throttle(() => {
  if (inputBuffer.count > 0) {
    send("input", { 
      len: inputBuffer.len, 
      eventCount: inputBuffer.count 
    });
    inputBuffer = { len: 0, count: 0 };
  }
}, 2000);  // Flush every 2 seconds max

document.addEventListener("input", (e) => {
  if (e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target.isContentEditable) {
    inputBuffer.len += (e.data || "").length;
    inputBuffer.count++;
    flushInput();
  }
});

// Flush remaining input on page unload
window.addEventListener("beforeunload", () => {
  if (inputBuffer.count > 0) {
    send("input", { 
      len: inputBuffer.len, 
      eventCount: inputBuffer.count 
    });
  }
});

// ---------- Clipboard Events ----------
["copy", "cut", "paste"].forEach((evt) => {
  document.addEventListener(evt, (e) => {
    const text = e.clipboardData?.getData("text/plain") || "";
    send(evt, { len: text.length });
  }, true);
});

// ---------- Scroll Tracking (Throttled) ----------
let maxScrollDepth = 0;
const trackScroll = throttle(() => {
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const docHeight = Math.max(
    document.body.scrollHeight,
    document.documentElement.scrollHeight
  );
  const viewportHeight = window.innerHeight;
  const scrollPercent = Math.round((scrollTop + viewportHeight) / docHeight * 100);
  
  if (scrollPercent > maxScrollDepth) {
    maxScrollDepth = scrollPercent;
  }
}, 1000);

document.addEventListener("scroll", trackScroll, { passive: true });

// Report max scroll depth on page unload
window.addEventListener("beforeunload", () => {
  if (maxScrollDepth > 0) {
    send("scroll", { maxDepthPercent: maxScrollDepth });
  }
});

// ---------- Link Click Tracking ----------
document.addEventListener("click", (e) => {
  const link = e.target.closest("a");
  if (link && link.href && !link.href.startsWith("javascript:")) {
    const isExternal = link.hostname !== location.hostname;
    send("linkClick", {
      targetUrl: link.href,
      isExternal,
      linkText: (link.textContent || "").slice(0, 100).trim()
    });
  }
}, true);
