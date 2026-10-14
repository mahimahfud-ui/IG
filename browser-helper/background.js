const CONTROL_ORIGIN = "https://mahi-ig-control.onrender.com";
const DASHBOARD_ORIGIN = "https://mahicloud.onrender.com";
const DASHBOARD_PATH = "/instagram-cleaner.html";
const DASHBOARD_ACTIONS = new Set([
  "GET_SESSION",
  "SCAN_NON_FOLLOWERS",
  "UNFOLLOW_SELECTED",
  "SCAN_LIKES",
  "UNLIKE_SELECTED",
  "OPEN_COMMENTS",
  "SCAN_VISIBLE_COMMENTS",
  "DELETE_COMMENTS_SELECTED"
]);

async function forwardToInstagram(message) {
  const tabs = await chrome.tabs.query({ url: "https://www.instagram.com/*" });
  if (!tabs.length) {
    throw new Error("Open Instagram in Chrome and sign in first.");
  }

  const tab = tabs.find(t => t.active) || tabs[0];
  if (tab.id == null) throw new Error("Instagram tab could not be identified.");

  const result = await chrome.tabs.sendMessage(tab.id, message);
  return result || { ok: false, error: "No response from Instagram tab." };
}

// Relay only supported requests from the MahiCloud dashboard page.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "MAHI_WEB_REQUEST") return;

  let sourceUrl;
  try {
    sourceUrl = new URL(sender?.url || sender?.tab?.url || "");
  } catch (_) {
    sendResponse({ ok: false, error: "Untrusted dashboard origin." });
    return;
  }

  if (sourceUrl.origin !== DASHBOARD_ORIGIN || sourceUrl.pathname !== DASHBOARD_PATH) {
    sendResponse({ ok: false, error: "Untrusted dashboard origin." });
    return;
  }

  const action = String(message.action || "");
  if (!DASHBOARD_ACTIONS.has(action)) {
    sendResponse({ ok: false, error: "Unsupported dashboard action." });
    return;
  }

  const payload = message.payload && typeof message.payload === "object" && !Array.isArray(message.payload)
    ? message.payload
    : {};
  const forwardedMessage = { ...payload, type: action };

  forwardToInstagram(forwardedMessage)
    .then(sendResponse)
    .catch(error => sendResponse({
      ok: false,
      error: error?.message || "Could not contact the Instagram tab."
    }));

  return true;
});

// Preserve the existing legacy control-site integration while validating its
// exact origin instead of accepting lookalike domains with the same prefix.
chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
  let senderOrigin = "";
  try {
    senderOrigin = new URL(sender?.url || "").origin;
  } catch (_) {}

  if (senderOrigin !== CONTROL_ORIGIN) {
    sendResponse({ ok: false, error: "Untrusted control origin." });
    return;
  }

  forwardToInstagram(message)
    .then(sendResponse)
    .catch(error => sendResponse({
      ok: false,
      error: error?.message || "Could not contact the Instagram tab."
    }));

  return true;
});
