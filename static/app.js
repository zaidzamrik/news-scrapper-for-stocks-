const form = document.getElementById("analyzeForm");
const input = document.getElementById("tickerInput");
const button = document.getElementById("analyzeButton");
const status = document.getElementById("status");
const resultCard = document.getElementById("resultCard");
const lookupResults = document.getElementById("lookupResults");

const resultTicker = document.getElementById("resultTicker");
const resultDate = document.getElementById("resultDate");
const resultSignal = document.getElementById("resultSignal");
const resultWhy = document.getElementById("resultWhy");
const resultRisks = document.getElementById("resultRisks");
const planBuy = document.getElementById("planBuy");
const planHold = document.getElementById("planHold");
const planExit = document.getElementById("planExit");
const resultDisclaimer = document.getElementById("resultDisclaimer");
let lookupTimeoutId = null;

function setStatus(message, isError = false) {
  status.textContent = message || "";
  status.style.color = isError ? "#b91c1c" : "#5f6b7a";
}

function resetResult() {
  resultCard.classList.add("hidden");
  resultWhy.innerHTML = "";
  resultRisks.innerHTML = "";
}

function renderList(element, items) {
  element.innerHTML = "";
  (items || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function hideLookupResults() {
  lookupResults.innerHTML = "";
  lookupResults.classList.add("hidden");
}

function renderLookupResults(items) {
  lookupResults.innerHTML = "";
  if (!items || items.length === 0) {
    hideLookupResults();
    return;
  }

  items.forEach((item) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "lookup-item";
    option.setAttribute("role", "option");
    option.innerHTML = `
      <span class="lookup-ticker">${item.ticker}</span>
      <span class="lookup-name">${item.company_name}</span>
    `;
    option.addEventListener("click", () => {
      input.value = item.company_name;
      hideLookupResults();
      input.focus();
    });
    lookupResults.appendChild(option);
  });

  lookupResults.classList.remove("hidden");
}

async function fetchLookupResults(query) {
  try {
    const response = await fetch(`/lookup?query=${encodeURIComponent(query)}`);
    if (!response.ok) {
      hideLookupResults();
      return;
    }
    const data = await response.json();
    renderLookupResults(data.results || []);
  } catch (_error) {
    hideLookupResults();
  }
}

function updateSignalBadge(signal) {
  resultSignal.textContent = signal;
  resultSignal.classList.remove("signal-buy", "signal-hold", "signal-exit", "signal-dont-buy");
  if (signal === "BUY") {
    resultSignal.classList.add("signal-buy");
  } else if (signal === "HOLD") {
    resultSignal.classList.add("signal-hold");
  } else if (signal === "EXIT") {
    resultSignal.classList.add("signal-exit");
  } else {
    resultSignal.classList.add("signal-dont-buy");
  }
}

input.addEventListener("input", () => {
  const query = input.value.trim();
  if (lookupTimeoutId) {
    window.clearTimeout(lookupTimeoutId);
  }
  if (query.length < 2) {
    hideLookupResults();
    return;
  }
  lookupTimeoutId = window.setTimeout(() => {
    fetchLookupResults(query);
  }, 180);
});

input.addEventListener("blur", () => {
  window.setTimeout(hideLookupResults, 120);
});

input.addEventListener("focus", () => {
  const query = input.value.trim();
  if (query.length >= 2) {
    fetchLookupResults(query);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const rawInput = input.value.trim();

  if (!rawInput) {
    setStatus("Please enter a stock ticker.", true);
    resetResult();
    return;
  }

  const cleaned = rawInput.replace(/\s+/g, " ").trim();
  const tickerParam = cleaned;
  const companyParam = cleaned;

  setStatus("Analyzing stock...");
  resetResult();
  hideLookupResults();
  button.disabled = true;

  try {
    const url = `/analyze?ticker=${encodeURIComponent(tickerParam)}&company_name=${encodeURIComponent(
      companyParam
    )}&simple=true`;
    const response = await fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || "Unable to analyze this stock right now.";
      throw new Error(message);
    }

    const data = await response.json();
    const payload = data?.signal ? data : data?.simple;

    if (!payload || !payload.signal) {
      throw new Error("No result returned. Please try again.");
    }

    resultTicker.textContent = payload.ticker || tickerParam;
    resultDate.textContent = payload.date || "";
    updateSignalBadge(payload.signal || "DON'T BUY");

    renderList(resultWhy, payload.why || []);
    planBuy.textContent = payload.plan?.buy || "";
    planHold.textContent = payload.plan?.hold || "";
    planExit.textContent = payload.plan?.exit || "";
    renderList(resultRisks, payload.risks || []);
    resultDisclaimer.textContent = payload.disclaimer || "";

    resultCard.classList.remove("hidden");
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});
