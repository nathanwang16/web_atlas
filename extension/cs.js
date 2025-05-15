// cs.js — injected into every page

function send(evtType, extra) {
  chrome.runtime.sendMessage({type: evtType, url: location.href, ...extra});
}

/* keystrokes in editable elements */
document.addEventListener("input", e => {
  if (e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target.isContentEditable) {
    send("input", {len: (e.data || "").length});
  }
});

/* copy / cut / paste size */
["copy","cut","paste"].forEach(evt =>
  document.addEventListener(evt, e => {
    const size = e.clipboardData?.getData("text/plain")?.length || 0;
    send(evt, {len: size});
  }, true)
);