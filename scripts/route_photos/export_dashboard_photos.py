"""Collect the per-stage photo manifests into one file the dashboard can read.

Usage: python3 export_dashboard_photos.py [route-photos dir] [out.json]

Only metadata is exported. The dashboard links straight to Strava's CDN, so the
images themselves stay out of the repo and out of the Docker image — they are
other people's photos and we are not redistributing them.
"""
import json
import os
import sys

DEFAULT_SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'route-photos')
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), '..', '..',
                           'site', 'data', 'route-photos.json')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    stages = {}
    for n in (1, 2, 3, 4):
        manifest = os.path.join(src, f'stage{n}', 'manifest.json')
        if not os.path.exists(manifest):
            print(f'  stage {n}: no manifest, skipped')
            continue
        photos = json.load(open(manifest))
        stages[str(n)] = [{
            'km': p['route_km'],
            'off': p['offset_m'],
            'ts': int(p['timestamp']) if p.get('timestamp') else None,
            'thumb': p.get('thumb_url', ''),
            'url': p.get('url') or p.get('full_url', ''),
        } for p in sorted(photos, key=lambda x: x['route_km'])]
        print(f'  stage {n}: {len(stages[str(n)])} photos')

    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({
        'source': 'Strava community photos (public route-tile layer)',
        'note': 'Photos by other Strava users, hot-linked from Strava\'s CDN. '
                'Metadata only — no images are stored in this repo.',
        'stages': stages,
    }, open(out, 'w'), separators=(',', ':'))
    size = os.path.getsize(out)
    print(f'  wrote {out} ({size/1024:.0f} KB)')


if __name__ == '__main__':
    main()
