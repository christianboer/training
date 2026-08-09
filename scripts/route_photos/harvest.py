"""Harvest Strava community-photo vector tiles along a stage route.

Usage: python3 harvest.py <stage.gpx> <out.json> [zoom]
Writes photos within 300 m of the route, annotated with distance-off-route
and the km position along the route where they sit.
"""
import gzip
import json
import math
import sys
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import mvt

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
TILE_URL = 'https://www.strava.com/tiles/photos/{z}/{x}/{y}'
MAX_OFFSET_M = 300


def read_route(path):
    root = ET.parse(path).getroot()
    return [(float(p.attrib['lat']), float(p.attrib['lon']))
            for p in root.findall('.//gpx:trkpt', NS)]


def haversine(a, b, c, d):
    R = 6371000
    dlat, dlon = math.radians(c - a), math.radians(d - b)
    h = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def cumulative_km(route):
    out = [0.0]
    for i in range(1, len(route)):
        out.append(out[-1] + haversine(*route[i - 1], *route[i]))
    return [d / 1000 for d in out]


def nearest_on_route(lat, lon, route, cum):
    """Perpendicular distance (m) to the route polyline + km position of the foot."""
    k = math.cos(math.radians(lat))
    px, py = lon * k, lat
    best_d, best_km = float('inf'), 0.0
    for i in range(len(route) - 1):
        ay, ax = route[i][0], route[i][1] * k
        by, bx = route[i + 1][0], route[i + 1][1] * k
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
        d = math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * 111320
        if d < best_d:
            best_d = d
            best_km = cum[i] + t * (cum[i + 1] - cum[i])
    return best_d, best_km


def tiles_for(route, z):
    n = 2 ** z
    ts = set()
    for lat, lon in route:
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.log(math.tan(math.radians(lat)) +
                              1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
        for dx in (0, 1, -1):
            for dy in (0, 1, -1):
                ts.add((x + dx, y + dy))
    return sorted(ts)


def fetch_tile(z, x, y):
    # curl, not urllib: this environment terminates TLS at a proxy whose CA
    # python's bundle doesn't carry.
    out = subprocess.run(
        ['curl', '-sS', '--compressed', '--max-time', '30',
         TILE_URL.format(z=z, x=x, y=y)],
        capture_output=True, check=True)
    data = out.stdout
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data


def main():
    gpx, out_path = sys.argv[1], sys.argv[2]
    z = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    route = read_route(gpx)
    cum = cumulative_km(route)
    ts = tiles_for(route, z)
    print(f'{gpx}: {len(route)} pts, {cum[-1]:.1f} km, {len(ts)} tiles at z{z}')

    photos = {}
    errors = 0

    def work(t):
        x, y = t
        try:
            return t, fetch_tile(z, x, y)
        except Exception as e:
            return t, e

    with ThreadPoolExecutor(max_workers=8) as ex:
        for (x, y), data in ex.map(work, ts):
            if isinstance(data, Exception):
                errors += 1
                continue
            try:
                layers = mvt.decode(data, z, x, y)
            except Exception:
                errors += 1
                continue
            for layer in layers:
                for f in layer['features']:
                    if not f['points']:
                        continue
                    lat, lon = f['points'][0]
                    p = f['props']
                    key = p.get('uuid') or p.get('full_url') or f'{lat},{lon}'
                    if key in photos:
                        continue
                    if p.get('member_count'):
                        continue  # cluster stand-in, not an individual photo
                    photos[key] = {
                        'uuid': key, 'lat': round(lat, 6), 'lon': round(lon, 6),
                        'timestamp': p.get('timestamp'),
                        'score': p.get('score'),
                        'thumb_url': p.get('thumb_url', ''),
                        'url': p.get('url', ''),
                        'full_url': p.get('full_url', ''),
                    }

    kept = []
    for ph in photos.values():
        d, km = nearest_on_route(ph['lat'], ph['lon'], route, cum)
        if d <= MAX_OFFSET_M:
            ph['offset_m'] = round(d)
            ph['route_km'] = round(km, 2)
            kept.append(ph)
    kept.sort(key=lambda p: p['route_km'])

    json.dump(kept, open(out_path, 'w'), indent=1)
    bands = [(25, 0), (50, 0), (100, 0), (300, 0)]
    print(f'  {len(photos)} unique photos in tiles, {errors} tile errors')
    for limit, _ in bands:
        print(f'  <= {limit:3d} m from route: {sum(1 for p in kept if p["offset_m"] <= limit)}')
    print(f'  written to {out_path}')


if __name__ == '__main__':
    main()
