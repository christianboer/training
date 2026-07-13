#!/usr/bin/env python3
"""Export training data from SQLite + plan markdown to JSON for the dashboard.

Usage:
    python scripts/export_dashboard_data.py

Reads:
    - db/training.db (activity data)
    - plan/pilgrims-way-4day.md (structured training plan)

Writes:
    - site/data/training.json
"""

import json
import math
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DB_PATH = os.path.join(BASE_DIR, 'db', 'training.db')
PLAN_PATH = os.path.join(BASE_DIR, 'plan', 'pilgrims-way-4day.md')
OUTPUT_PATH = os.path.join(BASE_DIR, 'site', 'data', 'training.json')

PLAN_START = '2026-07-06'  # Week 1 Monday
RACE_DATE = '2026-09-03'   # Stage 1 of the England 4-Day

EVENTS = [
    {"date": "2026-09-03", "name": "Stage 1: Guildford → Bletchingley", "distance_km": 51.1, "elevation_m": 1213, "role": "Queen stage — longest & hilliest"},
    {"date": "2026-09-04", "name": "Stage 2: Bletchingley → Maidstone", "distance_km": 44.4, "elevation_m": 990, "role": "4-Day"},
    {"date": "2026-09-05", "name": "Stage 3: Maidstone → Charing Heath", "distance_km": 41.0, "elevation_m": 639, "role": "4-Day"},
    {"date": "2026-09-06", "name": "Stage 4: Charing Heath → Canterbury", "distance_km": 32.2, "elevation_m": 347, "role": "Victory lap into Canterbury"},
    {"date": "2026-09-27", "name": "Euromast Trappenloop", "distance_km": 0.6, "elevation_m": 100, "role": "Sharpener — 589 steps"},
    {"date": "2026-10-03", "name": "Trappenmarathon", "distance_km": 47, "elevation_m": 3090, "role": "Stair-repeat marathon"},
]

PHASES = [
    {"name": "Recovery & Rehab", "weeks": [1, 2], "color": "#ef4444"},
    {"name": "Rebuild", "weeks": [3, 4, 5], "color": "#3b82f6"},
    {"name": "Event Specific", "weeks": [6, 7], "color": "#8b5cf6"},
    {"name": "Taper & Event", "weeks": [8, 9], "color": "#f59e0b"},
    {"name": "Stair Block", "weeks": [10, 11, 12, 13], "color": "#10b981"},
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
            "description": "Steady effort up, easy jog down. Builds cardiac endurance for the rolling North Downs profile.",
        },
        {
            "id": "B",
            "name": "Steep Repeats",
            "variant": "B",
            "repeats": "10–15",
            "elevation": "130–195 hm",
            "description": "The Trappenmarathon key session: stair rhythm with strong arm drive. Controlled descent, focus on technique.",
        },
        {
            "id": "C",
            "name": "Downhill Focus",
            "variant": "C",
            "repeats": "6–10",
            "elevation": "80–130 hm",
            "description": "Easy uphill, progressively faster downhill. Builds eccentric quad strength and ankle stability. Skip until week 6 — grass camber is the re-sprain scenario.",
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
        {"phase": "Recovery/Rebuild (Wk 1–4)", "focus": "No dike work — flat, even surfaces only; rehab is the hill session"},
        {"phase": "Event Specific (Wk 5–7)", "focus": "A light in week 5, then A+B 1x/week; no C before week 6"},
        {"phase": "Taper/Event (Wk 8–10)", "focus": "None — Kent provides the hills"},
        {"phase": "Stair Block (Wk 11–13)", "focus": "Session B is the priority, 1–2x/week — Trappenmarathon prep"},
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


# The four stages of the England 4-Day (Pilgrims' Way / North Downs Way).
# GPX files are Strava route exports in plan/stages/.
STAGES = [
    {"stage": 1, "date": "2026-09-03", "name": "Guildford → Bletchingley",
     "gpx": "stage1-guildford-bletchingley.gpx", "planned_hours": 6.72,
     "start": "Guildford", "finish": "Bletchingley"},
    {"stage": 2, "date": "2026-09-04", "name": "Bletchingley → Maidstone",
     "gpx": "stage2-bletchingley-maidstone.gpx", "planned_hours": 5.72,
     "start": "Bletchingley", "finish": "Maidstone"},
    {"stage": 3, "date": "2026-09-05", "name": "Maidstone → Charing Heath",
     "gpx": "stage3-maidstone-charing-heath.gpx", "planned_hours": 5.18,
     "start": "Maidstone", "finish": "Charing Heath"},
    {"stage": 4, "date": "2026-09-06", "name": "Charing Heath → Canterbury",
     "gpx": "stage4-charing-heath-canterbury.gpx", "planned_hours": 3.95,
     "start": "Charing Heath", "finish": "Canterbury"},
]
STAGES_DIR = os.path.join(BASE_DIR, 'plan', 'stages')


def parse_gpx_profile(gpx_path, num_points=100, waypoint_defs=None):
    """Parse GPX file into a sampled elevation profile. Optional waypoint_defs
    ({name, type, idx} with idx -1 meaning last point) are anchored to
    track-point indices."""
    if not os.path.exists(gpx_path):
        print(f"  Warning: GPX not found at {gpx_path}, using fallback profile")
        return None

    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    pts = root.findall('.//gpx:trkpt', ns)

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    all_dist = [0.0]
    all_ele = []
    cum_up = [0.0]
    prev = None

    for p in pts:
        lat = float(p.attrib['lat'])
        lon = float(p.attrib['lon'])
        ele_el = p.find('gpx:ele', ns)
        ele = float(ele_el.text) if ele_el is not None else 0
        if prev:
            d = haversine(prev[0], prev[1], lat, lon)
            all_dist.append(all_dist[-1] + d)
            diff = ele - prev[2]
            cum_up.append(cum_up[-1] + (diff if diff > 0 else 0))
        all_ele.append(ele)
        prev = (lat, lon, ele)

    # Sample evenly for profile chart
    step = max(1, len(pts) // num_points)
    profile = []
    for i in range(0, len(pts), step):
        profile.append({
            "km": round(all_dist[i] / 1000, 1),
            "ele": round(all_ele[i]),
        })
    if profile[-1]["km"] != round(all_dist[-1] / 1000, 1):
        profile.append({
            "km": round(all_dist[-1] / 1000, 1),
            "ele": round(all_ele[-1]),
        })

    waypoints = []
    for wp in (waypoint_defs or []):
        idx = wp["idx"] if wp["idx"] != -1 else len(pts) - 1
        waypoints.append({
            **{k: v for k, v in wp.items() if k != "idx"},
            "km": round(all_dist[idx] / 1000, 2),
            "ele": round(all_ele[idx]),
            "cum_gain_m": round(cum_up[idx]),
        })

    for i in range(1, len(waypoints)):
        waypoints[i]["leg_km"] = round(waypoints[i]["km"] - waypoints[i - 1]["km"], 2)
        waypoints[i]["leg_gain_m"] = waypoints[i]["cum_gain_m"] - waypoints[i - 1]["cum_gain_m"]
    if waypoints:
        waypoints[0]["leg_km"] = 0
        waypoints[0]["leg_gain_m"] = 0

    return {
        "profile": profile,
        "waypoints": waypoints,
        "total_km": round(all_dist[-1] / 1000, 1),
        "total_ascent": round(cum_up[-1]),
        "min_ele": round(min(all_ele)),
        "max_ele": round(max(all_ele)),
    }


def build_stage_profiles():
    """Parse each stage GPX into an elevation profile with start/finish waypoints."""
    stages = []
    for s in STAGES:
        gpx_path = os.path.join(STAGES_DIR, s["gpx"])
        wp_defs = [
            {"name": s["start"], "type": "start", "idx": 0},
            {"name": s["finish"], "type": "finish", "idx": -1},
        ]
        profile = parse_gpx_profile(gpx_path, num_points=80, waypoint_defs=wp_defs)
        if not profile:
            continue
        stages.append({
            "stage": s["stage"],
            "date": s["date"],
            "name": s["name"],
            "planned_hours": s["planned_hours"],
            **profile,
        })
    if not stages:
        return None
    return {
        "stages": stages,
        "total_km": round(sum(s["total_km"] for s in stages), 1),
        "total_ascent": round(sum(s["total_ascent"] for s in stages)),
    }


def build_stage_plan(course_profile, carbs_per_hr=60, fluid_l_per_hr=0.5):
    """Per-stage logistics plan: planned time, pace, fuel and fluid budget."""
    if not course_profile:
        return None

    stages = []
    for s in course_profile["stages"]:
        hours = s["planned_hours"]
        h = int(hours)
        m = round((hours - h) * 60)
        pace_min = hours * 60 / s["total_km"]
        stages.append({
            "stage": s["stage"],
            "date": s["date"],
            "name": s["name"],
            "km": s["total_km"],
            "ascent_m": s["total_ascent"],
            "planned_time": f"{h}h{m:02d}",
            "planned_hours": hours,
            "pace_min_km": round(pace_min, 2),
            "carbs_g": round(hours * carbs_per_hr),
            "fluid_l": round(hours * fluid_l_per_hr, 1),
        })

    total_hours = sum(s["planned_hours"] for s in stages)
    th = int(total_hours)
    tm = round((total_hours - th) * 60)
    return {
        "targets": {
            "carbs_per_hour_g": carbs_per_hr,
            "fluid_l_per_hour": fluid_l_per_hr,
            "planned_total_time": f"{th}h{tm:02d}",
            "planned_total_hours": round(total_hours, 2),
            "hr_cap": 135,
        },
        "recovery_routine": [
            "Within 30 min of finishing: 60–80g carbs + 20g protein",
            "Legs up 20 min, then shower, then short walk before dinner",
            "500ml electrolytes through the evening",
            "Next morning: ankle rehab block + 5 min mobility before breakfast",
        ],
        "stages": stages,
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Parse plan
    plan_weeks = parse_plan(PLAN_PATH)
    exercises = parse_exercises(PLAN_PATH)

    # Query database
    conn = sqlite3.connect(DB_PATH)
    actual_weeks = query_actuals(conn, PLAN_START, num_weeks=len(plan_weeks) or 13)
    history = query_history(conn)
    daily_runs = query_daily_runs(conn)
    reference_races = query_reference_races(conn)
    conn.close()

    # Parse stage GPX profiles + build the per-stage plan
    course_profile = build_stage_profiles()
    race_plan = build_stage_plan(course_profile)

    # Calculate plan elevation target total
    plan_total_elevation = sum(w.get("target_elevation") or 0 for w in plan_weeks)
    plan_total_km = sum(w.get("target_km") or 0 for w in plan_weeks)

    # Build output
    data = {
        "generated_at": datetime.now().isoformat(timespec='seconds'),
        "race": {
            "name": "Pilgrims' Way 4-Day",
            "date": RACE_DATE,
            "end_date": "2026-09-06",
            "distance_km": 168.7,
            "elevation_m": 3189,
            "days": 4,
            "start_time": "09:00",
            "location": "Guildford → Canterbury, England",
            "second_target": {
                "name": "Trappenmarathon",
                "date": "2026-10-03",
                "distance_km": 47,
                "elevation_m": 3090,
            },
        },
        "events": EVENTS,
        "phases": PHASES,
        "plan_start": PLAN_START,
        "plan": plan_weeks,
        "actual": actual_weeks,
        "history": history,
        "daily_runs": daily_runs,
        "exercises": exercises,
        "plan_totals": {
            "target_km": plan_total_km,
            "target_elevation": plan_total_elevation,
        },
        "course_profile": course_profile,
        "race_plan": race_plan,
        "dike_training": DIKE_TRAINING,
        "prediction": {
            "reference_races": reference_races,
            "reference_4day": {
                "name": "England 4-Day 2025 (Arundel → Dymchurch)",
                "distance_km": 159.0,
                "elevation_m": 2163,
                "moving_hours": 18.2,
                "pace_min_km": 6.87,
            },
            "scenarios": [
                {"label": "Optimistic", "hours": 19.75, "conditions": "Ankle fully settled, 2025 pace holds (6:55–7:00/km)"},
                {"label": "Target", "hours": 20.5, "conditions": "Solid prep, ankle managed, walk breaks on schedule"},
                {"label": "Realistic", "hours": 21.5, "conditions": "Matches the 21h34 route estimate — extra walking on rough ground"},
                {"label": "Conservative", "hours": 23.0, "conditions": "Ankle forces walk-heavy stages — still finishes, just longer days"},
            ],
            "cutoff_hours": 26,
            "cutoff_label": "4× daylight budget",
            "key_factors": [
                "Ankle stability on uneven ground — rehab compliance in weeks 1–6 decides it",
                "Back-to-back recovery routine — eat within 30 min, legs up, sleep",
                "Stage 1 discipline — hardest stage on day 1; going out too fast taxes days 2–4",
                "Stair economy — variant B sessions in weeks 11–12 set up the Trappenmarathon",
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
