# Strava Sync

Fetch the latest Strava activities, sync them to the database, export dashboard data, and commit+push.

Uses the **official Strava MCP connector** (`mcp.strava.com`, server name `strava-mcp`, tools prefixed `mcp__strava-mcp__`). It is read-only and returns structured metric JSON. If the tools aren't loaded, fetch their schemas first:

```
ToolSearch query: select:mcp__strava-mcp__list_activities,mcp__strava-mcp__get_activity_performance,mcp__strava-mcp__get_gear
```

## Steps

### 1. Find the last synced activity date

```bash
sqlite3 db/training.db "SELECT MAX(activity_date) FROM activities"
```

Use this timestamp as the lower bound for fetching new activities.

### 2. Fetch new activities from Strava

Call `mcp__strava-mcp__list_activities` with:
- `range_start`: the timestamp from step 1 (ISO LocalDateTime, e.g. `2026-06-17T13:00:00` — note this connector filters on **local** time, no `Z`)
- `ordering`: `StartDateLocalAsc`
- `first`: `100`

Dedupe the returned `id`s against the DB (the last-synced activity may reappear at the boundary):

```bash
sqlite3 db/training.db "SELECT activity_id FROM activities WHERE activity_id IN (<ids>)"
```

If no genuinely new activities remain, inform the user and stop.

`list_activities` already returns the summary fields you need: `id`, `name`, `sport_type`, `start_local`, `gear_id`, and a `summary` block (`distance`, `moving_time`, `elapsed_time`, `elevation_gain`, `avg_speed`, `max_speed`, `avg_cadence`, `total_calories`, `relative_effort`).

### 3. Enrich each new activity

For each new activity:

- **Heart rate / power** — call `mcp__strava-mcp__get_activity_performance` with `activity_id` to get `average_heartrate`, `max_heartrate`, `average_watts` (only present when `has_device_watts`/`has_heartrate`).
- **Gear name** — if the activity has a `gear_id`, resolve it to a name. Call `mcp__strava-mcp__get_gear` once (cache the result) and map `gear_id` → `"{brand} {model_name}"` (e.g. `28504914` → `HOKA Bondi 9 VCH`). Rides often have no `gear_id`; leave gear empty then.

**Known limitation:** This connector does **not** expose `private_note`. It returns the public `description` instead (often empty). Legging-wear matching (step 6) depends on `private_note`, so it will not auto-match new activities — note this to the user; it is not a regression (the old community server didn't expose it either). If a run's leggings need recording, add them manually via `legging_wears`.

### 4. Write JSON and run sync script

`sync_strava.py` expects **Strava API field names**. Map the connector's output:

| Connector field | JSON field for the script |
|---|---|
| `id` | `id` |
| `start_local` | `start_date` (store as-is; local ISO, no `Z`) |
| `name` | `name` |
| `sport_type` | `type` |
| `summary.distance` | `distance` |
| `summary.moving_time` | `moving_time` |
| `summary.elapsed_time` | `elapsed_time` |
| `summary.elevation_gain` | `total_elevation_gain` |
| `summary.avg_speed` | `average_speed` |
| `summary.max_speed` | `max_speed` |
| `summary.avg_cadence` | `average_cadence` |
| `summary.total_calories` | `calories` |
| `summary.relative_effort` | `suffer_score` |
| `average_heartrate` (perf) | `average_heartrate` |
| `max_heartrate` (perf) | `max_heartrate` |
| `average_watts` (perf) | `average_watts` |
| resolved gear | `gear_name` |

Write the array to `/tmp/strava_sync.json`, then run:

```bash
python3 scripts/sync_strava.py /tmp/strava_sync.json
```

Report how many activities were synced.

### 5. Export dashboard data

```bash
python3 scripts/export_dashboard_data.py
```

### 6. Index legging wears

```bash
python3 scripts/index_leggings.py
```

Report any unmatched activities so the user can resolve them manually. (New activities won't carry a `private_note` — see the limitation in step 3.)

### 7. Commit and push

Stage the changed files and create a commit:

```bash
git add db/training.db site/data/training.json
```

Use a commit message like: `Sync N Strava activities (date range) and update dashboard data`

Include a summary of the synced activities (types and count) in the commit body.

Then push to remote:

```bash
git push
```
