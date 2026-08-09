"""Rank the harvested articles and thin them to a readable set per route.

Usage: python3 selection.py <harvest.json> <outdir> [bucket_km] [cap]

Geosearch is indiscriminate: next to a hill fort it hands you the electoral ward
and the local secondary school. Scoring here encodes what the route is actually
for — things you walk past, not the region you walk through — then one winner
per stretch of route keeps the list short.
"""
import json
import math
import os
import re
import sys

BUCKET_KM = 2.0   # at most one fact per this much route
CAP = 14          # and no more than this many per route
MIN_SCORE = 70    # a stretch with nothing interesting gets nothing, not filler

# Matched against the title and the article's categories, never the extract —
# "nature reserve" in a hill's description shouldn't demote the hill.
AREA_HINTS = (
    'national landscape', 'area of outstanding natural beauty',
    'site of special scientific interest', 'nature reserve', 'green belt',
    'electoral ward', 'civil parish', 'districts of england', 'boroughs',
    'local government', 'unparished areas',
)
DULL_HINTS = (
    'school', 'academy', 'college', 'university', 'railway station',
    'transmitting station', 'hospital', 'football club', 'cricket club',
    'business park', 'industrial estate', 'shopping centre', 'supermarket',
    'roads in', 'motorway', 'bus stations', 'power station', 'sewage',
    'landfill', 'car parks',
)
GOOD_HINTS = (
    'listed buildings', 'scheduled monuments', 'castles', 'churches',
    'hillforts', 'hill forts', 'roman ', 'archaeological', 'ruins',
    'country houses', 'manor houses', 'windmills', 'watermills', 'abbeys',
    'priories', 'monasteries', 'museums', 'monuments and memorials',
    'bridges', 'follies', 'hills of', 'viewpoints', 'pilgrim',
    'burial', 'barrows', 'battles', 'inns', 'public houses',
)
STOP = {'the', 'of', 'and', 'in', 'at', 'st', 'saint', 'church', 'hill'}


def hay(f):
    return (f['title'] + ' ' + ' '.join(f.get('categories', []))).lower()


def score(f):
    """Higher is better. Proximity dominates; notability and kind adjust."""
    s = 100.0
    s -= f['offset_m'] / 12.0                                  # on the path wins
    s += min(12.0, math.log10(max(f.get('bytes', 1), 1)) * 3)  # rough notability
    h = hay(f)
    if any(k in h for k in GOOD_HINTS):
        s += 14
    if any(k in h for k in AREA_HINTS):
        s -= 25      # a region, not a point on the route
    if any(k in h for k in DULL_HINTS):
        s -= 45
    return s


def words(title):
    return {w for w in re.findall(r"[a-z']+", title.lower()) if w not in STOP}


def dedupe(facts, km_window=0.6):
    """Drop near-duplicate articles about the same thing.

    Geosearch happily returns both "St Martha's Hill" and "St Martha's Hill and
    Colyer's Hanger"; keep whichever scored better.
    """
    kept = []
    for f in sorted(facts, key=score, reverse=True):
        fw = words(f['title'])
        clash = any(
            abs(k['route_km'] - f['route_km']) <= km_window and fw and
            len(fw & words(k['title'])) / len(fw | words(k['title'])) >= 0.4
            for k in kept)
        if not clash:
            kept.append(f)
    return kept


def pick(facts, bucket_km=BUCKET_KM, cap=CAP):
    buckets = {}
    for f in dedupe(facts):
        if score(f) < MIN_SCORE:
            continue
        b = int(f['route_km'] // bucket_km)
        if b not in buckets or score(f) > score(buckets[b]):
            buckets[b] = f
    best = sorted(buckets.values(), key=score, reverse=True)[:cap]
    return sorted(best, key=lambda f: f['route_km'])


def trim(text, max_chars=340):
    """A couple of sentences, cut on a sentence boundary rather than mid-word."""
    text = ' '.join(text.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    stop = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return (cut[:stop + 1] if stop > max_chars * 0.5 else cut.rstrip() + '…')


def run(facts, outdir, bucket_km=BUCKET_KM, cap=CAP, lang='en', quiet=False):
    """Thin `facts` (a list, or a path to harvest output) and write facts.json."""
    say = (lambda *a: None) if quiet else print
    if isinstance(facts, str):
        facts = json.load(open(facts))
    sel = pick(facts, bucket_km, cap)
    say(f'{len(facts)} on route -> {len(sel)} selected '
        f'(1 per {bucket_km} km, max {cap})')

    out = [{
        'km': f['route_km'],
        'off': f['offset_m'],
        'title': f['title'],
        'text': trim(f['extract']),
        'url': f.get('url') or
               f'https://{lang}.wikipedia.org/?curid={f["pageid"]}',
    } for f in sel]

    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, 'facts.json')
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)
    say(f'  written to {path}')
    for f in out:
        say(f'  km {f["km"]:5.1f}  {f["off"]:3d} m  {f["title"]}')
    return out


def main():
    run(sys.argv[1], sys.argv[2],
        float(sys.argv[3]) if len(sys.argv) > 3 else BUCKET_KM,
        int(sys.argv[4]) if len(sys.argv) > 4 else CAP)


if __name__ == '__main__':
    main()
