# Summary And Heatmap Design

## Goal

Fix the dashboard's top-level summary semantics and replace the current line chart with a more
useful daily heatmap.

The current page mixes two different scopes:

- `project` and `tool` are page-wide filters
- `day / week / month` is a ledger grouping control

Right now the summary strip is derived from the grouped ledger rows, which makes
`conversation_count` change when the grouping changes. That is incorrect for the mental model the
page is trying to support.

The redesign will make the scopes explicit:

- top summaries reflect the current page-wide filters only
- ledger grouping affects only the table
- the right-side visualization becomes a daily activity heatmap

## User Outcome

After this change, a user should be able to:

1. pick a `project` and/or `tool`
2. read stable overall totals for that filtered slice
3. change `day / week / month` without the overall totals shifting
4. inspect recent day-by-day intensity in a compact vertical heatmap
5. hover any heatmap cell to see exact daily statistics

## Current Problem

### Summary bug

The top summary metrics are currently computed by summing the visible grouped rows returned from
`aggregate_metrics`.

That works for additive metrics:

- text prompts
- slash commands

It does not work for conversations, because grouped rows dedupe conversations inside each period
bucket. When the same conversation spans multiple days, summing day buckets overcounts compared
with summing month buckets.

Observed behavior on real data:

- `day`: conversations `125`
- `week`: conversations `115`
- `month`: conversations `110`

This is not a display quirk. It is a real data-model mismatch between grouped ledger rows and the
page-level summary band.

### Activity chart mismatch

The current line chart has exact hover values, but it still asks the user to interpolate a daily
activity pattern from a chart intended for trend reading. The user specifically wants something
closer to an activity ledger: compact, daily, scannable, and exact on hover.

## Design Direction

### Summary band

The dashboard gets a dedicated summary band, separate from the filter row.

The order becomes:

1. masthead and scan status
2. filters and ledger grouping control
3. summary band with helper copy
4. ledger and heatmap workspace

The summary band contains:

- conversations
- text prompts
- slash commands

The helper copy should explicitly explain scope:

`These totals match the current project and tool filters. Grouping only changes the ledger below.`

### Grouping control

The current `Day / Week / Month` segmented control should remain, but it needs clearer scope. It is
not a global time filter. It is only the ledger grouping mode.

The control should therefore be labeled as ledger grouping, either directly in nearby copy or with
an explicit small label.

### Heatmap

The right-side visualization becomes a daily heatmap.

Behavior:

- one cell per day
- newest day at the top
- older days flow downward
- color intensity represents total daily events
- zero-activity days remain visible as empty/light cells
- page-wide filters apply
- ledger grouping does not affect the heatmap

Hover content per day:

- date
- conversations
- text prompts
- slash commands
- total events

The heatmap should use a vertical layout rather than GitHub's horizontal contribution pattern. The
goal is not to mimic GitHub; it is to give the dashboard a compact, legible daily activity column
that reads like a side ledger.

## Data Model And Query Design

### Keep existing grouped ledger data

`aggregate_metrics` remains the source for the table because it already supports grouped ledger
rows for:

- `day`
- `week`
- `month`

No ledger behavior should regress.

### Add page-level summary query

Add a separate summary query derived from normalized base tables, filtered by `project` and `tool`
only.

Source of truth:

- `conversations` for distinct conversation totals
- `prompt_events` for text prompt totals and slash command totals

This query must ignore the selected ledger grouping.

Required output:

- `conversation_count`
- `text_prompt_count`
- `slash_command_count`

This makes the summary band stable across `day / week / month`.

### Add daily heatmap query

Add a dedicated daily query from normalized base data.

Preferred source:

- `prompt_events` aggregated by day, project, and tool
- `conversations` joined or separately counted per day for hover details

Output shape per day:

- `date`
- `conversation_count`
- `text_prompt_count`
- `slash_command_count`
- `total_event_count`

Range:

- last 12 months of daily data, inclusive of zero-activity days

The query layer or server layer must backfill missing calendar days so the heatmap remains visually
continuous.

## API Changes

Extend `GET /api/metrics` so one response can hydrate the whole page.

Response sections:

- `summary`
- `rows`
- `projects`
- `heatmap_days`
- `last_refreshed_at`
- `refresh`

Semantics:

- `summary` depends on `project` and `tool`
- `rows` depends on `project`, `tool`, and `period`
- `heatmap_days` depends on `project` and `tool`
- `projects` ranking should continue to depend on the current `tool` filter

This preserves the current one-request client model while fixing the scope confusion.

## UI Behavior

### Filters

Page-wide filters:

- project
- tool

These update:

- summary band
- ledger rows
- heatmap

### Ledger grouping

`day / week / month` updates only:

- ledger rows

It must not update:

- summary band
- heatmap

### Hover interaction

Hovering a heatmap cell shows a small exact-stat readout for that day.

That can be implemented as:

- tooltip attached to the cell, or
- a persistent detail line near the heatmap that updates on hover

The tooltip/detail content must include the exact date and all four metrics.

## Visual Direction

The current indie side-project styling should stay intact.

The new summary band should be:

- more prominent than the filters
- clearly readable as the dashboard's top totals
- visually separate from the grouping control

The heatmap should feel like part of the same system:

- warm/mint/coral palette already established
- compact daily grid
- low-noise empty days
- obvious hover affordance

The heatmap should not look like a generic analytics chart replacement. It should read as a daily
activity board.

## Implementation Notes

### Backend

Add new query helpers in `ai_monitor.db.queries`:

- fetch_summary_metrics(...)
- fetch_daily_heatmap(...)

Update `ai_monitor.server.routes.get_metrics` to return these new sections.

### Frontend

Update the dashboard template to:

- separate filters from summary band
- add helper copy clarifying grouping scope
- replace the line chart container with a heatmap container

Update the client code to:

- render summary from `payload.summary`
- stop deriving summary from ledger rows
- render heatmap from `payload.heatmap_days`
- keep ledger rendering tied to `payload.rows`

Remove line-chart-specific code that is no longer needed after the heatmap lands.

## Testing

### Query and API tests

Add regression coverage for:

- summary totals stay identical across `day`, `week`, and `month` for the same `project/tool`
- conversation totals are distinct-conversation totals, not bucket-summed totals
- heatmap payload includes zero-activity days in the requested range
- heatmap payload contains exact per-day conversation/text/slash/total counts

### Browser verification

Verify with Playwright:

- summary numbers stay fixed while switching `day / week / month`
- ledger rows change when grouping changes
- heatmap remains unchanged when grouping changes
- project/tool filters update summary, ledger, and heatmap together
- hovering a heatmap cell reveals exact day statistics
- desktop and mobile layouts remain usable

## Risks

### Conversation semantics by day

Daily conversation counts in the heatmap must be defined clearly. The simplest rule is:

- a conversation counts on a day if at least one prompt event occurred on that day

This rule is consistent with prompt-based ingestion and easy to explain in hover output.

### Query cost

Daily backfill across 12 months is still small for a local SQLite app, but the implementation
should keep the query logic straightforward and avoid unnecessary post-processing in the browser.

## Out Of Scope

This change does not introduce:

- custom date range selection
- additional aggregate cards beyond the three existing totals
- multiple heatmap modes
- per-conversation drilldown UI
- export features

## Recommended Implementation Order

1. add summary and daily heatmap query helpers
2. extend `/api/metrics` response shape
3. add tests proving summary stability across grouping modes
4. redesign template layout so summary band is separate and prominent
5. replace the line chart renderer with heatmap rendering and hover details
6. verify responsive behavior and hover states in Playwright
