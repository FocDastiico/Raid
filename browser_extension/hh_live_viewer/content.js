(function () {
  const CAPTURE_DEBOUNCE_MS = 1800;
  let captureTimer = null;
  let lastSignature = "";

  function textOf(element) {
    return element ? element.textContent.replace(/\s+/g, " ").trim() : "";
  }

  function valueOfSelector(selector) {
    const node = document.querySelector(selector);
    if (!node) {
      return "";
    }

    if ("value" in node && node.value) {
      return String(node.value).trim();
    }

    return textOf(node);
  }

  function collectSlots() {
    const slotLabels = ["leader", "champion2", "champion3", "champion4", "champion5"];
    const slotNodes = Array.from(document.querySelectorAll("[class*='champion'], [class*='leader'], [class*='slot']"));
    return slotLabels.map((slotName, index) => {
      const node = slotNodes[index];
      return {
        slot: slotName,
        text: textOf(node)
      };
    });
  }

  function collectVisibleButtons() {
    return Array.from(document.querySelectorAll("button"))
      .map((button) => textOf(button))
      .filter(Boolean)
      .slice(0, 30);
  }

  function collectVisibleHeadings() {
    return Array.from(document.querySelectorAll("h1, h2, h3, h4"))
      .map((heading) => textOf(heading))
      .filter(Boolean)
      .slice(0, 20);
  }

  function collectTextPreview() {
    const root = document.querySelector("main") || document.body;
    return textOf(root).slice(0, 5000);
  }

  function pickFirstText(selectors) {
    for (const selector of selectors) {
      const node = document.querySelector(selector);
      const text = textOf(node);
      if (text) {
        return text;
      }
    }

    return "";
  }

  function buildPayload() {
    return {
      url: location.href,
      title: document.title,
      pageSummary: {
        dungeon: valueOfSelector("mat-select[formcontrolname='dungeon'], [aria-label*='Dungeon'], [placeholder='Dungeon']"),
        stage: valueOfSelector("mat-select[formcontrolname='stage'], [aria-label*='Stage'], [placeholder='Stage']"),
        leaderSkill: pickFirstText([
          "*[class*='leader']",
          "*[class*='skill']",
          "*[class*='selected']"
        ]),
        headings: collectVisibleHeadings(),
        buttons: collectVisibleButtons(),
        slots: collectSlots()
      },
      textPreview: collectTextPreview(),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    };
  }

  function buildSignature(payload) {
    return JSON.stringify({
      url: payload.url,
      title: payload.title,
      pageSummary: payload.pageSummary,
      textPreview: payload.textPreview.slice(0, 1000)
    });
  }

  function sendCapture(reason) {
    const payload = buildPayload();
    const signature = buildSignature(payload);
    if (reason !== "manual" && signature === lastSignature) {
      return;
    }

    lastSignature = signature;
    chrome.runtime.sendMessage({
      type: "capture-page",
      reason,
      payload
    });
  }

  function scheduleCapture(reason) {
    window.clearTimeout(captureTimer);
    captureTimer = window.setTimeout(() => sendCapture(reason), CAPTURE_DEBOUNCE_MS);
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "manual-capture") {
      sendCapture("manual");
      sendResponse({ ok: true });
    }
  });

  const observer = new MutationObserver(() => scheduleCapture("mutation"));
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: false
  });

  window.addEventListener("load", () => scheduleCapture("load"));
  window.addEventListener("click", () => scheduleCapture("click"), true);
  window.addEventListener("change", () => scheduleCapture("change"), true);
  window.addEventListener("popstate", () => scheduleCapture("navigation"));

  scheduleCapture("init");
})();
