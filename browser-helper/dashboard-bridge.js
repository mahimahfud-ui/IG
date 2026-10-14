(() => {
  "use strict";

  const PAGE_SOURCE = "mahi-web";
  const EXTENSION_SOURCE = "mahi-extension";
  const ALLOWED_ACTIONS = new Set([
    "GET_SESSION",
    "SCAN_NON_FOLLOWERS",
    "UNFOLLOW_SELECTED",
    "SCAN_LIKES",
    "UNLIKE_SELECTED",
    "OPEN_COMMENTS",
    "SCAN_VISIBLE_COMMENTS",
    "DELETE_COMMENTS_SELECTED"
  ]);

  function respond(requestId, response) {
    window.postMessage({
      source: EXTENSION_SOURCE,
      requestId,
      ok: response?.ok === true,
      data: response?.data,
      error: response?.error
    }, location.origin);
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;

    const request = event.data;
    if (request?.source !== PAGE_SOURCE) return;
    if (typeof request.requestId !== "string" || request.requestId.length > 160) return;

    const action = String(request.type || "");
    if (!ALLOWED_ACTIONS.has(action)) {
      respond(request.requestId, { ok: false, error: "Unsupported browser helper action." });
      return;
    }

    const payload = request.payload && typeof request.payload === "object" && !Array.isArray(request.payload)
      ? request.payload
      : {};

    chrome.runtime.sendMessage({
      type: "MAHI_WEB_REQUEST",
      action,
      payload
    }).then(response => {
      respond(request.requestId, response || { ok: false, error: "No response from Browser Tools." });
    }).catch(error => {
      respond(request.requestId, {
        ok: false,
        error: error?.message || "Browser Tools could not complete the request."
      });
    });
  });
})();
