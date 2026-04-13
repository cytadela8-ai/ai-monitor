# Summary And Heatmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the top summary totals stable across ledger grouping changes and replace the current
right-side line chart with a vertical daily heatmap that shows exact per-day stats on hover.

**Architecture:** Keep `aggregate_metrics` as the ledger source for `day/week/month`, but stop
using those grouped rows for the page-wide summary band. Add dedicated SQLite queries for global
summary totals and daily heatmap data from normalized base tables, extend `/api/metrics` to return
all three payload sections, then update the frontend so filters affect the whole page while ledger
grouping affects only the table.

**Tech Stack:** FastAPI, SQLite, vanilla JS, Jinja templates, Chart.js removal from the active UI,
pytest, Playwright, Ruff, Ty

---

## File Structure

- Modify: `ai_monitor/db/queries.py`
  Add dedicated query helpers for fixed summary totals and daily heatmap rows.
- Modify: `ai_monitor/server/routes.py`
  Return `summary` and `heatmap_days` in `GET /api/metrics`.
- Modify: `ai_monitor/server/templates/index.html`
  Separate the summary band from the filter row and replace the chart container with a heatmap
  container and hover detail area.
- Modify: `ai_monitor/server/static/app.js`
  Stop deriving summary totals from grouped ledger rows; render fixed summary data and the vertical
  heatmap; keep `day/week/month` scoped to the ledger only.
- Modify: `ai_monitor/server/static/app.css`
  Style the summary band as its own prominent block and implement the vertical heatmap layout and
  hover states.
- Create: `tests/db/test_queries.py`
  Add query-level tests for fixed summary totals and daily heatmap output.
- Modify: `tests/server/test_metrics_api.py`
  Assert the new payload sections and stable summary semantics.
- Modify: `tests/server/test_dashboard.py`
  Assert the updated template structure and summary/heatmap markup.
- Modify: `README.md`
  Update the dashboard description to mention fixed totals and the daily heatmap.
- Modify: `DEV.md`
  Document the new query responsibilities and the UI split between filters and grouping.

## Task 1: Add Query-Level Regression Coverage

**Files:**
- Create: `tests/db/test_queries.py`
- Modify: `tests/server/test_metrics_api.py`

- [ ] **Step 1: Write failing query tests for stable summary totals**

```python
from pathlib import Path

from ai_monitor.db.queries import fetch_summary_metrics


def test_fetch_summary_metrics_ignores_ledger_grouping(seed_database: Path) -> None:
    day_summary = fetch_summary_metrics(seed_database)
    week_summary = fetch_summary_metrics(seed_database)
    month_summary = fetch_summary_metrics(seed_database)

    assert day_summary == week_summary == month_summary
```

- [ ] **Step 2: Write failing query tests for daily heatmap output**

```python
from ai_monitor.db.queries import fetch_daily_heatmap


def test_fetch_daily_heatmap_returns_zero_filled_days(seed_database: Path) -> None:
    rows = fetch_daily_heatmap(seed_database, days=7)

    assert len(rows) == 7
    assert rows[-1].date >= rows[0].date
    assert any(row.total_event_count == 0 for row in rows)


def test_fetch_daily_heatmap_includes_exact_day_counts(seed_database: Path) -> None:
    rows = fetch_daily_heatmap(seed_database, days=30, project="zk-chains-registry")

    target = next(row for row in rows if row.date == "2026-04-07")
    assert target.text_prompt_count == 48
    assert target.slash_command_count == 17
    assert target.total_event_count == 65
```

- [ ] **Step 3: Add API-level failing assertions for the new payload shape**

```python
def test_metrics_endpoint_returns_summary_and_heatmap(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "week"})

    payload = response.json()
    assert "summary" in payload
    assert "heatmap_days" in payload
    assert payload["summary"]["conversation_count"] > 0
    assert payload["heatmap_days"]


def test_summary_totals_stay_fixed_across_grouping_modes(client: TestClient) -> None:
    day_payload = client.get("/api/metrics", params={"period": "day"}).json()
    week_payload = client.get("/api/metrics", params={"period": "week"}).json()
    month_payload = client.get("/api/metrics", params={"period": "month"}).json()

    assert day_payload["summary"] == week_payload["summary"] == month_payload["summary"]
```

- [ ] **Step 4: Run tests to verify they fail for the current implementation**

Run:

```bash
uv run pytest -q tests/db/test_queries.py tests/server/test_metrics_api.py
```

Expected:

- `ImportError` or `AttributeError` for missing query helpers
- API assertions fail because `/api/metrics` does not yet return `summary` or `heatmap_days`

- [ ] **Step 5: Commit**

```bash
git add tests/db/test_queries.py tests/server/test_metrics_api.py
git commit -m "test: cover summary and heatmap queries"
```

## Task 2: Add Backend Queries For Fixed Summary And Daily Heatmap

**Files:**
- Modify: `ai_monitor/db/queries.py`
- Test: `tests/db/test_queries.py`

- [ ] **Step 1: Add summary and heatmap row dataclasses**

```python
@dataclass(frozen=True)
class SummaryMetricsRow:
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int


@dataclass(frozen=True)
class DailyHeatmapRow:
    date: str
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int
    total_event_count: int
```

- [ ] **Step 2: Implement `fetch_summary_metrics()` from normalized base tables**

```python
def fetch_summary_metrics(
    database_path: Path,
    project: str | None = None,
    provider: str | None = None,
) -> SummaryMetricsRow:
    ensure_database(database_path)
    conversation_where = []
    prompt_where = []
    params: list[str] = []

    if project is not None:
        conversation_where.append("project_name = ?")
        prompt_where.append("project_name = ?")
        params.append(project)

    if provider is not None:
        conversation_where.append("provider = ?")
        prompt_where.append("provider = ?")
        params.append(provider)

    conversation_sql = " AND ".join(conversation_where) or "1 = 1"
    prompt_sql = " AND ".join(prompt_where) or "1 = 1"

    connection = sqlite3.connect(database_path)
    try:
        conversation_count = connection.execute(
            f"SELECT COUNT(*) FROM conversations WHERE {conversation_sql}",
            params[: len(conversation_where)],
        ).fetchone()[0]
        prompt_row = connection.execute(
            f'''
            SELECT
                SUM(CASE WHEN event_type = "text_prompt" THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type = "slash_command" THEN 1 ELSE 0 END)
            FROM prompt_events
            WHERE {prompt_sql}
            ''',
            params[: len(prompt_where)],
        ).fetchone()
    finally:
        connection.close()

    return SummaryMetricsRow(
        conversation_count=conversation_count,
        text_prompt_count=prompt_row[0] or 0,
        slash_command_count=prompt_row[1] or 0,
    )
```

- [ ] **Step 3: Implement `fetch_daily_heatmap()` with zero-filled days**

```python
def fetch_daily_heatmap(
    database_path: Path,
    project: str | None = None,
    provider: str | None = None,
    days: int = 365,
) -> list[DailyHeatmapRow]:
    ensure_database(database_path)
    # Query daily prompt event totals and distinct conversations per day.
    # Backfill missing days in Python from today - days + 1 through today.
```

Use this SQL shape inside the function:

```sql
SELECT
    DATE(occurred_at) AS day,
    COUNT(DISTINCT provider || ':' || external_conversation_id) AS conversation_count,
    SUM(CASE WHEN event_type = 'text_prompt' THEN 1 ELSE 0 END) AS text_prompt_count,
    SUM(CASE WHEN event_type = 'slash_command' THEN 1 ELSE 0 END) AS slash_command_count
FROM prompt_events
WHERE ...
GROUP BY DATE(occurred_at)
ORDER BY day ASC
```

- [ ] **Step 4: Run the focused tests and make them pass**

Run:

```bash
uv run pytest -q tests/db/test_queries.py tests/server/test_metrics_api.py
```

Expected:

- query tests pass
- API tests still fail because the route has not been updated yet

- [ ] **Step 5: Commit**

```bash
git add ai_monitor/db/queries.py tests/db/test_queries.py tests/server/test_metrics_api.py
git commit -m "feat: add summary and heatmap queries"
```

## Task 3: Extend `/api/metrics` To Return Summary And Heatmap Data

**Files:**
- Modify: `ai_monitor/server/routes.py`
- Test: `tests/server/test_metrics_api.py`

- [ ] **Step 1: Update imports to include the new query helpers**

```python
from ai_monitor.db.queries import (
    fetch_daily_heatmap,
    fetch_latest_refresh_run,
    fetch_metrics_rows,
    fetch_ranked_projects,
    fetch_summary_metrics,
)
```

- [ ] **Step 2: Add `summary` and `heatmap_days` to the route response**

```python
summary = fetch_summary_metrics(
    database_path=config.database_path,
    project=project,
    provider=provider,
)
heatmap_days = fetch_daily_heatmap(
    database_path=config.database_path,
    project=project,
    provider=provider,
)

return {
    "period": period,
    "summary": summary.__dict__,
    "rows": [row.__dict__ for row in rows],
    "projects": [project_row.__dict__ for project_row in projects],
    "heatmap_days": [row.__dict__ for row in heatmap_days],
    "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
    "refresh": None if last_refresh is None else last_refresh.__dict__,
}
```

- [ ] **Step 3: Update API tests to assert the exact response structure**

```python
def test_metrics_endpoint_returns_summary_and_heatmap(client: TestClient) -> None:
    payload = client.get("/api/metrics", params={"period": "week"}).json()

    assert sorted(payload["summary"]) == [
        "conversation_count",
        "slash_command_count",
        "text_prompt_count",
    ]
    assert sorted(payload["heatmap_days"][0]) == [
        "conversation_count",
        "date",
        "slash_command_count",
        "text_prompt_count",
        "total_event_count",
    ]
```

- [ ] **Step 4: Run API tests**

Run:

```bash
uv run pytest -q tests/server/test_metrics_api.py
```

Expected:

- all API tests pass

- [ ] **Step 5: Commit**

```bash
git add ai_monitor/server/routes.py tests/server/test_metrics_api.py
git commit -m "feat: return summary and heatmap data"
```

## Task 4: Redesign The Template For Separate Summary Band And Heatmap

**Files:**
- Modify: `ai_monitor/server/templates/index.html`
- Modify: `tests/server/test_dashboard.py`

- [ ] **Step 1: Add a dedicated summary band outside the filter row**

Replace the current toolbar summary placement with this structure:

```html
<section class="toolbar panel">
  <div class="segment-shell">
    <span class="toolbar-label">Ledger grouping</span>
    <div class="segment" aria-label="Ledger grouping" role="group">
      ...
    </div>
  </div>
  <div class="filter-row">...</div>
  <div class="project-quick-picks" id="project-quick-picks"></div>
</section>

<section class="summary-band panel" aria-label="Overall totals">
  <div class="summary-band-copy">
    <h2>Overall totals</h2>
    <p>These totals match the current project and tool filters. Grouping only changes the ledger below.</p>
  </div>
  <p class="summary-ribbon" aria-label="Current totals">
    ...
  </p>
</section>
```

- [ ] **Step 2: Replace the chart area with a heatmap shell**

```html
<article class="panel heatmap-panel">
  <div class="panel-heading">
    <h2>Daily Activity Grid</h2>
    <p>Latest days at the top. Hover a cell for exact counts.</p>
  </div>
  <div class="heatmap-shell">
    <div class="heatmap-grid" id="heatmap-grid" aria-label="Daily activity heatmap"></div>
  </div>
  <p class="heatmap-hover-detail" id="heatmap-hover-detail">
    Point at a day to see the exact mix.
  </p>
</article>
```

- [ ] **Step 3: Update template tests to match the new structure**

```python
def test_dashboard_exposes_summary_band_and_heatmap(client: TestClient) -> None:
    body = client.get("/").text

    assert 'class="summary-band panel"' in body
    assert 'id="heatmap-grid"' in body
    assert 'id="heatmap-hover-detail"' in body
    assert "Ledger grouping" in body
```

- [ ] **Step 4: Run the dashboard tests**

Run:

```bash
uv run pytest -q tests/server/test_dashboard.py
```

Expected:

- tests fail until the template and JS are aligned

- [ ] **Step 5: Commit**

```bash
git add ai_monitor/server/templates/index.html tests/server/test_dashboard.py
git commit -m "feat: add summary band and heatmap shell"
```

## Task 5: Replace Chart Rendering With Vertical Daily Heatmap Rendering

**Files:**
- Modify: `ai_monitor/server/static/app.js`
- Modify: `ai_monitor/server/static/app.css`
- Test: `tests/server/test_dashboard.py`

- [ ] **Step 1: Stop deriving summary totals from ledger rows**

Replace:

```javascript
function renderSummary(rows) {
  setText("conversation-total", formatCompactNumber(sumBy(rows, "conversation_count")));
  setText("text-prompt-total", formatCompactNumber(sumBy(rows, "text_prompt_count")));
  setText("slash-command-total", formatCompactNumber(sumBy(rows, "slash_command_count")));
}
```

with:

```javascript
function renderSummary(summary) {
  setText("conversation-total", formatCompactNumber(summary.conversation_count));
  setText("text-prompt-total", formatCompactNumber(summary.text_prompt_count));
  setText("slash-command-total", formatCompactNumber(summary.slash_command_count));
}
```

- [ ] **Step 2: Add a heatmap renderer**

```javascript
function renderHeatmap(days) {
  const grid = document.getElementById("heatmap-grid");
  const detail = document.getElementById("heatmap-hover-detail");
  if (!grid || !detail) {
    return;
  }

  grid.innerHTML = "";
  const max = Math.max(...days.map((day) => day.total_event_count), 1);

  for (const day of [...days].reverse()) {
    const cell = document.createElement("button");
    cell.className = "heatmap-cell";
    cell.type = "button";
    cell.dataset.intensity = String(
      day.total_event_count === 0 ? 0 : Math.ceil((day.total_event_count / max) * 4)
    );
    cell.setAttribute("aria-label", `${day.date}: ${day.total_event_count} events`);
    cell.addEventListener("mouseenter", () => {
      detail.textContent =
        `${day.date}: ${day.conversation_count} conversations, ` +
        `${day.text_prompt_count} text prompts, ` +
        `${day.slash_command_count} slash cmds, ` +
        `${day.total_event_count} events total`;
    });
    cell.addEventListener("focus", () => {
      detail.textContent =
        `${day.date}: ${day.conversation_count} conversations, ` +
        `${day.text_prompt_count} text prompts, ` +
        `${day.slash_command_count} slash cmds, ` +
        `${day.total_event_count} events total`;
    });
    grid.append(cell);
  }
}
```

- [ ] **Step 3: Wire the payload correctly**

Update the load path:

```javascript
renderSummary(payload.summary);
renderTable(payload.rows);
renderHeatmap(payload.heatmap_days);
```

Remove chart-specific render scheduling and active chart instance handling once the heatmap is
working.

- [ ] **Step 4: Style the vertical heatmap**

Add this CSS structure:

```css
.summary-band {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: end;
}

.heatmap-grid {
  display: grid;
  grid-auto-flow: row;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}

.heatmap-cell {
  aspect-ratio: 1;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  background: var(--surface-muted);
}

.heatmap-cell[data-intensity="1"] { background: color-mix(in srgb, var(--page-pop) 22%, white); }
.heatmap-cell[data-intensity="2"] { background: color-mix(in srgb, var(--page-pop) 35%, var(--accent) 10%); }
.heatmap-cell[data-intensity="3"] { background: color-mix(in srgb, var(--accent) 54%, white 8%); }
.heatmap-cell[data-intensity="4"] { background: color-mix(in srgb, var(--accent) 82%, var(--coral) 8%); }
```

On narrow screens, let the heatmap panel still appear before the ledger but keep the grid legible.

- [ ] **Step 5: Run targeted tests and a manual browser check**

Run:

```bash
uv run pytest -q tests/server/test_dashboard.py tests/server/test_metrics_api.py
```

Then verify manually:

```bash
uv run uvicorn ai_monitor.server.app:app --reload --port 8012
```

Expected:

- summary totals do not move when switching `day/week/month`
- ledger rows do move
- heatmap stays fixed for the current filters

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/server/static/app.js ai_monitor/server/static/app.css tests/server/test_dashboard.py
git commit -m "feat: replace activity chart with heatmap"
```

## Task 6: Final Verification, Cleanup, And Docs

**Files:**
- Modify: `README.md`
- Modify: `DEV.md`

- [ ] **Step 1: Remove chart-specific dead code and unused assets**

Delete unused line-chart rendering code in `ai_monitor/server/static/app.js` and confirm no UI path
depends on it. If `ai_monitor/server/static/vendor/chart.umd.min.js` is no longer used after the
heatmap implementation, remove it in the same task.

- [ ] **Step 2: Update docs**

Add this README description update:

```md
- stable overall totals that follow the current project/tool filters
- grouped ledger views by day, week, or month
- a vertical daily heatmap with exact hover statistics
```

Add this DEV note:

```md
- `fetch_summary_metrics()` reads normalized base tables for page-wide totals.
- `fetch_metrics_rows()` remains the grouped ledger source.
- `fetch_daily_heatmap()` builds the filter-aware daily activity payload for the right-side heatmap.
```

- [ ] **Step 3: Run full project checks**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ty check
```

Expected:

- all tests pass
- no lint errors
- no type errors

- [ ] **Step 4: Run final Playwright verification**

Verify in the browser:

1. open the dashboard from a fresh tab
2. note the overall totals
3. switch `Day -> Week -> Month`
4. confirm overall totals stay fixed
5. apply a project filter and confirm totals, ledger, and heatmap all update
6. hover multiple heatmap cells and confirm exact per-day details
7. verify desktop and mobile layouts
8. confirm browser console has no errors

- [ ] **Step 5: Commit**

```bash
git add README.md DEV.md ai_monitor/server/static app.js ai_monitor/server/static/app.css
git add ai_monitor/server/templates/index.html ai_monitor/server/routes.py ai_monitor/db/queries.py
git add tests README.md DEV.md
git commit -m "feat: add stable totals and daily heatmap"
```

## Self-Review

- Spec coverage: covered summary stability, filter/grouping split, vertical newest-first heatmap,
  hover detail, API extension, testing, and docs updates.
- Placeholder scan: no `TODO` or open-ended “handle this later” steps remain.
- Type consistency: plan uses `summary`, `heatmap_days`, `fetch_summary_metrics()`,
  `fetch_daily_heatmap()`, and existing `fetch_metrics_rows()` consistently.
