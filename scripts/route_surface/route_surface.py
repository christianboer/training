#!/usr/bin/env python3
"""How much of a route is paved, and how much is not.

    python3 route_surface.py <route.gpx> [--out DIR]

Snaps every segment of the track onto the nearest OpenStreetMap way and reads
its `surface` tag, falling back to the road class where nobody has surveyed it.
Writes `surface.json` (the durable part: one record per segment, with the raw
tags) plus a readable `index.html`.

    --reclassify   re-bucket surface.json on disk without calling Overpass
    --max-offset   how far off the line a way may be to count (default 20 m)
    --out DIR      where to write (default route-surface/<gpx name>/)

Matching is nearest-way-to-segment, but distance alone is not enough: for
kilometres at a stretch the Pilgrims' Way runs a footpath directly alongside a
lane, and at every junction two classes of way meet inside the search radius. So
candidates whose bearing disagrees with the segment by more than BEARING_TOL are
penalised heavily — a parallel path wins over the road beside it, and a side
street does not capture the segment crossing its mouth.

Data is © OpenStreetMap contributors, under the ODbL.
"""

import argparse
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overpass
from classify import classify, PAVED, UNPAVED, UNKNOWN

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))

SOURCE = 'OpenStreetMap contributors (ODbL), via Overpass'

SAMPLE_M = 60          # polyline spacing handed to Overpass
MAX_OFFSET = 20        # metres: beyond this a way is not what we are walking on
BEARING_TOL = 30       # degrees of agreement before a candidate is penalised
BEARING_PENALTY = 40   # metres of equivalent cost for disagreeing


# --- geometry -------------------------------------------------------------

def haversine(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = (math.sin(dp / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def local_xy(lat, lon, lat0):
    """Equirectangular metres. Fine over a stage: the error over 50 km of Kent
    is centimetres, and every comparison here is local anyway."""
    return (math.radians(lon) * 6371000.0 * math.cos(math.radians(lat0)),
            math.radians(lat) * 6371000.0)


def seg_distance(p, a, b):
    """Perpendicular distance from point to segment, all in local metres."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def bearing(a, b):
    """Degrees, undirected (0-180): a footpath tagged the other way round is
    still the same footpath."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return None
    return math.degrees(math.atan2(dy, dx)) % 180.0


def bearing_delta(x, y):
    if x is None or y is None:
        return 0.0
    d = abs(x - y) % 180.0
    return min(d, 180.0 - d)


# --- the route ------------------------------------------------------------

def read_track(path):
    root = ET.parse(path).getroot()
    pts = [(float(p.attrib['lat']), float(p.attrib['lon']))
           for p in root.findall('.//gpx:trkpt', NS)]
    name = root.find('.//gpx:trk/gpx:name', NS)
    if name is None:
        name = root.find('.//gpx:metadata/gpx:name', NS)
    return pts, (name.text.strip() if name is not None and name.text else
                 os.path.splitext(os.path.basename(path))[0])


def decimate(pts, step=SAMPLE_M):
    keep = [pts[0]]
    for p in pts[1:]:
        if haversine(keep[-1], p) >= step:
            keep.append(p)
    if keep[-1] != pts[-1]:
        keep.append(pts[-1])
    return keep


# --- matching -------------------------------------------------------------

CELL = 100.0   # metres: grid cell for the candidate index

# highway=* values that are a street a pavement could belong to
ROAD_CLASSES = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
                'unclassified', 'residential', 'living_street', 'service'}


def match(pts, ways, max_offset=MAX_OFFSET):
    """-> [{from_km, to_km, len_m, way, tags}] one record per track segment.

    A bbox harvest brings back every street in the corridor, so the naive
    "test each of ~1900 track segments against every way segment" is tens of
    millions of distance computations. Way segments are therefore binned into a
    CELL-metre grid and only the nine cells around a track segment's midpoint
    are tested — the same answer, two orders of magnitude fewer sums."""
    lat0 = sum(p[0] for p in pts) / len(pts)

    # A pavement is drawn in OSM as a footway carrying the name of the street
    # it runs along, so the road names in the harvest are what tells a pavement
    # apart from a field path. Collected before matching, used below.
    road_names = {
        (el.get('tags', {}).get('name') or '').strip()
        for el in ways.values()
        if el.get('tags', {}).get('highway') in ROAD_CLASSES
        and el.get('tags', {}).get('name')}
    road_names.discard('')

    # project every way once, and index its segments by grid cell
    grid = {}
    tags_by_way = {}
    for wid, el in ways.items():
        geom = el.get('geometry') or []
        if len(geom) < 2:
            continue
        tags_by_way[wid] = el.get('tags', {})
        xy = [local_xy(g['lat'], g['lon'], lat0) for g in geom]
        for i in range(len(xy) - 1):
            a, b = xy[i], xy[i + 1]
            item = (wid, a, b, bearing(a, b))
            # every cell the segment's bounding box touches, padded by the
            # offset so a segment just outside a cell is still found from it
            x0 = int(math.floor((min(a[0], b[0]) - max_offset) / CELL))
            x1 = int(math.floor((max(a[0], b[0]) + max_offset) / CELL))
            y0 = int(math.floor((min(a[1], b[1]) - max_offset) / CELL))
            y1 = int(math.floor((max(a[1], b[1]) + max_offset) / CELL))
            for cx in range(x0, x1 + 1):
                for cy in range(y0, y1 + 1):
                    grid.setdefault((cx, cy), []).append(item)

    out = []
    cum = 0.0
    prev_xy = local_xy(pts[0][0], pts[0][1], lat0)
    for i in range(1, len(pts)):
        here_xy = local_xy(pts[i][0], pts[i][1], lat0)
        seg_len = haversine(pts[i - 1], pts[i])
        mid = ((prev_xy[0] + here_xy[0]) / 2, (prev_xy[1] + here_xy[1]) / 2)
        want = bearing(prev_xy, here_xy)

        cell = grid.get((int(math.floor(mid[0] / CELL)),
                         int(math.floor(mid[1] / CELL))), ())
        best, best_cost = None, float('inf')
        for wid, a, b, brg in cell:
            d = seg_distance(mid, a, b)
            if d > max_offset:
                continue
            cost = d
            if bearing_delta(want, brg) > BEARING_TOL:
                cost += BEARING_PENALTY
            if cost < best_cost:
                best, best_cost = (wid, tags_by_way[wid], d), cost

        rec = {'from_km': round(cum / 1000, 4),
               'to_km': round((cum + seg_len) / 1000, 4),
               'len_m': round(seg_len, 2)}
        if best:
            wid, tags, d = best
            rec['way'] = wid
            rec['off_m'] = round(d, 1)
            rec['tags'] = {k: v for k, v in tags.items()
                           if k in ('highway', 'surface', 'tracktype', 'name',
                                    'designation', 'footway')}
            name = (tags.get('name') or '').strip()
            if (tags.get('highway') in ('footway', 'path')
                    and not tags.get('surface')
                    and not tags.get('designation')
                    and name and name in road_names):
                rec['tags']['_sidewalk_of'] = name
        out.append(rec)
        cum += seg_len
        prev_xy = here_xy
    return out


# --- summary --------------------------------------------------------------

def summarise(segments, name, gpx):
    total = sum(s['len_m'] for s in segments)
    buckets = {PAVED: 0.0, UNPAVED: 0.0, UNKNOWN: 0.0}
    basis = {'tagged': 0.0, 'inferred': 0.0, 'none': 0.0}
    evidence = {}
    spans = []

    for s in segments:
        verdict, how, why = classify(s.get('tags'))
        buckets[verdict] += s['len_m']
        basis[how] += s['len_m']
        if why:
            evidence[why] = evidence.get(why, 0.0) + s['len_m']
        s['verdict'] = verdict
        # merge neighbours into readable stretches
        if spans and spans[-1]['verdict'] == verdict:
            spans[-1]['to_km'] = s['to_km']
        else:
            spans.append({'from_km': s['from_km'], 'to_km': s['to_km'],
                          'verdict': verdict})

    def pct(v):
        return round(v / total * 100, 1) if total else 0.0

    return {
        'name': name,
        'gpx': os.path.basename(gpx),
        'total_km': round(total / 1000, 2),
        'paved_km': round(buckets[PAVED] / 1000, 2),
        'unpaved_km': round(buckets[UNPAVED] / 1000, 2),
        'unknown_km': round(buckets[UNKNOWN] / 1000, 2),
        'paved_pct': pct(buckets[PAVED]),
        'unpaved_pct': pct(buckets[UNPAVED]),
        'unknown_pct': pct(buckets[UNKNOWN]),
        'tagged_pct': pct(basis['tagged']),
        'inferred_pct': pct(basis['inferred']),
        'evidence': {k: round(v / 1000, 2) for k, v in
                     sorted(evidence.items(), key=lambda kv: -kv[1])},
        # stretches of 250 m or more, so the profile is legible
        'spans': [s for s in spans if (s['to_km'] - s['from_km']) >= 0.25],
        'source': SOURCE,
    }


# --- output ---------------------------------------------------------------

def write_html(summary, out_dir):
    def bar(s):
        w = (s['to_km'] - s['from_km']) / summary['total_km'] * 100
        cls = {'verhard': 'p', 'onverhard': 'u'}.get(s['verdict'], 'x')
        return f'<i class="{cls}" style="width:{w:.3f}%"></i>'

    rows = ''.join(
        f'<tr><td>{k}</td><td class="r">{v:.2f} km</td></tr>'
        for k, v in summary['evidence'].items())

    html = f'''<!doctype html>
<meta charset="utf-8"><title>{summary['name']} — verhard of niet</title>
<style>
 body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; max-width: 900px;
        margin: 40px auto; padding: 0 20px; color: #222; }}
 h1 {{ font-size: 22px; margin-bottom: 4px; }}
 .sub {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
 .strip {{ display: flex; height: 26px; border-radius: 3px; overflow: hidden;
           margin: 18px 0 6px; }}
 .strip i {{ display: block; }}
 .p {{ background: #7a7d82; }}
 .u {{ background: #b4762f; }}
 .x {{ background: #dcdcdc; }}
 .key {{ font-size: 12px; color: #666; }}
 .key b {{ display: inline-block; width: 10px; height: 10px; margin: 0 4px 0 14px; }}
 .big {{ font-size: 34px; font-weight: 600; }}
 table {{ border-collapse: collapse; margin-top: 24px; font-size: 13px; }}
 td {{ padding: 3px 14px 3px 0; border-bottom: 1px solid #eee; }}
 .r {{ text-align: right; }}
</style>
<h1>{summary['name']}</h1>
<div class="sub">{summary['total_km']:.2f} km &middot; bron:
  {summary['source']}</div>

<div class="big">{summary['unpaved_pct']:.0f}% onverhard</div>
<div class="strip">{''.join(bar(s) for s in summary['spans'])}</div>
<div class="key">start &rarr; finish
  <b class="u"></b>onverhard {summary['unpaved_km']:.1f} km
  <b class="p"></b>verhard {summary['paved_km']:.1f} km
  <b class="x"></b>onbekend {summary['unknown_km']:.1f} km</div>

<p class="sub" style="margin-top:20px">{summary['tagged_pct']:.0f}% van de
afstand ligt op een weg met een <code>surface</code>-tag; voor
{summary['inferred_pct']:.0f}% is het afgeleid uit het wegtype.</p>

<table>{rows}</table>
'''
    path = os.path.join(out_dir, 'index.html')
    open(path, 'w').write(html)
    return path


def run(gpx, out_dir=None, max_offset=MAX_OFFSET, reclassify=False, quiet=False):
    pts, name = read_track(gpx)
    out_dir = out_dir or os.path.join(
        REPO, 'route-surface', os.path.splitext(os.path.basename(gpx))[0])
    os.makedirs(out_dir, exist_ok=True)
    seg_path = os.path.join(out_dir, 'segments.json')

    if reclassify:
        if not os.path.exists(seg_path):
            raise SystemExit(f'no segments.json in {out_dir} to reclassify')
        blob = json.load(open(seg_path))
        segments = blob['segments'] if isinstance(blob, dict) else blob
    else:
        line = decimate(pts)
        if not quiet:
            print(f'{gpx}: {len(pts)} pts, '
                  f'{sum(haversine(pts[i-1], pts[i]) for i in range(1, len(pts)))/1000:.1f} km, '
                  f'{len(line)} polyline points', flush=True)
        ways = overpass.fetch_route(line, quiet=quiet)
        if not quiet:
            print(f'  {len(ways)} ways near the route', flush=True)
        segments = match(pts, ways, max_offset=max_offset)
        json.dump({'gpx': os.path.basename(gpx),
                   'max_offset_m': max_offset,
                   'source': SOURCE,
                   'segments': segments}, open(seg_path, 'w'))

    summary = summarise(segments, name, gpx)
    json.dump(summary, open(os.path.join(out_dir, 'surface.json'), 'w'),
              indent=1, ensure_ascii=False)
    html = write_html(summary, out_dir)

    if not quiet:
        matched = sum(1 for s in segments if s.get('way'))
        print(f'  {matched}/{len(segments)} segments matched to a way')
        print(f'  onverhard {summary["unpaved_km"]:.1f} km '
              f'({summary["unpaved_pct"]:.0f}%) · '
              f'verhard {summary["paved_km"]:.1f} km '
              f'({summary["paved_pct"]:.0f}%) · '
              f'onbekend {summary["unknown_km"]:.1f} km '
              f'({summary["unknown_pct"]:.0f}%)')
        print(f'  {summary["tagged_pct"]:.0f}% tagged, '
              f'{summary["inferred_pct"]:.0f}% inferred from road class')
        print(f'  written to {out_dir}')
        print(f'\nopen {html}')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('gpx')
    ap.add_argument('--out')
    ap.add_argument('--max-offset', type=float, default=MAX_OFFSET)
    ap.add_argument('--reclassify', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    run(a.gpx, a.out, max_offset=a.max_offset, reclassify=a.reclassify,
        quiet=a.quiet)


if __name__ == '__main__':
    main()
