#!/usr/bin/env python3
"""Pick the routebook's photos out of the harvested Strava manifests and fetch
just those.

`route_photos.py` can restore all 233 renditions, but a book only shows a
handful per stage, so this downloads what the layout uses and leaves the rest on
Strava's CDN — kinder to their bandwidth and it keeps the PDF small.

Selection wants two things at once: the best-scoring photos, and photos spread
along the stage rather than four views of the same hill. So the stage is cut
into as many equal bands as there are slots and the best photo in each band
wins.

These are other Strava users' photographs. They are fine in a private route book
for the crew; the PDF must stay out of git and must never be published. The
credit line on the page is not decoration.
"""
import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(BASE_DIR, '../..'))
PHOTO_DIR = os.path.join(REPO, 'route-photos')
CACHE = os.path.join(BASE_DIR, 'cache', 'photos')

UA = ('PilgrimsWayRoutebook/1.0 (personal route book; '
      'contact c.boer@blisdigital.com)')


# Vetoed by eye, by uuid prefix. Strava's own score ranks a photo's popularity,
# which says nothing about whether it is a landscape or a selfie — and a
# stranger's portrait has no place in our route book. Rejecting one here lets
# the next-best photo in that stretch of the route take the slot.
EXCLUDE = {
    'A826D6EB',   # stage 3, km 8.9 — selfie, hooded figure
}


def load_manifest(stage):
    path = os.path.join(PHOTO_DIR, f'stage{stage}', 'manifest.json')
    if not os.path.exists(path):
        return []
    m = json.load(open(path))
    return m if isinstance(m, list) else m.get('photos', m.get('items', []))


def select(stage, slots=4, min_score=None):
    """Best photo per equal band along the stage, so the set covers the day."""
    items = [p for p in load_manifest(stage)
             if p.get('url') and p['uuid'][:8] not in EXCLUDE]
    if not items:
        return []
    if min_score:
        items = [p for p in items if p.get('score', 0) >= min_score] or items

    lo = min(p['route_km'] for p in items)
    hi = max(p['route_km'] for p in items)
    span = (hi - lo) or 1.0

    picked = []
    for i in range(slots):
        a, b = lo + span * i / slots, lo + span * (i + 1) / slots
        band = [p for p in items
                if (a <= p['route_km'] < b) or (i == slots - 1 and p['route_km'] == hi)]
        if band:
            picked.append(max(band, key=lambda p: p.get('score', 0)))
    return sorted(picked, key=lambda p: p['route_km'])


def find(stage, uuid_prefix):
    """One named photo out of a stage's manifest — for the cover, which is a
    choice rather than a selection."""
    return next((p for p in load_manifest(stage)
                 if p['uuid'].startswith(uuid_prefix)), None)


def fetch(photo, stage, quiet=False, full=False):
    """Download a rendition into the local cache. -> path or None.

    `full` takes the 1536px-class rendition instead of the 576px one. Worth it
    for the cover and nowhere else: at 38 mm tall a thumbnail is already past
    what the paper can resolve, while the cover photo is the one image on the
    page big enough for its pixel count to show.
    """
    os.makedirs(CACHE, exist_ok=True)
    suffix = '_full' if full else ''
    name = (f'stage{stage}_km{photo["route_km"]:05.1f}_'
            f'{photo["uuid"][:8]}{suffix}.jpg')
    path = os.path.join(CACHE, name)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    url = photo['full_url'] if full and photo.get('full_url') else photo['url']
    for attempt in range(3):
        time.sleep(0.15 * (1 + 3 * attempt))
        r = subprocess.run(['curl', '-sfL', '--max-time', '60', '-A', UA,
                            '-o', path, url], capture_output=True)
        if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 1000:
            if not quiet:
                print(f'    {name} ({os.path.getsize(path) // 1024} KB)')
            return path
    if os.path.exists(path):
        os.remove(path)
    print(f'    ! failed {url}', file=sys.stderr)
    return None


def gather(stage, slots=4, quiet=False):
    """-> [{km, offset_m, score, path, url}] ready for the layout."""
    out = []
    for p in select(stage, slots=slots):
        path = fetch(p, stage, quiet=quiet)
        if path:
            out.append({'km': p['route_km'], 'offset_m': p.get('offset_m'),
                        'score': p.get('score'), 'path': path,
                        'lat': p['lat'], 'lon': p['lon'], 'url': p['url']})
    return out


if __name__ == '__main__':
    slots = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    total = 0
    for s in (1, 2, 3, 4):
        got = gather(s, slots=slots)
        total += len(got)
        print(f'stage {s}: {len(got)}/{slots} at km '
              f'{", ".join(str(round(g["km"], 1)) for g in got)}')
    print(f'{total} photos in {CACHE}')
