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


def run(photos, outdir, bucket_m=250, max_offset=25, fetch_images=True, quiet=False):
    """Thin `photos` (a list, or a path to harvest output) and write manifest.json.

    Set fetch_images=False to keep only the manifest — enough for the dashboard,
    which hot-links Strava's CDN.
    """
    say = (lambda *a: None) if quiet else print
    if isinstance(photos, str):
        photos = json.load(open(photos))
    sel = pick(photos, bucket_m, max_offset)
    os.makedirs(outdir, exist_ok=True)
    say(f'{len(photos)} harvested -> {len(sel)} selected '
        f'(1 per {bucket_m} m, <= {max_offset} m off route)')

    for i, p in enumerate(sel):
        p['file'] = f'{i:03d}_km{p["route_km"]:05.2f}.jpg'

    if fetch_images:
        jobs = [(p.get('url') or p.get('full_url'), os.path.join(outdir, p['file']))
                for p in sel]
        ok = 0
        with ThreadPoolExecutor(max_workers=6) as ex:
            for path, good, err in ex.map(download, jobs):
                if good:
                    ok += 1
                else:
                    say(f'  FAILED {os.path.basename(path)}: {err}')
        total = sum(os.path.getsize(os.path.join(outdir, p['file']))
                    for p in sel if os.path.exists(os.path.join(outdir, p['file'])))
        say(f'  downloaded {ok}/{len(sel)}, {total/1e6:.1f} MB into {outdir}')
    else:
        say('  images not downloaded (metadata only)')

    json.dump(sel, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1)
    return sel


def main():
    run(sys.argv[1], sys.argv[2],
        int(sys.argv[3]) if len(sys.argv) > 3 else 250,
        int(sys.argv[4]) if len(sys.argv) > 4 else 25)


if __name__ == '__main__':
    main()
