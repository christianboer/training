#!/usr/bin/env python3
"""Export training data from SQLite + plan markdown to JSON for the dashboard.

Usage:
    python scripts/export_dashboard_data.py

Reads:
    - db/training.db (activity data)
    - plan/swiss-iron-trail-t78.md (structured training plan)

Writes:
    - site/data/training.json
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DB_PATH = os.path.join(BASE_DIR, 'db', 'training.db')
PLAN_PATH = os.path.join(BASE_DIR, 'plan', 'swiss-iron-trail-t78.md')
OUTPUT_PATH = os.path.join(BASE_DIR, 'site', 'data', 'training.json')

PLAN_START = '2026-03-23'  # Week 1 Monday
RACE_DATE = '2026-06-27'

EVENTS = [
    {"date": "2026-04-12", "name": "Rotterdam Half Marathon", "distance_km": 21, "elevation_m": 0, "role": "Speed sharpener"},
    {"date": "2026-05-22", "name": "French Alps — Bourg d'Oisans", "distance_km": 41, "elevation_m": 3138, "role": "Mountain adaptation",
     "routes": [
         {"name": "Villard via weg omhoog", "km": 14.6, "elevation_m": 1008, "max_alt_m": 1671, "url": "https://www.strava.com/routes/3457828796816278982"},
         {"name": "Villard steil linksom", "km": 13.9, "elevation_m": 1000, "max_alt_m": 1671, "url": "https://www.strava.com/routes/3457840458426864014"},
         {"name": "Villard steil rechtsom", "km": 12.2, "elevation_m": 1130, "max_alt_m": 1833, "url": "https://www.strava.com/routes/3457826669002961350"},
     ],
     "nutrition": {
         "product": "Maurten Drink Mix 320",
         "per_loop": "2× soft flask 500ml = 640 kcal",
         "hotel_stop": "Banana + bread w/ honey (~200 kcal) + 500ml water",
         "total_kcal": 2320,
         "total_fluid_l": 4,
         "heat_note": ">20°C: add 500ml plain water per loop alongside Maurten"
     }},
    {"date": "2026-06-06", "name": "Trail Godefroy", "distance_km": 53, "elevation_m": 1960, "role": "Dress rehearsal",
     "aid_stations": [
         {"name": "R1", "km": 9, "action": "Top up flasks, ½ bar"},
         {"name": "R2", "km": 18, "action": "Full refuel: flask + bar + fruit"},
         {"name": "R3 — Bouillon", "km": 27, "action": "Key stop: Maurten sachet + bar + fruit"},
         {"name": "R4", "km": 36, "action": "Top up flasks, ½ bar"},
         {"name": "R5", "km": 45, "action": "Full refuel: flask + bar + fruit"},
     ],
     "nutrition": {
         "product": "Maurten 320 + bars",
         "strategy": "1× Maurten 320 per segment + ½ bar from R1, fruit at R2/R3/R5",
         "total_kcal": 2620,
         "total_fluid_l": 3.75,
         "carry": "6× Maurten 320 sachets + 3 bars (~200 kcal each)",
         "heat_note": ">25°C: extra water at aid stations + electrolyte tab"
     }},
    {"date": "2026-06-27", "name": "Swiss Iron Trail T78", "distance_km": 78, "elevation_m": 5000, "role": "A-race"},
]

PHASES = [
    {"name": "Base Building", "weeks": [1, 2, 3, 4], "color": "#3b82f6"},
    {"name": "Vertical Loading", "weeks": [5, 6, 7, 8], "color": "#8b5cf6"},
    {"name": "Mountain Specificity", "weeks": [9, 10], "color": "#10b981"},
    {"name": "Race Rehearsal & Taper", "weeks": [11, 12, 13, 14], "color": "#f59e0b"},
]

DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def parse_plan(plan_path):
    """Parse the training plan markdown into structured week/day data."""
    with open(plan_path, 'r') as f:
        content = f.read()

    weeks = []
    # Match week headers like: ### Week 1 (Mar 23–29) or ### Week 3 — Rotterdam HM (Apr 6–12)
    week_pattern = re.compile(
        r'### Week (\d+)(?:\s*—\s*[^(]*)?\s*\(([^)]+)\)\s*\n'
        r'(.*?)(?=\n### |\n---|\n## |\n\*\*[A-Z]|\Z)',
        re.DOTALL
    )

    for m in week_pattern.finditer(content):
        week_num = int(m.group(1))
        date_range = m.group(2).strip()
        block = m.group(3)

        # Parse the day table rows
        days = []
        for line in block.split('\n'):
            line = line.strip()
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.split('|')]
            # split('|') gives ['', cell1, cell2, ...], filter empties from edges
            cells = [c for c in cells if c != '']
            if len(cells) < 2:
                continue

            day_name = cells[0].replace('**', '').strip()
            session = cells[1].replace('**', '').strip()

            # Skip header and separator rows
            if day_name in ('Day', '---', '') or session in ('Session', '---', ''):
                continue
            if '---' in day_name:
                continue
            if day_name == 'Total' or day_name.startswith('Total'):
                continue

            # Strip date annotations like "(May 22)" from day names
            day_clean = re.sub(r'\s*\([^)]+\)', '', day_name).strip()

            km_str = cells[2].replace('**', '').strip() if len(cells) > 2 else '—'
            elev_str = cells[3].replace('**', '').strip() if len(cells) > 3 else '—'

            # Parse km
            km = None
            if km_str and km_str not in ('—', '', '—'):
                km_clean = re.sub(r'[^0-9.]', '', km_str)
                if km_clean:
                    km = float(km_clean)

            # Parse elevation
            elev = None
            if elev_str and elev_str not in ('—', '', '—'):
                elev_clean = re.sub(r'[^0-9.]', '', elev_str)
                if elev_clean:
                    elev = float(elev_clean)

            days.append({
                "day": day_clean,
                "session": session,
                "target_km": km,
                "target_elevation": elev,
            })

        # Calculate week start date
        week_start = datetime.strptime(PLAN_START, '%Y-%m-%d') + timedelta(weeks=week_num - 1)

        # Assign dates to days
        for i, day in enumerate(days):
            day_idx = next((j for j, dn in enumerate(DAY_NAMES) if day['day'].startswith(dn)), i)
            day['date'] = (week_start + timedelta(days=day_idx)).strftime('%Y-%m-%d')

        # Parse total targets from the Total row
        total_km = None
        total_elev = None
        total_match = re.search(r'\|\s*\*\*Total\*\*.*?\|\s*.*?\|\s*\*\*~?(\d+)\s*km', block)
        if total_match:
            total_km = float(total_match.group(1))
        elev_total_match = re.search(r'\|\s*\*\*Total\*\*.*?\|.*?\|.*?\|\s*\*\*~?([\d,]+)\s*m', block)
        if elev_total_match:
            total_elev = float(elev_total_match.group(1).replace(',', ''))

        # Determine phase
        phase = next((p['name'] for p in PHASES if week_num in p['weeks']), 'Unknown')

        weeks.append({
            "week_number": week_num,
            "phase": phase,
            "start_date": week_start.strftime('%Y-%m-%d'),
            "end_date": (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            "target_km": total_km,
            "target_elevation": total_elev,
            "days": days,
        })

    return weeks


def parse_exercises(plan_path):
    """Parse exercise descriptions from the plan markdown."""
    with open(plan_path, 'r') as f:
        content = f.read()

    exercises = {"morning": [], "postrun": [], "strength": []}

    # Morning routine section
    morning_match = re.search(
        r'### Daily Morning Routine.*?\n(.*?)(?=\n### )',
        content, re.DOTALL
    )
    if morning_match:
        section = morning_match.group(1)
        current_group = None
        for line in section.strip().split('\n'):
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                current_group = line.strip('*').strip()
            elif line.startswith('- '):
                text = line[2:].strip()
                # Split on em-dash to get name and description
                parts = text.split(' — ', 1)
                name = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ''
                # Extract reps/duration from description
                reps = ''
                reps_match = re.search(r'(\d+\s*(?:reps?|sec|each)\b[^.]*)', desc)
                if reps_match:
                    reps = reps_match.group(1)
                exercises["morning"].append({
                    "name": name,
                    "description": desc,
                    "reps": reps,
                    "group": current_group,
                })

    # Post-run section
    postrun_match = re.search(
        r'### Post-Run Mobility.*?\n(.*?)(?=\n### )',
        content, re.DOTALL
    )
    if postrun_match:
        for line in postrun_match.group(1).strip().split('\n'):
            line = line.strip()
            if line.startswith('- '):
                text = line[2:].strip()
                parts = text.split(' — ', 1)
                name = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ''
                reps = ''
                reps_match = re.search(r'(\d+\s*(?:reps?|sec|each)\b[^.]*)', desc)
                if reps_match:
                    reps = reps_match.group(1)
                exercises["postrun"].append({
                    "name": name,
                    "description": desc,
                    "reps": reps,
                })

    # Strength section
    strength_match = re.search(
        r'### Strength.*?\n(.*?)(?=\n---|\n## |\Z)',
        content, re.DOTALL
    )
    if strength_match:
        for line in strength_match.group(1).strip().split('\n'):
            line = line.strip()
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c != '']
            if len(cells) < 3:
                continue
            name = cells[0]
            sets_reps = cells[1]
            purpose = cells[2]
            if name in ('Exercise', '---', '') or '---' in name:
                continue
            exercises["strength"].append({
                "name": name,
                "sets_reps": sets_reps,
                "purpose": purpose,
            })

    return exercises


DIKE_TRAINING = {
    "elevation_per_rep": 13,
    "variants": [
        {
            "id": "A",
            "name": "Long Asphalt",
            "surface": "Asphalt",
            "distance_m": 250,
            "gradient_pct": 5,
            "color": "#3b82f6",
            "simulates": "Gentle trail climbs",
            "stimulus": "HR endurance, sustained climbing",
        },
        {
            "id": "B",
            "name": "Stairs + Asphalt",
            "surface": "Asphalt + stairs",
            "distance_m": 120,
            "gradient_pct": 11,
            "color": "#8b5cf6",
            "simulates": "Steep trail climbing",
            "stimulus": "Power hiking, leg strength",
        },
        {
            "id": "C",
            "name": "Steep Grass",
            "surface": "Grass",
            "distance_m": 50,
            "gradient_pct": 26,
            "color": "#10b981",
            "simulates": "Technical steep terrain + descent",
            "stimulus": "Eccentric quad strength, ankle stability",
        },
    ],
    "sessions": [
        {
            "id": "A",
            "name": "Volume Climbing",
            "variant": "A",
            "repeats": "8–12",
            "elevation": "100–160 hm",
            "description": "Steady effort up, easy jog down. Builds cardiac endurance for sustained T78 climbs.",
        },
        {
            "id": "B",
            "name": "Steep Repeats",
            "variant": "B",
            "repeats": "10–15",
            "elevation": "130–195 hm",
            "description": "Power hike up with strong arm drive. Controlled descent, focus on technique.",
        },
        {
            "id": "C",
            "name": "Downhill Focus",
            "variant": "C",
            "repeats": "6–10",
            "elevation": "80–130 hm",
            "description": "Easy uphill, progressively faster downhill. Builds eccentric quad strength for 5,000m descent.",
            "recovery_note": "Allow 10–14 days between sessions",
        },
        {
            "id": "D",
            "name": "Mix Session",
            "variant": "all",
            "repeats": "12 (4x3)",
            "elevation": "~150 hm",
            "description": "All three variants combined. Grass up + asphalt down, stairs up + grass down, asphalt up + stairs down.",
        },
    ],
    "periodization": [
        {"phase": "Base (Wk 1–4)", "focus": "A + B rotation 1x/week, C every 2 weeks"},
        {"phase": "Vertical (Wk 5–8)", "focus": "All sessions 1–2x/week, C every 10–14 days"},
        {"phase": "Mountain (Wk 9–10)", "focus": "Light session A only"},
        {"phase": "Taper (Wk 11–14)", "focus": "Session A only, no C after week 11"},
    ],
}


def query_actuals(conn, plan_start, num_weeks=14):
    """Query actual activity data aligned to plan weeks."""
    weeks = []
    start = datetime.strptime(plan_start, '%Y-%m-%d')

    for w in range(num_weeks):
        week_start = start + timedelta(weeks=w)
        week_end = week_start + timedelta(days=7)

        rows = conn.execute("""
            SELECT activity_date, activity_name, activity_type,
                   distance_m, moving_time_s, elevation_gain_m,
                   avg_heart_rate, calories, gear
            FROM activities
            WHERE activity_date >= ? AND activity_date < ?
            ORDER BY activity_date
        """, (week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d'))).fetchall()

        activities = []
        total_km = 0
        total_elev = 0
        total_hours = 0
        run_km = 0
        run_elev = 0

        for r in rows:
            dist_km = round((r[3] or 0) / 1000, 1)
            elev = round(r[5] or 0, 0)
            hours = round((r[4] or 0) / 3600, 2)
            pace = round((r[4] or 0) / 60 / max(dist_km, 0.1), 1) if r[2] in ('Run', 'TrailRun') and dist_km > 0 else None

            activities.append({
                "date": r[0][:10] if r[0] else None,
                "name": r[1],
                "type": r[2],
                "distance_km": dist_km,
                "elevation_m": elev,
                "moving_time_hours": hours,
                "avg_hr": r[6],
                "calories": r[7],
                "gear": r[8],
                "pace_min_km": pace,
            })

            total_km += dist_km
            total_elev += elev
            total_hours += hours
            if r[2] in ('Run', 'TrailRun'):
                run_km += dist_km
                run_elev += elev

        weeks.append({
            "week_number": w + 1,
            "start_date": week_start.strftime('%Y-%m-%d'),
            "end_date": (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            "total_km": round(total_km, 1),
            "run_km": round(run_km, 1),
            "total_elevation": round(total_elev, 0),
            "run_elevation": round(run_elev, 0),
            "total_hours": round(total_hours, 1),
            "activities": activities,
        })

    return weeks


def query_history(conn, weeks_back=52):
    """Query weekly volume for the last N weeks."""
    end = datetime.now()
    start = end - timedelta(weeks=weeks_back)

    rows = conn.execute("""
        SELECT
            date(activity_date, 'weekday 0', '-6 days') as week_start,
            SUM(CASE WHEN activity_type IN ('Run', 'TrailRun') THEN distance_m ELSE 0 END) as run_m,
            SUM(CASE WHEN activity_type IN ('Run', 'TrailRun') THEN elevation_gain_m ELSE 0 END) as run_elev,
            SUM(CASE WHEN activity_type IN ('Run', 'TrailRun') THEN moving_time_s ELSE 0 END) as run_time,
            SUM(distance_m) as total_m,
            SUM(elevation_gain_m) as total_elev,
            COUNT(*) as activity_count
        FROM activities
        WHERE activity_date >= ? AND activity_date <= ?
        GROUP BY week_start
        ORDER BY week_start
    """, (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))).fetchall()

    return [{
        "week_start": r[0],
        "run_km": round((r[1] or 0) / 1000, 1),
        "run_elevation": round(r[2] or 0, 0),
        "run_hours": round((r[3] or 0) / 3600, 1),
        "total_km": round((r[4] or 0) / 1000, 1),
        "total_elevation": round(r[5] or 0, 0),
        "activity_count": r[6],
    } for r in rows]


def query_daily_runs(conn, weeks_back=52):
    """Query daily run distances for heatmap."""
    end = datetime.now()
    start = end - timedelta(weeks=weeks_back)

    rows = conn.execute("""
        SELECT date(activity_date) as day,
               SUM(distance_m) / 1000.0 as km
        FROM activities
        WHERE activity_type IN ('Run', 'TrailRun')
          AND activity_date >= ? AND activity_date <= ?
        GROUP BY day
        ORDER BY day
    """, (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))).fetchall()

    return {r[0]: round(r[1], 1) for r in rows}


def query_reference_races(conn):
    """Query reference race performances for time prediction."""
    rows = conn.execute("""
        SELECT activity_date, activity_name,
               ROUND(distance_m/1000, 1) as km,
               ROUND(elevation_gain_m, 0) as elev,
               ROUND(moving_time_s/3600.0, 2) as hours,
               ROUND(elevation_gain_m / (moving_time_s/3600.0), 0) as vert_rate,
               ROUND(moving_time_s/60.0/(distance_m/1000), 2) as pace
        FROM activities
        WHERE activity_type = 'Run' AND distance_m > 40000 AND elevation_gain_m > 2000
        ORDER BY activity_date
    """).fetchall()

    return [{
        "date": r[0][:10],
        "name": r[1],
        "distance_km": r[2],
        "elevation_m": r[3],
        "time_hours": r[4],
        "vert_rate": r[5],
        "pace_min_km": r[6],
    } for r in rows]


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Parse plan
    plan_weeks = parse_plan(PLAN_PATH)
    exercises = parse_exercises(PLAN_PATH)

    # Query database
    conn = sqlite3.connect(DB_PATH)
    actual_weeks = query_actuals(conn, PLAN_START)
    history = query_history(conn)
    daily_runs = query_daily_runs(conn)
    reference_races = query_reference_races(conn)
    conn.close()

    # Build output
    data = {
        "generated_at": datetime.now().isoformat(timespec='seconds'),
        "race": {
            "name": "Swiss Iron Trail T78",
            "date": RACE_DATE,
            "distance_km": 78,
            "elevation_m": 5000,
            "cutoff_hours": 21,
            "start_time": "04:00",
            "location": "Savognin, Switzerland",
            "url": "https://www.irontrail.ch/en/races-info/runs/t78-savognin",
        },
        "events": EVENTS,
        "phases": PHASES,
        "plan_start": PLAN_START,
        "plan": plan_weeks,
        "actual": actual_weeks,
        "history": history,
        "daily_runs": daily_runs,
        "exercises": exercises,
        "dike_training": DIKE_TRAINING,
        "prediction": {
            "reference_races": reference_races,
            "scenarios": [
                {"label": "Optimistic", "hours": 13.5, "conditions": "2024-level fitness, strong execution, good weather"},
                {"label": "Target", "hours": 14.0, "conditions": "Solid prep, pacing discipline, no major issues"},
                {"label": "Realistic", "hours": 14.5, "conditions": "Some unknowns, altitude adjustment"},
                {"label": "Conservative", "hours": 15.5, "conditions": "Stiffness issues or bad weather"},
            ],
            "cutoff_hours": 21,
            "key_factors": [
                "Descending speed — 5,000m of descent is where time is won or lost",
                "Vertical endurance — sustaining 280+ m/hr climbing rate beyond hour 10",
                "Back-to-back fatigue resistance — running vertical on pre-fatigued legs",
                "Race execution — eat from km 1, hold HR 140–145, power-hike efficiently",
            ],
        },
    }

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported dashboard data to {OUTPUT_PATH}")
    print(f"  Plan: {len(plan_weeks)} weeks parsed")
    print(f"  Actual: {sum(len(w['activities']) for w in actual_weeks)} activities in plan period")
    print(f"  History: {len(history)} weeks")
    print(f"  Daily runs: {len(daily_runs)} days")
    print(f"  Exercises: {sum(len(v) for v in exercises.values())} total")


if __name__ == '__main__':
    main()
