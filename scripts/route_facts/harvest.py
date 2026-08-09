"""Find the Wikipedia articles that sit on a route.

Usage: python3 harvest.py <route.gpx> [out.json] [max_offset_m]

Samples the route every SAMPLE_M, asks Wikipedia's geosearch what is nearby,
then measures each article's real perpendicular distance to the path and keeps
what is close enough. The offset filter is ours, not the source's — that is what
turns "articles about this region" into "things you pass".

The geometry here mirrors scripts/route_photos/harvest.py; both tools are
standalone so they each carry their own copy rather than importing sideways.
"""
import json
import math
import sys
import xml.etree.ElementTree as ET

import wiki

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
SAMPLE_M = 1500       # how often along the route to ask
MAX_OFFSET_M = 250    # how far off the path an article may sit and still count


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


def sample_points(route, cum, step_m):
    pts, nxt = [], 0.0
    for i, km in enumerate(cum):
        if km * 1000 >= nxt:
            pts.append(route[i])
            nxt = km * 1000 + step_m
    return pts


def run(gpx, out_path=None, max_offset=MAX_OFFSET_M, lang='en',
        step_m=SAMPLE_M, quiet=False):
    """Collect the Wikipedia articles within `max_offset` metres of the route.

    Returns them sorted by route_km, each annotated with offset_m, route_km and
    the intro extract. Writes to out_path as well if given.
    """
    say = (lambda *a: None) if quiet else print
    route = read_route(gpx)
    if len(route) < 2:
        raise ValueError(f'{gpx}: no track points')
    cum = cumulative_km(route)
    samples = sample_points(route, cum, step_m)

    # Radius must cover the worst case: an article max_offset off the path, at
    # the midpoint between two samples. Plus a little slack.
    radius = step_m / 2 + max_offset + 200
    say(f'{gpx}: {cum[-1]:.1f} km, {len(samples)} geosearch calls '
        f'(r={radius:.0f} m, keeping <= {max_offset} m off route)')

    stubs = {}
    for n, (lat, lon) in enumerate(samples):
        for g in wiki.geosearch(lat, lon, radius, lang):
            stubs.setdefault(g['pageid'], g)
        if not quiet and (n + 1) % 10 == 0:
            say(f'  {n + 1}/{len(samples)} sampled -> {len(stubs)} articles')

    near = []
    for g in stubs.values():
        off, km = nearest_on_route(g['lat'], g['lon'], route, cum)
        if off <= max_offset:
            near.append({'pageid': g['pageid'], 'title': g['title'],
                         'lat': g['lat'], 'lon': g['lon'],
                         'offset_m': round(off), 'route_km': round(km, 2)})
    say(f'  {len(stubs)} articles nearby, {len(near)} on the route')

    detail = wiki.pages([g['pageid'] for g in near], lang) if near else {}
    for g in near:
        g.update({k: v for k, v in detail.get(g['pageid'], {}).items()
                  if k != 'title'})
    # An article without an intro extract has nothing to say — drop it
    blank = [g['title'] for g in near if not g.get('extract')]
    if blank:
        say(f'  {len(blank)} without an intro extract, dropped: '
            + ', '.join(blank[:5]))
    near = [g for g in near if g.get('extract')]
    near.sort(key=lambda g: g['route_km'])

    if out_path:
        json.dump(near, open(out_path, 'w'), indent=1, ensure_ascii=False)
        say(f'  written to {out_path}')
    return near


def main():
    run(sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else None,
        int(sys.argv[3]) if len(sys.argv) > 3 else MAX_OFFSET_M)


if __name__ == '__main__':
    main()
