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

To add activities newer than the export:

1. Call `get-all-activities` with `startDate` after the last DB entry
2. Call `get-activity-details` for each new activity
3. Write the data as JSON to a temp file (array of objects with Strava API field names: `id`, `start_date`, `name`, `type`, `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain`, `average_speed`, `max_speed`, `average_heartrate`, `max_heartrate`, `average_watts`, `calories`, `average_cadence`, `gear_name`, etc.)
4. Run: `python3 scripts/sync_strava.py /tmp/strava_sync.json`

Check the latest activity date before syncing:
```bash
sqlite3 db/training.db "SELECT MAX(activity_date) FROM activities"
```

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

Static HTML/CSS/JS site in `site/`. Displays the 14-week training plan, progress charts, time prediction, exercise library, and race day reference.

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

The dashboard reads `site/data/training.json` which is generated from `db/training.db`, `plan/swiss-iron-trail-t78.md`, `plan/t78-course.gpx`, and `plan/t78-race-plan.json`. Those source files are the source of truth — editing them automatically updates the dashboard on next export.

### Race-day plan (aid stations + nutrition)

`plan/t78-race-plan.json` holds the official aid station availability (from the Swiss Irontrail Verpflegungsplan PDF) and your personal nutrition/drink plan per station (carry out / consume here). The aid station distance + elevation come from `plan/t78-course.gpx` via track-point indices hardcoded in `scripts/export_dashboard_data.py` (`T78_WAYPOINTS`). Edit the JSON to adjust the plan; edit the indices if Outdooractive republishes the GPX.

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
