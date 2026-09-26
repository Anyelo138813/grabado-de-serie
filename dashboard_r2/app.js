const DEFAULT_DATA_URL = "sample-data/events.json";

let allEvents = [];

const elements = {
  dataSource: document.getElementById("dataSource"),
  loadStatus: document.getElementById("loadStatus"),
  lineFilter: document.getElementById("lineFilter"),
  eventFilter: document.getElementById("eventFilter"),
  dateFilter: document.getElementById("dateFilter"),
  searchInput: document.getElementById("searchInput"),
  reloadButton: document.getElementById("reloadButton"),
  okCount: document.getElementById("okCount"),
  rejectCount: document.getElementById("rejectCount"),
  sendFailCount: document.getElementById("sendFailCount"),
  lastEvent: document.getElementById("lastEvent"),
  lineCount: document.getElementById("lineCount"),
  lineList: document.getElementById("lineList"),
  eventCount: document.getElementById("eventCount"),
  eventsTable: document.getElementById("eventsTable"),
};

const fallbackEvents = [
  {
    event_time: new Date().toISOString(),
    line_id: "LINEA_1",
    event_type: "sent",
    code_type: "SN",
    code: "55N2617FNH00336",
    message: "Codigo enviado a HSmartTest",
    ip: "192.168.1.10",
    port: "6000",
  },
  {
    event_time: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    line_id: "LINEA_1",
    event_type: "app",
    code_type: "SN",
    code: "",
    message: "Codigo rechazado: GVMP",
    ip: "192.168.1.10",
    port: "6000",
  },
  {
    event_time: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    line_id: "LINEA_2",
    event_type: "connection",
    code_type: "SN",
    code: "",
    message: "Conexion activa: remoto=192.168.1.11:6001 tipo=SN",
    ip: "192.168.1.11",
    port: "6001",
  },
];

function getDataUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("data") || DEFAULT_DATA_URL;
}

async function loadEvents() {
  const dataUrl = getDataUrl();
  setStatus("loading", "Cargando");
  elements.dataSource.textContent = dataUrl;

  try {
    const response = await fetch(dataUrl, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    allEvents = Array.isArray(data) ? data : data.events || [];
    setStatus("ok", "En linea");
  } catch (error) {
    allEvents = fallbackEvents;
    elements.dataSource.textContent = "Datos de ejemplo. Configura ?data=URL_DE_R2/events.json";
    setStatus("error", "Demo");
  }

  setupFilters();
  render();
}

function setStatus(state, label) {
  elements.loadStatus.className = `status-pill ${state === "ok" ? "ok" : state === "error" ? "error" : ""}`;
  elements.loadStatus.querySelector("span:last-child").textContent = label;
}

function setupFilters() {
  const currentLine = elements.lineFilter.value || "all";
  const currentEvent = elements.eventFilter.value || "all";
  const lines = unique(allEvents.map((event) => event.line_id).filter(Boolean)).sort();
  const eventTypes = unique(allEvents.map((event) => event.event_type).filter(Boolean)).sort();

  fillSelect(elements.lineFilter, [["all", "Todas"], ...lines.map((line) => [line, line])], currentLine);
  fillSelect(elements.eventFilter, [["all", "Todos"], ...eventTypes.map((type) => [type, type])], currentEvent);
}

function fillSelect(select, options, currentValue) {
  select.innerHTML = "";
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }
  select.value = options.some(([value]) => value === currentValue) ? currentValue : "all";
}

function render() {
  const filtered = getFilteredEvents();
  renderMetrics(filtered);
  renderLines(filtered);
  renderTable(filtered);
}

function getFilteredEvents() {
  const line = elements.lineFilter.value;
  const eventType = elements.eventFilter.value;
  const date = elements.dateFilter.value;
  const search = normalize(elements.searchInput.value);

  return allEvents
    .filter((event) => line === "all" || event.line_id === line)
    .filter((event) => eventType === "all" || event.event_type === eventType)
    .filter((event) => !date || String(event.event_time || "").startsWith(date))
    .filter((event) => {
      if (!search) return true;
      return normalize(`${event.code || ""} ${event.message || ""} ${event.line_id || ""}`).includes(search);
    })
    .sort((a, b) => new Date(b.event_time || 0) - new Date(a.event_time || 0));
}

function renderMetrics(events) {
  elements.okCount.textContent = events.filter(isOkEvent).length;
  elements.rejectCount.textContent = events.filter(isRejectedEvent).length;
  elements.sendFailCount.textContent = events.filter(isSendFailEvent).length;
  elements.lastEvent.textContent = events.length ? formatTime(events[0].event_time) : "--:--";
}

function renderLines(events) {
  const grouped = new Map();
  for (const event of events) {
    const key = event.line_id || "SIN_LINEA";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(event);
  }

  elements.lineCount.textContent = grouped.size;
  elements.lineList.innerHTML = "";

  if (!grouped.size) {
    elements.lineList.innerHTML = '<div class="empty">Sin lineas para mostrar.</div>';
    return;
  }

  for (const [line, lineEvents] of [...grouped.entries()].sort()) {
    const latest = lineEvents.sort((a, b) => new Date(b.event_time || 0) - new Date(a.event_time || 0))[0];
    const badgeClass = isSendFailEvent(latest) ? "error" : isRejectedEvent(latest) ? "warn" : "ok";
    const row = document.createElement("div");
    row.className = "line-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(line)}</strong>
        <span>${escapeHtml(latest.message || "")}</span>
      </div>
      <span class="badge ${badgeClass}">${escapeHtml(latest.event_type || "evt")}</span>
    `;
    elements.lineList.appendChild(row);
  }
}

function renderTable(events) {
  const visibleEvents = events.slice(0, 300);
  elements.eventCount.textContent = events.length;
  elements.eventsTable.innerHTML = "";

  if (!visibleEvents.length) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="5" class="empty">Sin eventos para mostrar.</td>';
    elements.eventsTable.appendChild(row);
    return;
  }

  for (const event of visibleEvents) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(formatDateTime(event.event_time))}</td>
      <td>${escapeHtml(event.line_id || "")}</td>
      <td><span class="badge ${badgeClassFor(event)}">${escapeHtml(event.event_type || "")}</span></td>
      <td class="code">${escapeHtml(event.code || "")}</td>
      <td class="message">${escapeHtml(event.message || "")}</td>
    `;
    elements.eventsTable.appendChild(row);
  }
}

function badgeClassFor(event) {
  if (isSendFailEvent(event)) return "error";
  if (isRejectedEvent(event)) return "warn";
  if (isOkEvent(event)) return "ok";
  return "";
}

function isOkEvent(event) {
  return event.event_type === "sent" || normalize(event.message).includes("codigo ok");
}

function isRejectedEvent(event) {
  return normalize(event.message).includes("rechazado");
}

function isSendFailEvent(event) {
  const text = normalize(event.message);
  return text.includes("fallo envio") || text.includes("no se envio") || text.includes("timeout");
}

function unique(values) {
  return [...new Set(values)];
}

function normalize(value) {
  return String(value || "").toLowerCase();
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("es-MX", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

for (const element of [elements.lineFilter, elements.eventFilter, elements.dateFilter, elements.searchInput]) {
  element.addEventListener("input", render);
}

elements.reloadButton.addEventListener("click", loadEvents);

loadEvents();
