#!/usr/bin/env python3
"""Read a stage GPX into the shape the routebook needs: the track as lat/lon
with cumulative distance, plus the course POIs snapped onto it.

`export_dashboard_data.py` already parses these files, but for the elevation
profile only — it throws the coordinates away. The map needs them, so this
reads the geometry and keeps the two concerns apart.
"""
import math
import xml.etree.ElementTree as ET

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
EARTH_R = 6371000


def haversine(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return EARTH_R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_stage(path):
    """-> {name, points: [(lat, lon, ele, km)], pois: [{name, type, km, lat, lon}]}"""
    root = ET.parse(path).getroot()

    points = []
    cum = 0.0
    prev = None
    for p in root.findall('.//gpx:trkpt', NS):
        lat, lon = float(p.attrib['lat']), float(p.attrib['lon'])
        ele_el = p.find('gpx:ele', NS)
        ele = float(ele_el.text) if ele_el is not None else 0.0
        if prev:
            cum += haversine(prev[0], prev[1], lat, lon)
        points.append((lat, lon, ele, cum / 1000.0))
        prev = (lat, lon)

    # Course POIs: Strava truncates <name> to 15 chars, so prefer <cmt>, and a
    # <cmt> may hold several alternatives on separate lines.
    pois = []
    for w in root.findall('.//gpx:wpt', NS):
        wlat, wlon = float(w.attrib['lat']), float(w.attrib['lon'])
        name_el, cmt_el, type_el = (w.find('gpx:name', NS), w.find('gpx:cmt', NS),
                                    w.find('gpx:type', NS))
        label = next((el.text.strip() for el in (cmt_el, name_el)
                      if el is not None and el.text and el.text.strip()), 'Waypoint')
        label = ' / '.join(l.strip() for l in label.splitlines() if l.strip())
        wp_type = (type_el.text.strip().lower().replace(' ', '_')
                   if type_el is not None and type_el.text else 'poi')
        i = min(range(len(points)),
                key=lambda j: haversine(wlat, wlon, points[j][0], points[j][1]))
        pois.append({'name': label, 'type': wp_type, 'km': points[i][3],
                     'lat': points[i][0], 'lon': points[i][1]})

    name_el = root.find('.//gpx:trk/gpx:name', NS)
    return {
        'name': name_el.text.strip() if name_el is not None and name_el.text else '',
        'points': points,
        'pois': sorted(pois, key=lambda p: p['km']),
        'total_km': points[-1][3] if points else 0.0,
    }


def point_at_km(points, km):
    """Nearest track point to a distance along the route — used to put the
    Wikipedia facts and the photos on the map at their recorded km."""
    return min(points, key=lambda p: abs(p[3] - km))


def simplify(points, tolerance_m=25):
    """Drop points that add nothing at print scale. 1,800 track points per
    stage make an SVG path far longer than the page can resolve; at ~15 m per
    printed pixel, 25 m of detail is already invisible."""
    if len(points) < 3:
        return list(points)
    kept = [points[0]]
    for p in points[1:-1]:
        if haversine(kept[-1][0], kept[-1][1], p[0], p[1]) >= tolerance_m:
            kept.append(p)
    kept.append(points[-1])
    return kept
