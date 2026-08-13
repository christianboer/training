#!/usr/bin/env python3
"""Fetch photographs from Wikimedia Commons, with the credit that the licence
requires.

Why Commons and not the hotels' own websites or Strava: nearly everything in this
booklet is CC BY-SA or CC0, which means it may be *shared* as long as the
photographer and the licence travel with the picture. That is the difference
between this booklet and the walkers' routebook — the routebook embeds other
people's Strava photos and must never leave the family, this one does not have to
hide.

So `credit` is not decoration and not optional: without the artist and the licence
printed on the page, using the image is simply not permitted. Every fetch returns
them, and build.py prints them.

Files are pinned by exact title rather than found by search, because search
results drift and a booklet should rebuild the same next month.
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, 'cache', 'photos')
META_CACHE = os.path.join(BASE, 'cache', 'commons-meta.json')

API = 'https://commons.wikimedia.org/w/api.php'
UA = ('PilgrimsWayCrewbook/1.0 (personal family booklet; '
      'contact c.boer@blisdigital.com)')


def _strip_html(s):
    """Commons returns Artist as an HTML fragment — often a link to a user page."""
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(s).strip()


def _load_meta_cache():
    if os.path.exists(META_CACHE):
        try:
            return json.load(open(META_CACHE))
        except Exception:
            pass
    return {}


def _save_meta_cache(cache):
    os.makedirs(os.path.dirname(META_CACHE), exist_ok=True)
    with open(META_CACHE, 'w') as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)


def _api(params, retries=3):
    """Commons over curl: this environment's TLS proxy breaks python's urllib,
    the same reason the tile and Wikipedia fetchers shell out."""
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(retries):
        time.sleep(0.4 * (1 + attempt))
        r = subprocess.run(['curl', '-sfL', '--compressed', '--max-time', '30',
                            '-A', UA, url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError:
                continue
    return None


def info(title, width=1600):
    """Metadata + a thumbnail URL for one pinned Commons file.

    The thumbnail matters: several of these originals are enormous (one Leeds
    Castle panorama is 13,840 px wide) and a print page needs about 1,600.
    """
    cache = _load_meta_cache()
    key = f'{title}|{width}'
    if key in cache:
        return cache[key]

    d = _api({'action': 'query', 'format': 'json', 'titles': title,
              'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata',
              'iiurlwidth': width})
    if not d:
        return None
    pages = (d.get('query') or {}).get('pages') or {}
    page = next(iter(pages.values()), None)
    if not page or 'imageinfo' not in page:
        print(f'  ! commons: no such file {title}', file=sys.stderr)
        return None

    ii = page['imageinfo'][0]
    em = ii.get('extmetadata', {})

    def meta(k):
        return _strip_html((em.get(k) or {}).get('value', ''))

    out = {
        'title': page['title'],
        'url': ii.get('thumburl') or ii['url'],
        'width': ii.get('thumbwidth') or ii['width'],
        'height': ii.get('thumbheight') or ii['height'],
        'page': ii.get('descriptionurl', ''),
        'artist': meta('Artist') or 'onbekend',
        'licence': meta('LicenseShortName') or '?',
        'licence_url': (em.get('LicenseUrl') or {}).get('value', ''),
    }
    cache[key] = out
    _save_meta_cache(cache)
    return out


def fetch(title, width=1600, quiet=False):
    """-> the info dict with a local `path`, or None."""
    meta = info(title, width=width)
    if not meta:
        return None
    os.makedirs(CACHE, exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', meta['title'].replace('File:', ''))
    name = f'{name[:80]}_{width}.jpg'
    path = os.path.join(CACHE, name)
    if not (os.path.exists(path) and os.path.getsize(path) > 2000):
        ok = False
        for attempt in range(3):
            time.sleep(0.3 * (1 + attempt))
            r = subprocess.run(['curl', '-sfL', '--max-time', '60', '-A', UA,
                                '-o', path, meta['url']], capture_output=True)
            if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 2000:
                ok = True
                break
        if not ok:
            if os.path.exists(path):
                os.remove(path)
            print(f'  ! commons: download failed {meta["title"]}', file=sys.stderr)
            return None
        if not quiet:
            print(f'    {name} ({os.path.getsize(path) // 1024} KB)')
    meta['path'] = path
    return meta


def credit_line(meta):
    """'Foto: Someone (CC BY-SA 2.0)' — the minimum the licence asks for."""
    return f'Foto: {meta["artist"]} ({meta["licence"]})'


if __name__ == '__main__':
    for t in sys.argv[1:]:
        m = fetch(t)
        print(json.dumps({k: v for k, v in (m or {}).items() if k != 'url'},
                         indent=1, ensure_ascii=False))
