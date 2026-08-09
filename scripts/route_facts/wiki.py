"""Thin client for the Wikipedia action API.

Two calls are all this pipeline needs: `geosearch` to find articles near a
coordinate, and `pages` to pull the intro extract, article size and categories
for the ones that survive the offset filter.

Wikimedia rate-limits anonymous callers hard (HTTP 429 with no JSON body), so
every request is paced and retried with backoff, and carries a descriptive
User-Agent as their API policy asks.
"""
import json
import subprocess
import time
import urllib.parse

# Their policy wants a UA that identifies the tool. No personal data in it.
USER_AGENT = ('route-facts/1.0 (personal GPX route annotator; '
              'https://www.mediawiki.org/wiki/API:Etiquette)')
PACE_S = 1.2      # spacing between requests — well inside the anonymous limit
MAX_TRIES = 4


def api(params, lang='en'):
    """One paced, retried API call. Returns the parsed JSON, or {} if it never came."""
    url = (f'https://{lang}.wikipedia.org/w/api.php?'
           + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2}))
    body = b''
    for attempt in range(MAX_TRIES):
        # curl, not urllib: this environment terminates TLS at a proxy whose CA
        # python's bundle doesn't carry.
        out = subprocess.run(
            ['curl', '-sS', '--compressed', '--max-time', '40',
             '-H', f'User-Agent: {USER_AGENT}', url],
            capture_output=True)
        body = out.stdout
        try:
            return json.loads(body)
        except ValueError:
            # Almost always a 429 served as plain text. Back off and try again.
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f'Wikipedia API gave no JSON after {MAX_TRIES} tries: '
                       f'{body[:160]!r}')


def geosearch(lat, lon, radius_m, lang='en', limit=200):
    """Article stubs (pageid, title, lat, lon) within radius_m of a coordinate."""
    d = api({'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lon}',
             'gsradius': min(int(radius_m), 10000), 'gslimit': limit}, lang)
    time.sleep(PACE_S)
    return d.get('query', {}).get('geosearch', [])


def pages(pageids, lang='en', sentences=2, batch=20):
    """Intro extract, size, url and categories per pageid.

    Batched at 20 because that is the cap `prop=extracts` enforces for intro
    extracts — ask for more and the surplus pages come back without one.
    """
    out = {}
    ids = list(pageids)
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        params = {
            'action': 'query', 'pageids': '|'.join(str(p) for p in chunk),
            'prop': 'extracts|info|categories',
            'exintro': 1, 'explaintext': 1, 'exsentences': sentences,
            'inprop': 'url', 'cllimit': 500, 'clshow': '!hidden',
        }
        while True:
            d = api(params, lang)
            time.sleep(PACE_S)
            for p in d.get('query', {}).get('pages', []):
                rec = out.setdefault(p['pageid'], {
                    'pageid': p['pageid'], 'title': p.get('title', ''),
                    'extract': '', 'bytes': p.get('length', 0),
                    'url': p.get('fullurl', ''), 'categories': [],
                })
                # A continuation round carries the next slice of categories only
                rec['extract'] = rec['extract'] or (p.get('extract') or '').strip()
                rec['categories'] += [c['title'] for c in p.get('categories', [])]
            cont = d.get('continue')
            if not cont:
                break
            params = {**params, **cont}
    return out
