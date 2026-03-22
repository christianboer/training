#!/usr/bin/env python3
"""Sync activities from Strava MCP JSON output into SQLite.

Usage:
    python sync_strava.py <json_file>

The JSON file should contain a list of activity objects as returned by the
Strava API (via MCP get-activity-details). Each object needs at minimum:
    id, start_date, name, type, distance, moving_time

Example workflow (run by Claude during a conversation):
    1. Call Strava MCP get-all-activities with startDate after last DB entry
    2. Call get-activity-details for each activity
    3. Write results to /tmp/strava_sync.json
    4. Run: python scripts/sync_strava.py /tmp/strava_sync.json
"""

import json
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'training.db')

UPSERT = """
INSERT OR REPLACE INTO activities (
    activity_id, activity_date, activity_name, activity_type, description,
    distance_m, moving_time_s, elapsed_time_s, elevation_gain_m, elevation_loss_m,
    max_speed_mps, average_speed_mps, avg_heart_rate, max_heart_rate,
    avg_watts, max_watts, calories, avg_cadence, max_cadence, gear,
    athlete_weight_kg, avg_temperature_c, relative_effort, total_work,
    training_load, intensity, elevation_low_m, elevation_high_m, filename,
    private_note, source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def map_activity(a):
    """Map a Strava API activity object to our DB schema."""
    return (
        a.get('id'),
        a.get('start_date'),               # already ISO 8601 from API
        a.get('name'),
        a.get('type') or a.get('sport_type'),
        a.get('description'),
        a.get('distance'),                  # meters
        a.get('moving_time'),               # seconds
        a.get('elapsed_time'),              # seconds
        a.get('total_elevation_gain'),
        a.get('elev_low') and a.get('elev_high') and None,  # no direct loss from API
        a.get('max_speed'),
        a.get('average_speed'),
        a.get('average_heartrate'),
        a.get('max_heartrate'),
        a.get('average_watts'),
        a.get('max_watts'),
        a.get('calories') or a.get('kilojoules'),
        a.get('average_cadence'),
        None,                               # max_cadence not in API summary
        a.get('gear', {}).get('name') if isinstance(a.get('gear'), dict) else a.get('gear_name'),
        None,                               # athlete_weight not in API
        a.get('average_temp'),
        a.get('suffer_score'),              # relative effort
        None,                               # total_work
        None,                               # training_load
        None,                               # intensity
        a.get('elev_low'),
        a.get('elev_high'),
        None,                               # no filename from API
        a.get('private_note'),
        'strava_api',
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python sync_strava.py <json_file>")
        sys.exit(1)

    json_path = sys.argv[1]
    with open(json_path, 'r') as f:
        activities = json.load(f)

    if isinstance(activities, dict):
        activities = [activities]

    conn = sqlite3.connect(DB_PATH)

    synced = 0
    skipped = 0
    for a in activities:
        aid = a.get('id')
        if not aid:
            skipped += 1
            continue
        try:
            conn.execute(UPSERT, map_activity(a))
            synced += 1
        except Exception as e:
            print(f"Error syncing activity {aid}: {e}")
            skipped += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    print(f"Synced {synced} activities ({skipped} skipped). Total in DB: {total}")
    conn.close()


if __name__ == '__main__':
    main()
