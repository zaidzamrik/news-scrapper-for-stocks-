const form = document.getElementById("analyzeForm");
const input = document.getElementById("tickerInput");
const button = document.getElementById("analyzeButton");
const status = document.getElementById("status");
const resultCard = document.getElementById("resultCard");

const resultTicker = document.getElementById("resultTicker");
const resultDate = document.getElementById("resultDate");
const resultSignal = document.getElementById("resultSignal");
const resultWhy = document.getElementById("resultWhy");
const resultRisks = document.getElementById("resultRisks");
const planBuy = document.getElementById("planBuy");
const planHold = document.getElementById("planHold");
const planExit = document.getElementById("planExit");
const resultDisclaimer = document.getElementById("resultDisclaimer");

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

function updateSignalBadge(signal) {
  resultSignal.textContent = signal;
  resultSignal.classList.remove("signal-buy", "signal-hold", "signal-avoid");
  if (signal === "BUY") {
    resultSignal.classList.add("signal-buy");
  } else if (signal === "HOLD") {
    resultSignal.classList.add("signal-hold");
  } else {
    resultSignal.classList.add("signal-avoid");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const rawInput = input.value.trim();

  if (!rawInput) {
    setStatus("Please enter a stock ticker.", true);
    resetResult();
    return;
  }

  const cleaned = rawInput.replace(/\s+/g, " ");
  const tickerParam = cleaned.replace(/\s+/g, "").toUpperCase();
  const companyParam = cleaned;

  setStatus("Analyzing stock...");
  resetResult();
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
    if (!data || !data.simple) {
      throw new Error("No result returned. Please try again.");
    }

    const simple = data.simple;

    resultTicker.textContent = simple.ticker || tickerParam;
    resultDate.textContent = simple.date || "";
    updateSignalBadge(simple.signal || data.signal || "HOLD");

    renderList(resultWhy, simple.why || []);
    planBuy.textContent = simple.plan?.buy || "";
    planHold.textContent = simple.plan?.hold || "";
    planExit.textContent = simple.plan?.exit || "";
    renderList(resultRisks, simple.risks || []);
    resultDisclaimer.textContent = simple.disclaimer || "";

    resultCard.classList.remove("hidden");
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});
