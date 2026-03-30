const SERVER_URL = "http://127.0.0.1:8765/snapshot";

async function postSnapshot(payload) {
  const response = await fetch(SERVER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Servidor respondeu com ${response.status}`);
  }

  return response.json();
}

function captureVisibleTab(windowId) {
  return chrome.tabs.captureVisibleTab(windowId, {
    format: "png"
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    autoCapture: true,
    lastStatus: "Extensao instalada"
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "capture-page") {
    (async () => {
      try {
        const autoState = await chrome.storage.local.get(["autoCapture"]);
        if (message.reason !== "manual" && autoState.autoCapture === false) {
          sendResponse({ ok: false, skipped: true, reason: "auto-disabled" });
          return;
        }

        const tab = sender.tab;
        if (!tab?.windowId || !tab?.id) {
          throw new Error("A aba ativa nao foi identificada");
        }

        const screenshot = await captureVisibleTab(tab.windowId);
        const payload = {
          ...message.payload,
          eventReason: message.reason || "unknown",
          tabId: tab.id,
          windowId: tab.windowId,
          capturedAt: new Date().toISOString(),
          screenshot
        };

        const result = await postSnapshot(payload);
        const status = `Ultimo envio: ${new Date().toLocaleTimeString()}`;
        await chrome.storage.local.set({
          lastStatus: status,
          lastResult: result
        });

        sendResponse({ ok: true, result });
      } catch (error) {
        const status = `Falha: ${error.message}`;
        await chrome.storage.local.set({
          lastStatus: status
        });
        sendResponse({ ok: false, error: error.message });
      }
    })();

    return true;
  }

  if (message?.type === "get-status") {
    chrome.storage.local.get(["autoCapture", "lastStatus", "lastResult"]).then((state) => {
      sendResponse({ ok: true, state });
    });
    return true;
  }

  if (message?.type === "set-auto-capture") {
    chrome.storage.local.set({
      autoCapture: Boolean(message.enabled),
      lastStatus: message.enabled ? "Captura automatica ligada" : "Captura automatica desligada"
    }).then(() => {
      sendResponse({ ok: true });
    });
    return true;
  }
});
