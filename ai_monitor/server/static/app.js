const state = {
  chart: null,
  diagnostics: null,
  latestRefresh: null,
  loading: false,
  period: "day",
  project: "",
  projectSignature: "",
  provider: "",
  renderToken: 0,
  tableMarkup: "",
};

const TABLE_COLUMNS = [
  ["Period", "period_start"],
  ["Project", "project_name"],
  ["Provider", "provider"],
  ["Conversations", "conversation_count"],
  ["Text Prompts", "text_prompt_count"],
  ["Slash Commands", "slash_command_count"],
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sumBy(rows, field) {
  return rows.reduce((total, row) => total + row[field], 0);
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
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

function formatChartAxisLabel(value) {
  const date = parsePeriodStart(value);
  if (!date) {
    return value;
  }

  if (state.period === "month") {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "2-digit",
      timeZone: "UTC",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
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

function defaultStatusNote() {
  if (!state.latestRefresh) {
    return "No local scan yet. The page will build one automatically.";
  }
  return "Using the latest local scan.";
}

function setBusy(isBusy, label = "Refresh Local Logs", busyMessage = "") {
  state.loading = isBusy;
  setWorkspaceBusy(isBusy);
  const refreshButton = document.getElementById("refresh-button");
  if (refreshButton) {
    refreshButton.disabled = isBusy;
    refreshButton.textContent = isBusy ? label : "Refresh Local Logs";
  }

  for (const control of document.querySelectorAll(".segment-button, .filter select")) {
    control.disabled = isBusy;
  }

  if (isBusy && busyMessage) {
    setStatusNote(busyMessage);
  }
}

function setChartSummary(message) {
  const summary = document.getElementById("chart-summary");
  if (summary) {
    summary.textContent = message;
  }
}

function setChartHoverValue(message = "Hover a bar to inspect the exact value.") {
  const hoverValue = document.getElementById("chart-hover-value");
  if (hoverValue) {
    hoverValue.textContent = message;
  }
}

function destroyChart() {
  if (state.chart) {
    state.chart.destroy();
    state.chart = null;
  }
}

function chartEntries(rows) {
  const grouped = new Map();
  for (const row of rows) {
    const current = grouped.get(row.period_start) ?? 0;
    grouped.set(row.period_start, current + row.text_prompt_count + row.slash_command_count);
  }

  return [...grouped.entries()]
    .sort((left, right) => left[0].localeCompare(right[0]))
    .slice(-12);
}

function chartHoverMessage(entries, index) {
  const [periodStart, value] = entries[index];
  return `${formatPeriodLabel(periodStart)}: ${formatCompactNumber(value)} events`;
}

function updateChartHover(entries, activeElements) {
  if (!activeElements.length) {
    setChartHoverValue("Hover a point to inspect the exact value.");
    return;
  }

  setChartHoverValue(chartHoverMessage(entries, activeElements[0].index));
}

function chartConfig(entries) {
  const values = entries.map(([, value]) => value);
  const labels = entries.map(([periodStart]) => formatChartAxisLabel(periodStart));
  return {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "#1f6a52",
          backgroundColor: "rgba(31, 106, 82, 0.14)",
          borderWidth: 3,
          cubicInterpolationMode: "monotone",
          fill: true,
          pointBackgroundColor: "#174f3d",
          pointBorderColor: "#f6f2eb",
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          pointRadius: 4,
          tension: 0.32,
        },
      ],
    },
    options: {
      animation: false,
      maintainAspectRatio: false,
      responsive: true,
      interaction: {
        intersect: false,
        mode: "nearest",
      },
      scales: {
        x: {
          grid: {
            color: "rgba(24, 32, 24, 0.05)",
            drawBorder: false,
          },
          ticks: {
            color: "#5e6656",
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(24, 32, 24, 0.08)",
            drawBorder: false,
          },
          ticks: {
            callback: (value) => formatCompactNumber(value),
            color: "#5e6656",
            precision: 0,
          },
          title: {
            color: "#5e6656",
            display: true,
            text: "Events",
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "rgba(24, 32, 24, 0.94)",
          bodyColor: "#f6f2eb",
          displayColors: false,
          padding: 12,
          titleColor: "#f6f2eb",
          callbacks: {
            label: (context) => `${formatCompactNumber(context.parsed.y)} events`,
            title: (items) => {
              if (!items.length) {
                return "";
              }
              return formatPeriodLabel(entries[items[0].dataIndex][0]);
            },
          },
        },
      },
      onHover: (_event, activeElements) => {
        updateChartHover(entries, activeElements);
      },
    },
  };
}

function resetDiagnostics() {
  state.diagnostics = null;
  setText("provider-count", "-");
  setText("diagnostic-conversations", "-");
  setText("diagnostic-prompts", "-");
  setText("last-refresh", formatTimestamp(state.latestRefresh));
}

function renderSummary(rows) {
  setText("conversation-total", formatCompactNumber(sumBy(rows, "conversation_count")));
  setText("text-prompt-total", formatCompactNumber(sumBy(rows, "text_prompt_count")));
  setText("slash-command-total", formatCompactNumber(sumBy(rows, "slash_command_count")));
}

function renderTable(rows) {
  const tbody = document.getElementById("metrics-table-body");
  if (!tbody) {
    return;
  }

  if (rows.length === 0) {
    const message = state.latestRefresh
      ? "No activity for this filter set."
      : "No cached activity yet. Initial scan is pending.";
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

function renderChart(rows) {
  const canvas = document.getElementById("chart-canvas");
  if (!(canvas instanceof HTMLCanvasElement)) {
    return;
  }

  const entries = chartEntries(rows);
  if (entries.length === 0) {
    destroyChart();
    const message = state.latestRefresh
      ? "No chart data is available for the current filter selection."
      : "The chart will populate after the first local scan completes.";
    setChartSummary(message);
    setChartHoverValue("Hover a point to inspect the exact value.");
    return;
  }

  const values = entries.map(([, value]) => value);
  const peakEntry = entries.reduce((highest, entry) => {
    return entry[1] > highest[1] ? entry : highest;
  });
  setChartSummary(
    `Showing ${entries.length} recent periods. Peak burst: ${peakEntry[1]} events on ${formatPeriodLabel(peakEntry[0])}.`
  );
  setChartHoverValue("Hover a point to inspect the exact value.");

  if (typeof Chart === "undefined") {
    destroyChart();
    setChartSummary("Chart library failed to load.");
    return;
  }

  destroyChart();
  state.chart = new Chart(canvas, chartConfig(entries));
}

function renderProjects(rows) {
  const select = document.getElementById("project-filter");
  if (!select) {
    return;
  }

  const currentValue = state.project;
  const projectNames = [...new Set(rows.map((row) => row.project_name))];
  if (currentValue && !projectNames.includes(currentValue)) {
    projectNames.push(currentValue);
  }
  projectNames.sort();
  const signature = projectNames.join("\u0000");
  if (signature === state.projectSignature) {
    return;
  }
  state.projectSignature = signature;

  select.innerHTML = '<option value="">All Projects</option>';
  for (const projectName of projectNames) {
    const option = document.createElement("option");
    option.value = projectName;
    option.textContent = projectName;
    option.selected = projectName === currentValue;
    select.append(option);
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
    setBusy(true, "Loading Activity", "Loading the normalized usage ledger...");
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
    renderProjects(payload.rows);
    renderSummary(payload.rows);
    renderTable(payload.rows);
    renderChart(payload.rows);
    renderDiagnostics();
    return payload;
  } catch (error) {
    requestFailed = true;
    console.error(error);
    setStatusNote("Loading failed. Try refreshing the local logs again.");
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
  const buttonLabel = automatic ? "Building Cache" : "Refreshing";
  const message = automatic
    ? "Starting the first local scan..."
    : "Scanning local Codex and Claude logs...";

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
    setStatusNote(automatic ? "Initial scan complete." : "Local cache refreshed.");
  } catch (error) {
    requestFailed = true;
    console.error(error);
    setStatusNote("Refresh failed. Check the server log and try again.");
  } finally {
    setBusy(false);
    if (!requestFailed && automatic) {
      setStatusNote("Initial scan complete.");
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
