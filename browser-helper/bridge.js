(() => {
  if (window.__MAHI_WEB_BRIDGE__) return;
  window.__MAHI_WEB_BRIDGE__ = true;

  function reply(requestId, ok, data, error) {
    window.postMessage({
      source: 'mahi-extension',
      requestId,
      ok: !!ok,
      data: data || {},
      error: error || ''
    }, location.origin);
  }

  window.addEventListener('message', event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (!message || message.source !== 'mahi-web' || !message.requestId) return;

    chrome.runtime.sendMessage({
      source: 'mahi-web',
      requestId: message.requestId,
      type: message.type,
      payload: message.payload || {}
    }, response => {
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reply(message.requestId, false, {}, lastError.message);
        return;
      }
      if (!response) {
        reply(message.requestId, false, {}, 'No response from Mahi browser helper.');
        return;
      }
      reply(message.requestId, response.ok, response.data, response.error);
    });
  });

  window.postMessage({
    source: 'mahi-extension',
    type: 'HELPER_READY',
    ok: true,
    data: { version: '1.3.1' }
  }, location.origin);
})();