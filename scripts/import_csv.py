#!/usr/bin/env python3
"""Import strava/activities.csv into SQLite database."""

import csv
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'training.db')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'strava', 'activities.csv')

# The CSV has duplicate column names. We use positional indexing for the typed columns.
# Columns by position (0-indexed):
#  0: Activity ID
#  1: Activity Date          (e.g. "Jun 10, 2013, 9:21:47 AM")
#  2: Activity Name
#  3: Activity Type
#  4: Activity Description
#  5: Elapsed Time (summary)
#  6: Distance (summary, km)
#  7: Max Heart Rate (summary)
#  8: Relative Effort (summary)
#  9: Commute (summary)
# 10: Activity Private Note
# 11: Activity Gear
# 12: Filename
# 13: Athlete Weight
# 14: Bike Weight
# 15: Elapsed Time (detailed, seconds)
# 16: Moving Time (seconds)
# 17: Distance (detailed, meters)
# 18: Max Speed (m/s)
# 19: Average Speed (m/s)
# 20: Elevation Gain
# 21: Elevation Loss
# 22: Elevation Low
# 23: Elevation High
# 24: Max Grade
# 25: Average Grade
# 26: Average Positive Grade
# 27: Average Negative Grade
# 28: Max Cadence
# 29: Average Cadence
# 30: Max Heart Rate (detailed)
# 31: Average Heart Rate
# 32: Max Watts
# 33: Average Watts
# 34: Calories
# 35: Max Temperature
# 36: Average Temperature
# 37: Relative Effort (detailed)
# 38: Total Work
# ...
# 44: Type (sport type)
# 45: Start Time
# 68: Bike
# 69: Gear

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY,
    activity_date TEXT,
    activity_name TEXT,
    activity_type TEXT,
    description TEXT,
    distance_m REAL,
    moving_time_s INTEGER,
    elapsed_time_s INTEGER,
    elevation_gain_m REAL,
    elevation_loss_m REAL,
    max_speed_mps REAL,
    average_speed_mps REAL,
    avg_heart_rate REAL,
    max_heart_rate REAL,
    avg_watts REAL,
    max_watts REAL,
    calories REAL,
    avg_cadence REAL,
    max_cadence REAL,
    gear TEXT,
    athlete_weight_kg REAL,
    avg_temperature_c REAL,
    relative_effort REAL,
    total_work REAL,
    training_load REAL,
    intensity REAL,
    elevation_low_m REAL,
    elevation_high_m REAL,
    filename TEXT,
    source TEXT DEFAULT 'export'
);

CREATE INDEX IF NOT EXISTS idx_activity_date ON activities(activity_date);
CREATE INDEX IF NOT EXISTS idx_activity_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_distance ON activities(distance_m);

CREATE TABLE IF NOT EXISTS activities_raw (
    activity_id INTEGER PRIMARY KEY,
    data TEXT
);
"""

UPSERT = """
INSERT OR REPLACE INTO activities (
    activity_id, activity_date, activity_name, activity_type, description,
    distance_m, moving_time_s, elapsed_time_s, elevation_gain_m, elevation_loss_m,
    max_speed_mps, average_speed_mps, avg_heart_rate, max_heart_rate,
    avg_watts, max_watts, calories, avg_cadence, max_cadence, gear,
    athlete_weight_kg, avg_temperature_c, relative_effort, total_work,
    training_load, intensity, elevation_low_m, elevation_high_m, filename, source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def parse_date(date_str):
    """Parse 'Jun 10, 2013, 9:21:47 AM' to ISO 8601."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%b %d, %Y, %I:%M:%S %p")
        return dt.isoformat()
    except ValueError:
        return date_str


def to_float(val):
    if not val or val.strip() == '':
        return None
    try:
        return float(val.replace(',', ''))
    except (ValueError, AttributeError):
        return None


def to_int(val):
    f = to_float(val)
    return int(f) if f is not None else None


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"CSV has {len(headers)} columns")

        imported = 0
        for row in reader:
            if len(row) < 45:
                continue

            activity_id = to_int(row[0])
            if activity_id is None:
                continue

            # Store raw data as tab-separated header:value pairs
            raw_data = '\t'.join(f"{headers[i]}={row[i]}" for i in range(len(row)))
            conn.execute(
                "INSERT OR REPLACE INTO activities_raw (activity_id, data) VALUES (?, ?)",
                (activity_id, raw_data)
            )

            gear = row[69].strip() if len(row) > 69 and row[69].strip() else (
                row[11].strip() if row[11].strip() else None
            )

            conn.execute(UPSERT, (
                activity_id,
                parse_date(row[1]),
                row[2].strip() or None,       # activity_name
                row[3].strip() or None,        # activity_type
                row[4].strip() or None,        # description
                to_float(row[17]),             # distance_m (detailed)
                to_int(row[16]),               # moving_time_s
                to_int(row[15]),               # elapsed_time_s
                to_float(row[20]),             # elevation_gain_m
                to_float(row[21]),             # elevation_loss_m
                to_float(row[18]),             # max_speed_mps
                to_float(row[19]),             # average_speed_mps
                to_float(row[31]),             # avg_heart_rate
                to_float(row[30]),             # max_heart_rate
                to_float(row[33]),             # avg_watts
                to_float(row[32]),             # max_watts
                to_float(row[34]),             # calories
                to_float(row[29]),             # avg_cadence
                to_float(row[28]),             # max_cadence
                gear,                          # gear
                to_float(row[13]),             # athlete_weight_kg
                to_float(row[36]),             # avg_temperature_c
                to_float(row[37]),             # relative_effort
                to_float(row[38]),             # total_work
                to_float(row[87]) if len(row) > 87 else None,  # training_load
                to_float(row[88]) if len(row) > 88 else None,  # intensity
                to_float(row[22]),             # elevation_low_m
                to_float(row[23]),             # elevation_high_m
                row[12].strip() or None,       # filename
                'export',
            ))
            imported += 1

    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    print(f"Imported {imported} activities. Total in DB: {count}")

    # Show sample
    for row in conn.execute(
        "SELECT activity_date, activity_name, activity_type, distance_m/1000 as km "
        "FROM activities ORDER BY activity_date DESC LIMIT 3"
    ):
        print(f"  {row[0]}  {row[2]:15s}  {row[3] or 0:8.2f} km  {row[1]}")

    conn.close()


if __name__ == '__main__':
    main()
