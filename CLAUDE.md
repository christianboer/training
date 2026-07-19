# Training — Strava Activity Database

## Project Overview

Personal training data from Strava. A SQLite database (`db/training.db`) indexes all activities for easy querying, combining a full Strava data export with incremental sync from the Strava MCP.

## Querying Activities

```bash
sqlite3 db/training.db "SELECT ... FROM activities ..."
```

### Key columns in `activities` table

| Column | Type | Notes |
|---|---|---|
| `activity_id` | INTEGER PK | Strava activity ID |
| `activity_date` | TEXT | ISO 8601 |
| `activity_name` | TEXT | |
| `activity_type` | TEXT | Run, Ride, Virtual Ride, Walk, Hike, etc. |
| `distance_m` | REAL | Meters |
| `moving_time_s` | INTEGER | Seconds |
| `elapsed_time_s` | INTEGER | Seconds |
| `elevation_gain_m` | REAL | |
| `max_speed_mps` | REAL | m/s |
| `average_speed_mps` | REAL | m/s |
| `avg_heart_rate` | REAL | bpm |
| `max_heart_rate` | REAL | bpm |
| `avg_watts` | REAL | |
| `calories` | REAL | |
| `avg_cadence` | REAL | |
| `gear` | TEXT | Shoe/bike name |
| `private_note` | TEXT | User's private note on the activity |
| `athlete_weight_kg` | REAL | |
| `avg_temperature_c` | REAL | |
| `source` | TEXT | `export` or `strava_api` |

Indexes on: `activity_date`, `activity_type`, `distance_m`.

There is also an `activities_raw` table with all 101 original CSV columns stored as text.

### Useful conversions

- Distance: `distance_m / 1000` → km
- Pace (min/km): `moving_time_s / 60.0 / (distance_m / 1000)`
- Speed (km/h): `average_speed_mps * 3.6`

## Syncing New Activities from Strava MCP

Uses the **official claude.ai Strava connector** (server `Strava`, tools `mcp__claude_ai_Strava__*`). Read-only, returns structured metric JSON. The `/strava-sync` slash command (`.claude/commands/strava-sync.md`) automates the full flow; the steps below are the manual equivalent.

Check the latest activity date before syncing:
```bash
sqlite3 db/training.db "SELECT MAX(activity_date) FROM activities"
```

To add activities newer than the export:

1. Call `mcp__claude_ai_Strava__list_activities` with `range_start` set to the last DB timestamp (ISO **local** time, no `Z`), `ordering: StartDateLocalAsc`, `first: 100`. Dedupe returned `id`s against the DB.
2. For each new activity, call `mcp__claude_ai_Strava__get_activity_performance` for HR/watts, and resolve `gear_id` → name via `mcp__claude_ai_Strava__get_gear` (match `gear_id` to `gear_id.id`, format `"{brand} {model_name}"`).
3. Write the data as JSON to a temp file using **Strava API field names**: `id`, `start_date` (from `start_local`), `name`, `type` (from `sport_type`), `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain` (from `elevation_gain`), `average_speed`, `max_speed`, `average_heartrate`, `max_heartrate`, `average_watts`, `calories` (from `total_calories`), `average_cadence`, `suffer_score` (from `relative_effort`), `gear_name`.
4. Run: `python3 scripts/sync_strava.py /tmp/strava_sync.json`

**Note:** This connector does not expose `private_note` (only the public `description`), so legging-wear auto-matching won't fire for newly synced activities — record those manually in `legging_wears` if needed.

**Important:** Always run `python3 scripts/export_dashboard_data.py` after syncing new activities. This updates `site/data/training.json` (including the "Last updated" timestamp shown in the dashboard footer). Then **commit and push** the updated `site/data/training.json` so the change is reflected in the remote repository.

## Legging Wear Tracking

### Tables

**`leggings`** — 40 Lululemon leggings from `~/Documents/Projects/outfits/web/src/data/collection.json`

| Column | Notes |
|---|---|
| `legging_id` | PK autoincrement |
| `slug` | UNIQUE `type-slug/color-slug` |
| `type_name` | e.g. `Swift Speed 28"` |
| `color_name` | e.g. `Sonic Pink` |
| `full_name` | e.g. `Lululemon Swift Speed 28" Sonic Pink` |
| `location` | Where stored (Ouddorp, Barendrecht) |

**`legging_wears`** — Links activities to leggings (`activity_id`, `legging_id`, `match_method`)

### Season queries

Seasons: fall-winter runs Sep–Apr, spring-summer runs May–Aug.

```sql
-- Not yet worn this season (fall-winter 25-26)
SELECT l.full_name, l.location FROM leggings l
WHERE l.legging_id NOT IN (
    SELECT lw.legging_id FROM legging_wears lw
    JOIN activities a ON a.activity_id = lw.activity_id
    WHERE a.activity_date >= '2025-09-01' AND a.activity_date < '2026-05-01'
) ORDER BY l.type_name, l.color_name;

-- Wear count this season
SELECT l.full_name, COUNT(*) as wears FROM legging_wears lw
JOIN leggings l ON l.legging_id = lw.legging_id
JOIN activities a ON a.activity_id = lw.activity_id
WHERE a.activity_date >= '2025-09-01' AND a.activity_date < '2026-05-01'
GROUP BY l.legging_id ORDER BY wears DESC;
```

### Matching private notes to leggings

`scripts/index_leggings.py` auto-matches activity private notes to leggings by type keyword + color slug words. Notes that can't be auto-matched (typos, alternate names, pipe separators) are reported for manual resolution via SQL INSERT into `legging_wears`.

## Scripts

- `scripts/import_csv.py` — One-time import of `strava/activities.csv` into SQLite. Idempotent (INSERT OR REPLACE).
- `scripts/sync_strava.py` — Insert activities from a JSON file (Strava API format). Marks them with `source = 'strava_api'`.
- `scripts/index_leggings.py` — Import leggings collection and auto-match private notes to legging wears. Re-runnable (idempotent). Reports unmatched for manual review.
- `scripts/export_dashboard_data.py` — Export SQLite + plan markdown to `site/data/training.json` for the dashboard. Re-run after every Strava sync.

## Training Dashboard

Static HTML/CSS/JS site in `site/`. Displays the 13-week training plan for the **Pilgrims' Way 4-Day** (Sep 3–6, 2026, Guildford → Canterbury, 168.7 km / ~3,189m over 4 stages) and the **Trappenmarathon** (Oct 3, 2026), with progress charts, stage profiles, time prediction, exercise library, and event day reference. (The previous Swiss Irontrail T78 plan lives on in `plan/swiss-iron-trail-t78.md` as an archive; T78 ended at km 48 in a storm DNF + ankle sprain on Jun 27, 2026.)

### Serving locally

```bash
python3 -m http.server -d site 8080
# Open http://localhost:8080
```

### Updating data after Strava sync

```bash
python3 scripts/sync_strava.py /tmp/strava_sync.json
python3 scripts/export_dashboard_data.py
```

The dashboard reads `site/data/training.json` which is generated from `db/training.db`, `plan/pilgrims-way-4day.md`, and the four stage GPX files in `plan/stages/`. Those source files are the source of truth — editing them automatically updates the dashboard on next export.

### Stage plan (4-Day logistics)

The four stages (dates, GPX filenames, planned hours) are defined in the `STAGES` list in `scripts/export_dashboard_data.py`. Each stage GPX (Strava route export) is parsed into an elevation profile with start/finish waypoints; the per-stage plan (planned time, pace, carbs/fluid budget) is derived from the planned hours at 60 g carbs + 0.5 L fluid per hour. Edit `STAGES` to change dates or planned times; drop replacement GPX files in `plan/stages/` if routes change.

### Structure

- `site/index.html` — Single page with all sections
- `site/css/style.css` — Mountain dark theme, responsive
- `site/js/app.js` — Main controller (countdown, timeline, heatmap, gear checklist, pace calculator)
- `site/js/plan.js` — This Week view (matches plan days to actual activities, week navigation)
- `site/js/charts.js` — Chart.js charts (weekly volume, elevation, cumulative progress)
- `site/js/exercises.js` — Exercise cards with inline SVG stick-figure illustrations, photo hover, video support, click-to-modal
- `site/img/exercises/` — Exercise photos (1:1, 1024x1024 JPG). Named by slug: `90-90-hip-switches.jpg`, `cat-cow.jpg`, etc. Auto-detected on page load.

### Adding exercise media

**Photos:** Drop a 1024x1024 image in `site/img/exercises/{slug}.jpg` (supports .png, .jpeg, .webp too). The slug is the exercise name lowercased with hyphens (e.g., `half-kneeling-hip-flexor-stretch`). Photos appear on card hover and in the modal.

**Videos:** Add a YouTube video ID to the `EXERCISE_VIDEOS` map in `site/js/exercises.js`. Videos appear alongside the photo in the modal.

## Data Sources

- `strava/activities.csv` — Full Strava data export (4,179 activities, 101 columns)
- `strava/activities/` — Binary activity files (FIT/TCX/GPX, 4,145 files)
- `strava/routes/` — Route GPX files (413 files)
- Various other CSVs: shoes, bikes, segments, goals, etc.
