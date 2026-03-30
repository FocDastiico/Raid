async function queryActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function refreshStatus() {
  const response = await chrome.runtime.sendMessage({ type: "get-status" });
  if (!response?.ok) {
    return;
  }

  document.getElementById("autoCapture").checked = Boolean(response.state.autoCapture);
  document.getElementById("status").textContent = response.state.lastStatus || "Sem status ainda";
}

document.getElementById("autoCapture").addEventListener("change", async (event) => {
  await chrome.runtime.sendMessage({
    type: "set-auto-capture",
    enabled: event.target.checked
  });
  refreshStatus();
});

document.getElementById("captureNow").addEventListener("click", async () => {
  const tab = await queryActiveTab();
  if (!tab?.id) {
    document.getElementById("status").textContent = "Nao encontrei a aba ativa";
    return;
  }

  await chrome.tabs.sendMessage(tab.id, { type: "manual-capture" });
  document.getElementById("status").textContent = "Envio manual solicitado";
  window.setTimeout(refreshStatus, 800);
});

refreshStatus();
