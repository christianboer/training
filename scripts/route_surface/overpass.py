#!/usr/bin/env python3
"""Fetch the OSM ways along a route from Overpass, in cached bbox chunks.

Same shape as route_facts/wiki.py, and for the same reasons: this environment's
TLS proxy breaks python's urllib, so fetches shell out to `curl`; the public
endpoints shed load hard, so requests are paced and retried.

**Few big boxes, not many small ones.** The first working version cut the
route into 4 km boxes on the theory that a light query is likelier to be
granted. That is backwards: refusals are slot contention, not query weight, so
thirteen boxes meant thirteen waits and a stage took seven minutes. The whole of
stage 3's corridor — 41 x 20 km, Maidstone included — comes back in **1.9 s** as
a single bbox. Boxes of ~13 km give four or five queries per stage, each a
second or two, which is the difference between half a minute and half an hour.

**Boxes, not `around`.** The obvious query is
`way(around:20, <every point of the track>)["highway"]` — exactly the ways we
want and nothing else. It does not work: a 629-point linestring for one 47 km
stage makes overpass-api.de answer "the server is probably too busy" (an HTML
page, not JSON) on nearly every call, because it has to test every candidate way
against every point. The same stretch as a plain bbox comes back in 1.3 s, since
bboxes are what the index is for. So we take boxes along the route and do the
20 m proximity test ourselves in `route_surface.match()`, which we were doing
anyway. It downloads streets we do not walk on; that is much cheaper than not
getting an answer.
"""

import hashlib
import json
import math
import os
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE_DIR, 'cache')

ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
]

UA = ('PilgrimsWayRouteSurface/1.0 (personal route planning; '
      'contact c.boer@blisdigital.com)')

SPAN = 0.12      # degrees: box grows to about 13 km before it is cut
MARGIN = 0.003   # degrees of padding, ~330 m — far more than the match radius
PACE = 1.0       # seconds between calls; the public instance allows 2 slots
TRIES = 12       # the public instances refuse a lot; patience is the whole game
MAX_BACKOFF = 30


def boxes(points, span=SPAN, margin=MARGIN):
    """-> [(south, west, north, east)] covering the track, boxes overlapping."""
    out = []
    lat0 = lon0 = None
    lo_la = hi_la = lo_lo = hi_lo = None
    for la, lo in points:
        if lo_la is None:
            lo_la = hi_la = la
            lo_lo = hi_lo = lo
            continue
        n_lo_la, n_hi_la = min(lo_la, la), max(hi_la, la)
        n_lo_lo, n_hi_lo = min(lo_lo, lo), max(hi_lo, lo)
        if (n_hi_la - n_lo_la) > span or (n_hi_lo - n_lo_lo) > span:
            out.append((lo_la - margin, lo_lo - margin,
                        hi_la + margin, hi_lo + margin))
            lo_la = hi_la = la      # next box starts at this point, so the
            lo_lo = hi_lo = lo      # margins make the two overlap
        else:
            lo_la, hi_la, lo_lo, hi_lo = n_lo_la, n_hi_la, n_lo_lo, n_hi_lo
    if lo_la is not None:
        out.append((lo_la - margin, lo_lo - margin,
                    hi_la + margin, hi_lo + margin))
    return out


def wait_for_slot(limit=180, quiet=False):
    """Block until overpass-api.de reports a free slot.

    Its /api/status is cheap and says exactly when the next slot frees up, which
    beats guessing with backoff: a refused query costs a full server-side
    timeout, a status check costs nothing."""
    deadline = time.time() + limit
    while time.time() < deadline:
        p = subprocess.run(['curl', '-s', '--compressed', '-A', UA,
                            '--max-time', '15',
                            'https://overpass-api.de/api/status'],
                           capture_output=True)
        txt = p.stdout.decode('utf-8', 'replace')
        if 'slots available now' in txt:
            return True
        if 'Slot available after' in txt:
            # "Slot available after: <iso>, in N seconds."
            secs = 5
            for part in txt.split('in ')[1:]:
                try:
                    secs = max(secs, min(60, int(part.split()[0]) + 2))
                    break
                except ValueError:
                    pass
            if not quiet:
                print(f'    waiting {secs}s for an overpass slot', flush=True)
            time.sleep(secs)
            continue
        return False   # unrecognised: don't spin, just try the query
    return False


def _post(query, endpoint, timeout=180):
    p = subprocess.run(
        ['curl', '-s', '--compressed', '-A', UA,
         '--max-time', str(timeout), '--data-binary', '@-', endpoint],
        input=query.encode(), capture_output=True)
    return p.stdout


def fetch_box(box, quiet=False):
    """One bbox -> list of way elements with tags + geometry. Cached by query
    hash, so a re-run is free and a part-harvested route resumes."""
    s, w, n, e = box
    query = (f'[out:json][timeout:180];\n'
             f'way["highway"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});\n'
             f'out tags geom;\n')

    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(query.encode()).hexdigest()[:16]
    path = os.path.join(CACHE, f'{key}.json')
    if os.path.exists(path):
        return json.load(open(path))['elements']

    last = ''
    for attempt in range(TRIES):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        # Ask before knocking, every time. overpass-api.de allows 2 concurrent
        # queries and refuses the third with a server-side timeout — expensive
        # for both sides. /api/status says exactly when the next slot frees, so
        # waiting for one turns a refusal into a few seconds of patience. This
        # is the single change that made a four-stage run finish; the mirrors
        # refuse for their own reasons, so the check is worth it before them too.
        wait_for_slot(quiet=quiet)
        raw = _post(query, endpoint)
        try:
            data = json.loads(raw)
        except Exception:
            # Overpass reports overload as an HTML page, not as JSON, and an
            # empty body when it drops the connection outright
            last = (raw[:200].decode('utf-8', 'replace').strip()
                    or '(empty response)')
            wait = min(MAX_BACKOFF, PACE * (2 ** attempt) * 2)
            if not quiet:
                print(f'    overpass busy ({endpoint.split("/")[2]}), '
                      f'retry in {wait:.0f}s', flush=True)
            time.sleep(wait)
            if attempt % len(ENDPOINTS) == len(ENDPOINTS) - 1:
                wait_for_slot(quiet=quiet)
            continue
        json.dump(data, open(path, 'w'))
        time.sleep(PACE)
        return data.get('elements', [])

    raise RuntimeError(f'overpass failed after {TRIES} tries: {last}')


def fetch_route(points, quiet=False):
    """-> {way_id: element}, deduped (boxes overlap, and ways cross seams)."""
    ways = {}
    bs = boxes(points)
    for i, b in enumerate(bs, 1):
        for el in fetch_box(b, quiet=quiet):
            ways[el['id']] = el
        if not quiet:
            print(f'    box {i}/{len(bs)} -> {len(ways)} ways', flush=True)
    return ways
