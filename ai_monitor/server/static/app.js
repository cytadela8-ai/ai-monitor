const state = {
  diagnostics: null,
  heatmapMarkup: "",
  latestRefresh: null,
  loading: false,
  period: "day",
  project: "",
  projectOptionsSignature: "",
  provider: "",
  renderToken: 0,
  tableMarkup: "",
};

const TABLE_COLUMNS = [
  ["Period", "period_start"],
  ["Project", "project_name"],
  ["Tool", "provider"],
  ["Conversations", "conversation_count"],
  ["Text Prompts", "text_prompt_count"],
  ["Slash Cmds", "slash_command_count"],
];

const DEMOTED_PROJECTS = new Set([".codex", "tmp", "unknown"]);
const QUICK_PICK_VARIANT_CLASSES = [
  "project-quick-pick--amber",
  "project-quick-pick--mint",
  "project-quick-pick--coral",
];
const QUICK_PICK_TILT_CLASSES = [
  "project-quick-pick--tilt-left",
  "project-quick-pick--tilt-right",
  "project-quick-pick--tilt-flat",
];
const LOAD_MESSAGES = [
  "Reading your local activity view...",
  "Lining up fresh counts from your logs...",
  "Stacking project totals into the ledger...",
];
const REFRESH_MESSAGES = [
  "Reading your local Codex and Claude logs...",
  "Counting prompts across your recent work...",
  "Rolling the latest project totals into place...",
];
const AUTO_REFRESH_MESSAGES = [
  "Starting the first local read...",
  "Building the first pass from your local logs...",
  "Getting your ledger ready from local history...",
];
const SUCCESS_MESSAGES = [
  "Local logs scanned. Ledger updated.",
  "Fresh read ready.",
  "Everything is up to date again.",
];
const AUTO_SUCCESS_MESSAGES = [
  "First local read complete.",
  "Your first ledger is ready.",
  "The first pass is in. You're good to go.",
];
const FAILURE_MESSAGES = [
  "Could not scan local logs. Check the server log and try again.",
  "That read did not land. Check the server log and try again.",
];
let celebrateTimer = 0;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function pickMessage(messages) {
  return messages[Math.floor(Math.random() * messages.length)];
}

function formatProvider(value) {
  if (value === "claude") {
    return "Claude";
  }
  if (value === "codex") {
    return "Codex";
  }
  return value;
}

function parsePeriodStart(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }

  const [, year, month, day] = match;
  return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
}

function formatPeriodLabel(value) {
  const date = parsePeriodStart(value);
  if (!date) {
    return value;
  }

  if (state.period === "month") {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(date);
  }

  const dayLabel = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);

  if (state.period === "week") {
    return `Week of ${dayLabel}`;
  }

  return dayLabel;
}

function formatDayLabel(value) {
  const date = parsePeriodStart(value);
  if (!date) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function formatTimestamp(value) {
  if (!value) {
    return "Not refreshed yet";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function setStatusNote(message) {
  const statusNote = document.getElementById("status-note");
  if (statusNote) {
    statusNote.textContent = message;
  }
}

function setWorkspaceBusy(isBusy) {
  const workspace = document.getElementById("workspace");
  if (workspace) {
    workspace.setAttribute("aria-busy", String(isBusy));
  }
}

function setScanState(state) {
  document.getElementById("status-rail")?.setAttribute("data-scan-state", state);
}

function celebrateRefresh() {
  const rail = document.getElementById("status-rail");
  if (!rail) {
    return;
  }

  if (celebrateTimer) {
    window.clearTimeout(celebrateTimer);
  }

  rail.classList.remove("is-celebrating");
  void rail.offsetWidth;
  rail.classList.add("is-celebrating");
  celebrateTimer = window.setTimeout(() => {
    rail.classList.remove("is-celebrating");
  }, 800);
}

function defaultStatusNote() {
  if (!state.latestRefresh) {
    return "No local read yet. The page will build one for you.";
  }
  return "Showing the latest local read.";
}

function setBusy(isBusy, label = "Scan Local Logs", busyMessage = "") {
  state.loading = isBusy;
  setWorkspaceBusy(isBusy);
  setScanState(isBusy ? "loading" : "idle");
  const refreshButton = document.getElementById("refresh-button");
  if (refreshButton) {
    refreshButton.disabled = isBusy;
    refreshButton.textContent = isBusy ? label : "Scan Local Logs";
  }

  for (const control of document.querySelectorAll(".segment-button, .filter select")) {
    control.disabled = isBusy;
  }

  for (const control of document.querySelectorAll(".project-quick-pick")) {
    control.disabled = isBusy;
  }

  if (isBusy && busyMessage) {
    setStatusNote(busyMessage);
  }
}

function setHeatmapSummary(message) {
  const summary = document.getElementById("heatmap-summary");
  if (summary) {
    summary.textContent = message;
  }
}

function setHeatmapHoverDetail(message = "Hover a square to inspect that day.") {
  const hoverValue = document.getElementById("heatmap-hover-detail");
  if (hoverValue) {
    hoverValue.textContent = message;
  }
}

function resetDiagnostics() {
  state.diagnostics = null;
  setText("provider-count", "-");
  setText("diagnostic-conversations", "-");
  setText("diagnostic-prompts", "-");
  setText("last-refresh", formatTimestamp(state.latestRefresh));
}

function renderSummary(summary) {
  setText("conversation-total", formatCompactNumber(summary.conversation_count));
  setText("text-prompt-total", formatCompactNumber(summary.text_prompt_count));
  setText("slash-command-total", formatCompactNumber(summary.slash_command_count));
}

function renderTable(rows) {
  const tbody = document.getElementById("metrics-table-body");
  if (!tbody) {
    return;
  }

  if (rows.length === 0) {
    const message = state.latestRefresh
      ? "No activity for this mix of filters."
      : "No saved activity yet. Your first local read is still pending.";
    const markup = `<tr><td class="empty-state" colspan="6">${escapeHtml(message)}</td></tr>`;
    if (markup !== state.tableMarkup) {
      tbody.innerHTML = markup;
      state.tableMarkup = markup;
    }
    return;
  }

  const markup = rows
    .map((row) => {
      const cells = TABLE_COLUMNS.map(([label, field]) => {
        let rawValue = row[field];
        if (field === "provider") {
          rawValue = formatProvider(rawValue);
        }
        if (field === "period_start") {
          rawValue = formatPeriodLabel(rawValue);
        }
        const content = typeof rawValue === "number"
          ? formatCompactNumber(rawValue)
          : escapeHtml(rawValue);
        return `<td data-label="${label}">${content}</td>`;
      }).join("");
      return `
        <tr>
          ${cells}
        </tr>
      `;
    })
    .join("");

  if (markup !== state.tableMarkup) {
    tbody.innerHTML = markup;
    state.tableMarkup = markup;
  }
}

function isoWeekdayIndex(value) {
  const date = parsePeriodStart(value);
  if (!date) {
    return 0;
  }

  const weekday = date.getUTCDay();
  return weekday === 0 ? 6 : weekday - 1;
}

function startOfIsoWeek(value) {
  const date = parsePeriodStart(value);
  if (!date) {
    return value;
  }

  const weekdayIndex = isoWeekdayIndex(value);
  date.setUTCDate(date.getUTCDate() - weekdayIndex);
  return date.toISOString().slice(0, 10);
}

function heatmapLevel(totalEvents, maxEvents) {
  if (totalEvents <= 0 || maxEvents <= 0) {
    return 0;
  }

  const ratio = totalEvents / maxEvents;
  if (ratio >= 0.8) {
    return 4;
  }
  if (ratio >= 0.55) {
    return 3;
  }
  if (ratio >= 0.3) {
    return 2;
  }
  return 1;
}

function heatmapDetail(day) {
  return `${formatDayLabel(day.day)}. ${formatCompactNumber(day.total_events)} total events. ` +
    `${formatCompactNumber(day.conversation_count)} conversations, ` +
    `${formatCompactNumber(day.text_prompt_count)} text prompts, ` +
    `${formatCompactNumber(day.slash_command_count)} slash commands.`;
}

function renderHeatmapLegend(maxEvents) {
  const legendScale = document.getElementById("heatmap-legend-scale");
  if (!legendScale) {
    return;
  }

  legendScale.innerHTML = "";
  for (let level = 0; level <= 4; level += 1) {
    const cell = document.createElement("span");
    cell.className = `heatmap-legend__cell heatmap-cell--level-${level}`;
    cell.setAttribute("aria-hidden", "true");
    legendScale.append(cell);
  }

  legendScale.title = maxEvents > 0
    ? `Scale runs from 0 to ${formatCompactNumber(maxEvents)} total events in a day.`
    : "Scale runs from 0 events upward once activity lands.";
}

function bindHeatmapInteractions() {
  const grid = document.getElementById("heatmap-grid");
  if (!grid) {
    return;
  }

  const cells = grid.querySelectorAll(".heatmap-cell[data-detail]");
  for (const cell of cells) {
    const detail = cell.getAttribute("data-detail");
    if (!detail) {
      continue;
    }

    const showDetail = () => {
      setHeatmapHoverDetail(detail);
    };
    const clearDetail = () => {
      setHeatmapHoverDetail();
    };

    cell.addEventListener("mouseenter", showDetail);
    cell.addEventListener("focus", showDetail);
    cell.addEventListener("mouseleave", clearDetail);
    cell.addEventListener("blur", clearDetail);
  }
}

function renderHeatmap(days) {
  const grid = document.getElementById("heatmap-grid");
  if (!grid) {
    return;
  }

  if (days.length === 0) {
    grid.innerHTML = "";
    state.heatmapMarkup = "";
    renderHeatmapLegend(0);
    const message = state.latestRefresh
      ? "No day-level activity for this slice yet."
      : "The daily grid will fill in after the first local read finishes.";
    setHeatmapSummary(message);
    setHeatmapHoverDetail();
    return;
  }

  const maxEvents = Math.max(...days.map((day) => day.total_events));
  const busiestDay = days.reduce((highest, day) => {
    return day.total_events > highest.total_events ? day : highest;
  });
  const oldestDay = days.at(-1);
  setHeatmapSummary(
    `Showing ${formatCompactNumber(days.length)} days from ${formatDayLabel(oldestDay.day)} ` +
    `to ${formatDayLabel(days[0].day)}. Busiest day: ${formatDayLabel(busiestDay.day)} ` +
    `with ${formatCompactNumber(busiestDay.total_events)} events.`
  );
  setHeatmapHoverDetail();
  renderHeatmapLegend(maxEvents);

  const weeks = new Map();
  for (const day of days) {
    const weekStart = startOfIsoWeek(day.day);
    const cells = weeks.get(weekStart) ?? new Array(7).fill(null);
    cells[isoWeekdayIndex(day.day)] = day;
    weeks.set(weekStart, cells);
  }

  const markup = [...weeks.entries()]
    .sort((left, right) => right[0].localeCompare(left[0]))
    .map(([weekStart, cells]) => {
      const cellMarkup = cells.map((day) => {
        if (!day) {
          return `<span class="heatmap-cell heatmap-cell--empty" aria-hidden="true"></span>`;
        }

        const detail = heatmapDetail(day);
        return `
          <button
            aria-label="${escapeHtml(detail)}"
            class="heatmap-cell heatmap-cell--level-${heatmapLevel(day.total_events, maxEvents)}"
            data-detail="${escapeHtml(detail)}"
            data-day="${day.day}"
            role="gridcell"
            title="${escapeHtml(detail)}"
            type="button"
          ></button>
        `;
      }).join("");

      return `<div class="heatmap-week" data-week-start="${weekStart}" role="row">${cellMarkup}</div>`;
    })
    .join("");

  if (markup !== state.heatmapMarkup) {
    grid.innerHTML = markup;
    state.heatmapMarkup = markup;
    bindHeatmapInteractions();
  }
}

function renderProjectOptions(projects) {
  const select = document.getElementById("project-filter");
  if (!select) {
    return;
  }

  const currentValue = state.project;
  const orderedProjects = [...projects];
  if (currentValue && !orderedProjects.some((project) => project.project_name === currentValue)) {
    orderedProjects.unshift({
      project_name: currentValue,
      total_events: 0,
    });
  }

  const signature = orderedProjects
    .map((project) => `${project.project_name}:${project.total_events}`)
    .join("\u0000");
  if (signature === state.projectOptionsSignature) {
    return;
  }
  state.projectOptionsSignature = signature;

  select.innerHTML = '<option value="">All Projects</option>';
  for (const project of orderedProjects) {
    const option = document.createElement("option");
    option.value = project.project_name;
    option.textContent = project.project_name;
    option.selected = project.project_name === currentValue;
    select.append(option);
  }
}

function projectQuickPicks(projects) {
  return projects
    .filter((project) => !DEMOTED_PROJECTS.has(project.project_name))
    .slice(0, 5);
}

function renderProjectQuickPicks(projects) {
  const container = document.getElementById("project-quick-picks");
  if (!container) {
    return;
  }

  const quickPicks = projectQuickPicks(projects);
  if (quickPicks.length === 0) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = "";

  if (state.project) {
    const allButton = document.createElement("button");
    allButton.className = "project-quick-pick project-quick-pick--amber project-quick-pick--tilt-flat";
    allButton.setAttribute("aria-pressed", "false");
    allButton.dataset.project = "";
    allButton.type = "button";
    allButton.textContent = "All";
    container.append(allButton);
  } else {
    const label = document.createElement("span");
    label.className = "quick-picks-label";
    label.textContent = "Quick jump";
    container.append(label);
  }

  for (const [index, project] of quickPicks.entries()) {
    const button = document.createElement("button");
    const variantClass = QUICK_PICK_VARIANT_CLASSES[index % QUICK_PICK_VARIANT_CLASSES.length];
    const tiltClass = QUICK_PICK_TILT_CLASSES[index % QUICK_PICK_TILT_CLASSES.length];
    button.className = `project-quick-pick ${variantClass} ${tiltClass}`;
    if (project.project_name === state.project) {
      button.classList.add("is-active");
    }
    button.setAttribute("aria-pressed", String(project.project_name === state.project));
    button.dataset.project = project.project_name;
    button.type = "button";
    button.title = `${project.project_name}: ${formatCompactNumber(project.total_events)} events`;

    const name = document.createElement("span");
    name.textContent = project.project_name;
    button.append(name);

    const count = document.createElement("strong");
    count.textContent = formatCompactNumber(project.total_events);
    button.append(count);

    container.append(button);
  }

  for (const button of container.querySelectorAll(".project-quick-pick")) {
    button.addEventListener("click", async () => {
      state.project = button.dataset.project ?? "";
      const select = document.getElementById("project-filter");
      if (select instanceof HTMLSelectElement) {
        select.value = state.project;
      }
      await loadMetrics();
    });
  }
}

function renderDiagnostics() {
  if (!state.diagnostics) {
    resetDiagnostics();
    return;
  }

  setText("provider-count", String(state.diagnostics.provider_count));
  setText("diagnostic-conversations", String(state.diagnostics.conversation_count));
  setText("diagnostic-prompts", String(state.diagnostics.prompt_event_count));
  setText("last-refresh", formatTimestamp(state.latestRefresh));
}

async function loadMetrics(options = {}) {
  const { showBusy = true } = options;
  let requestFailed = false;
  const renderToken = state.renderToken + 1;
  state.renderToken = renderToken;

  if (showBusy) {
    setBusy(true, "Loading Activity", pickMessage(LOAD_MESSAGES));
  }

  try {
    const params = new URLSearchParams({ period: state.period });
    if (state.project) {
      params.set("project", state.project);
    }
    if (state.provider) {
      params.set("provider", state.provider);
    }

    const response = await fetch(`/api/metrics?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Metrics request failed with status ${response.status}`);
    }

    const payload = await response.json();
    if (renderToken !== state.renderToken) {
      return null;
    }
    state.latestRefresh = payload.last_refreshed_at;
    state.diagnostics = payload.refresh;
    renderProjectOptions(payload.projects);
    renderProjectQuickPicks(payload.projects);
    renderSummary(payload.summary);
    renderTable(payload.rows);
    renderHeatmap(payload.heatmap_days);
    renderDiagnostics();
    return payload;
  } catch (error) {
    requestFailed = true;
    console.error(error);
    setScanState("error");
    setStatusNote("Could not load the activity view. Try scanning again.");
    return null;
  } finally {
    if (showBusy) {
      setBusy(false);
      if (!requestFailed) {
        setStatusNote(defaultStatusNote());
      }
    }
  }
}

async function refreshData(options = {}) {
  const { automatic = false } = options;
  let requestFailed = false;
  const buttonLabel = automatic ? "Reading Logs" : "Scanning";
  const message = automatic
    ? pickMessage(AUTO_REFRESH_MESSAGES)
    : pickMessage(REFRESH_MESSAGES);

  setBusy(true, buttonLabel, message);

  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    if (!response.ok) {
      throw new Error(`Refresh request failed with status ${response.status}`);
    }

    state.diagnostics = await response.json();
    state.latestRefresh = state.diagnostics.last_refreshed_at;
    const payload = await loadMetrics({ showBusy: false });
    if (!payload) {
      throw new Error("Metrics reload failed after refresh");
    }
    setScanState("fresh");
    celebrateRefresh();
    setStatusNote(automatic ? pickMessage(AUTO_SUCCESS_MESSAGES) : pickMessage(SUCCESS_MESSAGES));
  } catch (error) {
    requestFailed = true;
    console.error(error);
    setScanState("error");
    setStatusNote(pickMessage(FAILURE_MESSAGES));
  } finally {
    setBusy(false);
    if (!requestFailed) {
      setScanState("fresh");
    }
  }
}

function bindControls() {
  for (const button of document.querySelectorAll(".segment-button")) {
    button.addEventListener("click", async () => {
      state.period = button.dataset.period ?? "day";
      for (const other of document.querySelectorAll(".segment-button")) {
        other.classList.toggle("is-active", other === button);
        other.setAttribute("aria-pressed", String(other === button));
      }
      await loadMetrics();
    });
  }

  document.getElementById("project-filter")?.addEventListener("change", async (event) => {
    state.project = event.target.value;
    await loadMetrics();
  });

  document.getElementById("provider-filter")?.addEventListener("change", async (event) => {
    state.provider = event.target.value;
    await loadMetrics();
  });

  document.getElementById("refresh-button")?.addEventListener("click", async () => {
    await refreshData();
  });
}

async function initializeDashboard() {
  const shell = document.querySelector(".shell");
  state.latestRefresh = shell?.dataset.lastRefresh || null;
  bindControls();
  setStatusNote(defaultStatusNote());
  const payload = await loadMetrics();
  if (!payload?.refresh) {
    await refreshData({ automatic: true });
  }
}

void initializeDashboard();
