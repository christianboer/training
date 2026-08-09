"""Thin harvested photos to one per bucket along the route and download them.

Usage: python3 select_download.py <photos.json> <outdir> [bucket_m] [max_offset_m]
Picks the highest-scoring photo per bucket, downloads the 768px rendition,
and writes manifest.json next to the images.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def pick(photos, bucket_m, max_offset):
    buckets = {}
    for p in photos:
        if p['offset_m'] > max_offset:
            continue
        b = int(p['route_km'] * 1000 // bucket_m)
        cur = buckets.get(b)
        # Strava's own ranking first, then proximity to the route
        key = (-(p.get('score') or 0), p['offset_m'])
        if cur is None or key < cur[0]:
            buckets[b] = (key, p)
    return [p for _, (_, p) in sorted(buckets.items())]


def download(args):
    url, path = args
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path, True, 'cached'
    r = subprocess.run(['curl', '-sS', '--max-time', '60', '-o', path, url],
                       capture_output=True)
    ok = r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0
    return path, ok, r.stderr.decode()[:120]


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    bucket_m = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    max_offset = int(sys.argv[4]) if len(sys.argv) > 4 else 25

    photos = json.load(open(src))
    sel = pick(photos, bucket_m, max_offset)
    os.makedirs(outdir, exist_ok=True)
    print(f'{len(photos)} harvested -> {len(sel)} selected '
          f'(1 per {bucket_m} m, <= {max_offset} m off route)')

    jobs = []
    for i, p in enumerate(sel):
        url = p.get('url') or p.get('full_url')
        p['file'] = f'{i:03d}_km{p["route_km"]:05.2f}.jpg'
        jobs.append((url, os.path.join(outdir, p['file'])))

    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for path, good, err in ex.map(download, jobs):
            if good:
                ok += 1
            else:
                print(f'  FAILED {os.path.basename(path)}: {err}')

    total = sum(os.path.getsize(os.path.join(outdir, p['file']))
                for p in sel if os.path.exists(os.path.join(outdir, p['file'])))
    json.dump(sel, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1)
    print(f'  downloaded {ok}/{len(sel)}, {total/1e6:.1f} MB into {outdir}')


if __name__ == '__main__':
    main()
