const CONTROL_ORIGIN = "https://mahi-ig-control.onrender.com";

chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
  if (!sender?.url?.startsWith(CONTROL_ORIGIN)) {
    sendResponse({ok:false,error:"Untrusted control origin."});
    return;
  }

  (async () => {
    try {
      const tabs = await chrome.tabs.query({url:"https://www.instagram.com/*"});
      if (!tabs.length) throw new Error("Open Instagram in Chrome and sign in first.");
      const tab = tabs.find(t => t.active) || tabs[0];
      const result = await chrome.tabs.sendMessage(tab.id, message);
      sendResponse(result || {ok:false,error:"No response from Instagram tab."});
    } catch (error) {
      sendResponse({ok:false,error:error.message || "Could not contact Instagram tab."});
    }
  })();

  return true;
});
