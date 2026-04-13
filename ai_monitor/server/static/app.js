const state = {
  period: "day",
  project: "",
  provider: "",
  latestRefresh: null,
  diagnostics: null,
};

function sumBy(rows, field) {
  return rows.reduce((total, row) => total + row[field], 0);
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
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
    tbody.innerHTML =
      '<tr><td class="empty-state" colspan="6">No activity for this filter set.</td></tr>';
    return;
  }

  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${row.period_start}</td>
          <td>${row.project_name}</td>
          <td>${row.provider}</td>
          <td>${formatCompactNumber(row.conversation_count)}</td>
          <td>${formatCompactNumber(row.text_prompt_count)}</td>
          <td>${formatCompactNumber(row.slash_command_count)}</td>
        </tr>
      `
    )
    .join("");
}

function renderChart(rows) {
  const chart = document.getElementById("chart");
  if (!chart) {
    return;
  }

  const grouped = new Map();
  for (const row of rows) {
    const current = grouped.get(row.period_start) ?? 0;
    grouped.set(
      row.period_start,
      current + row.text_prompt_count + row.slash_command_count
    );
  }

  const values = [...grouped.values()];
  const maxValue = Math.max(...values, 1);
  chart.innerHTML = [...grouped.entries()]
    .map(([label, value]) => {
      const height = Math.max(12, Math.round((value / maxValue) * 180));
      return `
        <div class="chart-bar">
          <div class="chart-bar-fill" style="height:${height}px"></div>
          <span class="chart-bar-label">${label}</span>
        </div>
      `;
    })
    .join("");
}

function renderProjects(rows) {
  const select = document.getElementById("project-filter");
  if (!select) {
    return;
  }

  const currentValue = state.project;
  const projectNames = [...new Set(rows.map((row) => row.project_name))].sort();
  select.innerHTML = '<option value="">All Projects</option>';
  for (const projectName of projectNames) {
    const option = document.createElement("option");
    option.value = projectName;
    option.textContent = projectName;
    if (projectName === currentValue) {
      option.selected = true;
    }
    select.append(option);
  }
}

function renderDiagnostics() {
  if (!state.diagnostics) {
    return;
  }

  setText("provider-count", String(state.diagnostics.provider_count));
  setText("diagnostic-conversations", String(state.diagnostics.conversation_count));
  setText("diagnostic-prompts", String(state.diagnostics.prompt_event_count));
  setText("last-refresh", state.latestRefresh ?? "Not refreshed yet");
}

async function loadMetrics() {
  const params = new URLSearchParams({ period: state.period });
  if (state.project) {
    params.set("project", state.project);
  }
  if (state.provider) {
    params.set("provider", state.provider);
  }

  const response = await fetch(`/api/metrics?${params.toString()}`);
  const payload = await response.json();
  state.latestRefresh = payload.last_refreshed_at;
  state.diagnostics = payload.refresh;
  renderProjects(payload.rows);
  renderSummary(payload.rows);
  renderTable(payload.rows);
  renderChart(payload.rows);
  renderDiagnostics();
}

async function refreshData() {
  const response = await fetch("/api/refresh", { method: "POST" });
  state.diagnostics = await response.json();
  state.latestRefresh = state.diagnostics.last_refreshed_at;
  renderDiagnostics();
  await loadMetrics();
}

function bindControls() {
  for (const button of document.querySelectorAll(".segment-button")) {
    button.addEventListener("click", async () => {
      state.period = button.dataset.period ?? "day";
      for (const other of document.querySelectorAll(".segment-button")) {
        other.classList.toggle("is-active", other === button);
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

  document.getElementById("refresh-button")?.addEventListener("click", refreshData);
}

bindControls();
loadMetrics();
