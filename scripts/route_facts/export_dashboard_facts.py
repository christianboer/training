"""Collect the per-stage fact files into one the dashboard can read.

Usage: python3 export_dashboard_facts.py [route-facts dir] [out.json]

Only directories named stage<number> are picked up, so scratch routes can live
under route-facts/ without leaking into the dashboard.

The text is Wikipedia's, CC BY-SA 4.0. That licence allows publishing, which is
why — unlike the route photos — this file is committed and shipped in the Docker
image. The condition is attribution: every item keeps its article link, and the
dashboard names the source and licence.
"""
import glob
import json
import os
import sys

DEFAULT_SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'route-facts')
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), '..', '..',
                           'site', 'data', 'route-facts.json')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    stages = {}
    found = sorted(glob.glob(os.path.join(src, 'stage*', 'facts.json')))
    if not found:
        print(f'  no stage facts under {src} — nothing to export')
    for path in found:
        n = os.path.basename(os.path.dirname(path)).replace('stage', '')
        if not n.isdigit():
            continue
        facts = json.load(open(path))
        stages[n] = sorted(facts, key=lambda f: f['km'])
        print(f'  stage {n}: {len(facts)} facts')

    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({
        'source': 'Wikipedia',
        'license': 'CC BY-SA 4.0',
        'note': 'Intro extracts from Wikipedia articles whose subject lies on '
                'the route. Each item links to its source article.',
        'stages': stages,
    }, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'  wrote {out} ({os.path.getsize(out)/1024:.0f} KB)')


if __name__ == '__main__':
    main()
