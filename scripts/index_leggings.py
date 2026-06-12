#!/usr/bin/env python3
"""Index leggings collection and match activity private notes to legging wears."""

import json
import re
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'training.db')
COLLECTION_JSON = os.path.expanduser(
    '~/Documents/Projects/outfits/web/src/data/collection.json'
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS leggings (
    legging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    type_slug TEXT NOT NULL,
    color_slug TEXT NOT NULL,
    type_name TEXT,
    color_name TEXT,
    full_name TEXT,
    print_description TEXT,
    primary_color TEXT,
    location TEXT
);

CREATE TABLE IF NOT EXISTS legging_wears (
    activity_id INTEGER NOT NULL,
    legging_id INTEGER NOT NULL,
    match_method TEXT,
    PRIMARY KEY (activity_id, legging_id),
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
    FOREIGN KEY (legging_id) REFERENCES leggings(legging_id)
);
"""

# Type keywords used to identify legging references in notes
TYPE_KEYWORDS = {
    'swift speed': 'swift-speed-28',
    'speed up': 'speed-up-28',
    'invigorate': 'invigorate-28',
    'wunder under': 'wunder-under-hr-28',
    'align': 'align-28',
    'fast and free': 'fast-and-free-28',
    'train times': 'train-times-25',
}

# Words to strip when normalizing note lines for matching
STRIP_WORDS = [
    'lululemon', 'seawheeze', 'high-rise', 'high rise', 'tight', 'tights',
    'full-on luxtreme', '*full-on luxtreme', 'brushed luxtreme', '*brushed luxtreme',
    'pant', 'leggings', '28"', '28"', '25"', '25"', '28\'', '25\'',
]


def import_collection(conn):
    """Import leggings from collection.json into the leggings table."""
    with open(COLLECTION_JSON) as f:
        data = json.load(f)

    leggings = [item for item in data['items'] if item['category'] == 'leggings']

    for item in leggings:
        slug = f"{item['typeSlug']}/{item['colorSlug']}"
        full_name = f"{item['brand']} {item['type']} {item['color']}"
        locations = ', '.join(item.get('locations', []))

        # ON CONFLICT UPDATE (not INSERT OR REPLACE) so legging_id stays stable
        # across runs — legging_wears rows reference it.
        conn.execute("""
            INSERT INTO leggings
            (slug, type_slug, color_slug, type_name, color_name, full_name,
             print_description, primary_color, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                type_slug=excluded.type_slug,
                color_slug=excluded.color_slug,
                type_name=excluded.type_name,
                color_name=excluded.color_name,
                full_name=excluded.full_name,
                print_description=excluded.print_description,
                primary_color=excluded.primary_color,
                location=excluded.location
        """, (
            slug,
            item['typeSlug'],
            item['colorSlug'],
            item['type'],
            item['color'],
            full_name,
            item.get('description'),
            item.get('primaryColor'),
            locations or None,
        ))

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM leggings").fetchone()[0]
    print(f"Imported {count} leggings into collection")
    return count


def normalize(text):
    """Normalize text for matching: lowercase, strip filler words."""
    t = text.lower()
    # Remove special chars but keep spaces and hyphens
    t = t.replace('"', '').replace('"', '').replace("'", '').replace('*', '')
    for word in STRIP_WORDS:
        t = t.replace(word.lower(), '')
    # Collapse whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def find_type_in_line(line_lower):
    """Find which legging type a note line refers to. Returns type_slug or None."""
    for keyword, type_slug in TYPE_KEYWORDS.items():
        if keyword in line_lower:
            return type_slug
    return None


def match_line_to_legging(line, leggings_by_type):
    """Try to match a single note line to a legging. Returns legging row or None."""
    line_lower = line.lower()
    type_slug = find_type_in_line(line_lower)
    if not type_slug:
        return None

    candidates = leggings_by_type.get(type_slug, [])
    if not candidates:
        return None

    normalized = normalize(line)

    matches = []
    for leg in candidates:
        # Check if all color slug words appear in the normalized line
        color_words = leg['color_slug'].replace('-', ' ').split()
        if all(w in normalized for w in color_words):
            matches.append(leg)

    if len(matches) == 1:
        return matches[0]

    # If multiple matches, try stricter: check color_name words
    if len(matches) > 1:
        strict = []
        for leg in matches:
            color_name_words = leg['color_name'].lower().split()
            if all(w in normalized for w in color_name_words):
                strict.append(leg)
        if len(strict) == 1:
            return strict[0]
        # Still ambiguous — pick longest color_slug match (most specific)
        if strict:
            return max(strict, key=lambda l: len(l['color_slug']))
        return max(matches, key=lambda l: len(l['color_slug']))

    return None


def match_notes(conn):
    """Match activity private notes to leggings."""
    # Load leggings grouped by type
    rows = conn.execute(
        "SELECT legging_id, slug, type_slug, color_slug, color_name, full_name FROM leggings"
    ).fetchall()
    leggings_by_type = {}
    for r in rows:
        leg = dict(zip(
            ['legging_id', 'slug', 'type_slug', 'color_slug', 'color_name', 'full_name'], r
        ))
        leggings_by_type.setdefault(leg['type_slug'], []).append(leg)

    # Get all activities with private notes
    activities = conn.execute(
        "SELECT activity_id, activity_date, private_note FROM activities "
        "WHERE private_note IS NOT NULL ORDER BY activity_date"
    ).fetchall()

    matched = 0
    unmatched = []

    for activity_id, activity_date, note in activities:
        lines = note.strip().split('\n')
        found_legging = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            leg = match_line_to_legging(line, leggings_by_type)
            if leg:
                conn.execute(
                    "INSERT OR REPLACE INTO legging_wears (activity_id, legging_id, match_method) "
                    "VALUES (?, ?, 'auto')",
                    (activity_id, leg['legging_id'])
                )
                matched += 1
                found_legging = True

        # Check if note likely references a legging but we couldn't match.
        # Skip activities that already have a (manually resolved) wear row.
        if not found_legging:
            note_lower = note.lower()
            has_type_keyword = any(kw in note_lower for kw in TYPE_KEYWORDS)
            already_resolved = conn.execute(
                "SELECT 1 FROM legging_wears WHERE activity_id = ?", (activity_id,)
            ).fetchone()
            if has_type_keyword and not already_resolved:
                unmatched.append((activity_id, activity_date, note))

    conn.commit()
    print(f"Auto-matched {matched} legging wears")

    if unmatched:
        print(f"\n--- {len(unmatched)} UNMATCHED (contain legging type keyword but no match) ---")
        for aid, adate, note in unmatched:
            # Show just the relevant line
            note_preview = note.replace('\n', ' | ')[:120]
            print(f"  {adate[:10]}  ID:{aid}  {note_preview}")

    return matched, unmatched


def print_summary(conn):
    """Print a summary of the indexed data."""
    total_leggings = conn.execute("SELECT COUNT(*) FROM leggings").fetchone()[0]
    total_wears = conn.execute("SELECT COUNT(*) FROM legging_wears").fetchone()[0]
    unique_worn = conn.execute(
        "SELECT COUNT(DISTINCT legging_id) FROM legging_wears"
    ).fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Collection: {total_leggings} leggings")
    print(f"Total wears logged: {total_wears}")
    print(f"Unique leggings worn: {unique_worn}/{total_leggings}")
    print(f"Never worn: {total_leggings - unique_worn}")

    # Most worn
    print(f"\nTop 5 most worn:")
    for row in conn.execute("""
        SELECT l.full_name, COUNT(*) as wears
        FROM legging_wears lw JOIN leggings l ON l.legging_id = lw.legging_id
        GROUP BY lw.legging_id ORDER BY wears DESC LIMIT 5
    """):
        print(f"  {row[1]:3d}x  {row[0]}")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    import_collection(conn)
    match_notes(conn)
    print_summary(conn)

    conn.close()


if __name__ == '__main__':
    main()
