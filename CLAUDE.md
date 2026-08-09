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
- `scripts/route_photos/route_photos.py` — Given any GPX, find the Strava community photos along that route and build a contact sheet (see below).

## Route Photos

Strava's map shows community photos as blue dots. They come from a public vector-tile
endpoint, `https://www.strava.com/tiles/photos/{z}/{x}/{y}` — no login, no API key and
no route ID needed. All it takes is a GPX.

### Any route, one command

```bash
python3 scripts/route_photos/route_photos.py <route.gpx>
```

Harvests the tiles along the route, keeps the photos within 25 m of the path, thins
them to the best-scoring one per 250 m, downloads the 768px renditions and writes a
contact sheet to `route-photos/<gpx name>/index.html`. The heading comes from the
route name inside the GPX.

```bash
--no-images            # manifest + contact sheet only; images stay on Strava's CDN
--bucket 500           # one photo per 500 m instead of 250
--max-offset 50        # allow photos up to 50 m off the route
--out DIR --title "…"  # override the defaults
--zoom 15              # coarser tiles; 16 is what declusters into single photos
```

`--no-images` is usually what you want for a quick look — the contact sheet falls back
to the CDN for any photo it can't find on disk, so it works either way.

### The four Pilgrims' Way stages

Those live in `route-photos/stage{1,2,3,4}/` and feed the dashboard:

```bash
cd scripts/route_photos
python3 route_photos.py ../../plan/stages/stage1-guildford-bletchingley.gpx \
    --out ../../route-photos/stage1
python3 export_dashboard_photos.py   # every route-photos/stage*/ -> site/data/route-photos.json
```

`export_dashboard_photos.py` only picks up directories named `stage<number>`; anything
else under `route-photos/` is ignored, so scratch routes can live there safely.

The individual steps (`harvest.py`, `select_download.py`, `build_overview.py`) still
work standalone and each exposes a `run()` for scripting. Selection ranks candidates
by Strava's own `score`, then by proximity to the route; re-running skips files
already on disk.

**`manifest.json` is the durable part; the jpgs are disposable.** The dashboard
hot-links Strava's CDN, so downloaded images only matter for offline use — the 25 MB
from the first run was deleted. The manifests (130 KB) stay, so
`export_dashboard_photos.py` keeps working without a re-harvest. Re-run with
`--out` pointing at the same directory to get the jpgs back.

`mvt.py` is a hand-rolled Mapbox Vector Tile decoder (no third-party dependency); it
was verified against the browser's own decoding of the same tile. Note the tiles arrive
gzipped and this environment's TLS proxy breaks python's `urllib`, so fetches shell out
to `curl --compressed`.

**`route-photos/` is gitignored on purpose** — the photos belong to other Strava users.
Don't commit the images and don't publish the contact sheet as an artifact.

**On the dashboard** the photos appear as a horizontally scrolling strip under each
stage profile (`renderStagePhotos` in `site/js/course.js`), fed by
`site/data/route-photos.json`. That file holds metadata only — the images are
hot-linked from Strava's CDN, so the Docker image stays small and we are not
redistributing anyone's photos. The strip loads the 128px thumbnails (≈3 KB each,
lazily) and only fetches the 768px version when a photo is tapped open, which keeps
it cheap on mobile data. If `route-photos.json` is missing the stage profiles simply
render without strips.

## Training Dashboard

Static HTML/CSS/JS site in `site/`. Displays the 13-week training plan for the **Pilgrims' Way 4-Day** (Sep 3–6, 2026, Guildford → Canterbury, 170.0 km / ~2,470m over 4 stages) and the **Trappenmarathon** (Oct 3, 2026), with progress charts, stage profiles, time prediction, exercise library, and event day reference. (The previous Swiss Irontrail T78 plan lives on in `plan/swiss-iron-trail-t78.md` as an archive; T78 ended at km 48 in a storm DNF + ankle sprain on Jun 27, 2026.)

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

The four stages (dates, GPX filenames, planned hours) are defined in the `STAGES` list in `scripts/export_dashboard_data.py`. Each stage GPX (Strava route export) is parsed into an elevation profile with start/finish waypoints. Any `<wpt>` elements in the GPX (Strava course POIs — aid stations, cafés) are snapped to the nearest track point and merged into the waypoint list automatically, so adding a POI to the Strava route and re-exporting the GPX is enough to get it on the dashboard; the label comes from `<cmt>` (falling back to the 15-char-truncated `<name>`). The per-stage plan (planned time, pace, carbs/fluid budget) is derived from the planned hours at 60 g carbs + 0.5 L fluid per hour, plus the longest carry between refill points.

Edit `STAGES` to change dates or planned times; drop replacement GPX files in `plan/stages/` if routes change.

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
