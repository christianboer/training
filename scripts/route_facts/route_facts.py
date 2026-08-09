#!/usr/bin/env python3
"""Find the things worth knowing about along a route, for any GPX.

    python3 route_facts.py <route.gpx>

Asks Wikipedia what sits near the line, keeps only what is genuinely on it,
ranks landmarks above regions and writes route-facts/<gpx name>/facts.json plus
a readable index.html.

    python3 route_facts.py route.gpx --max-offset 400   # cast a wider net
    python3 route_facts.py route.gpx --bucket 3 --cap 8 # fewer, further apart
    python3 route_facts.py route.gpx --lang nl          # other Wikipedia

Unlike the route photos, this output is text under CC BY-SA 4.0: it may be
committed and published, provided each item keeps its link to the article and
the licence is named. Both are done for you here and on the dashboard.
"""
import argparse
import html
import json
import os
import sys
import xml.etree.ElementTree as ET

import harvest
# Not "select" — that name belongs to the standard library, and shadowing it
# breaks subprocess.
import selection

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
CREDIT = ('Teksten uit Wikipedia, licentie CC BY-SA 4.0. '
          'Elk fragment linkt naar het bronartikel.')


def route_title(gpx_path):
    """The <metadata><name> Strava/Garmin write, falling back to the filename."""
    try:
        name = ET.parse(gpx_path).getroot().find('.//gpx:metadata/gpx:name', NS)
        if name is not None and name.text and name.text.strip():
            return name.text.strip()
    except ET.ParseError:
        pass
    return os.path.splitext(os.path.basename(gpx_path))[0]


def write_sheet(facts, outdir, title):
    """A standalone page to read the result — the dashboard has its own view."""
    cards = '\n'.join(f'''<article>
  <span class="km">km {f['km']:.1f}</span>
  <h2><a href="{html.escape(f['url'])}" target="_blank" rel="noopener">{html.escape(f['title'])}</a></h2>
  <p>{html.escape(f['text'])}</p>
  <span class="off">{f['off']} m van de route</span>
</article>''' for f in facts)

    doc = f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — wetenswaardigheden</title>
<style>
  :root {{ --bg:#0f172a; --card:#1e293b; --border:#334155; --text:#e2e8f0;
           --muted:#94a3b8; --accent:#f97316; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0 auto; max-width:880px; padding:28px 24px 60px; background:var(--bg);
         color:var(--text); font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  h1 {{ font-size:1.6rem; margin:0 0 4px; }}
  .sub {{ color:var(--muted); font-size:.9rem; margin-bottom:24px; }}
  article {{ background:var(--card); border:1px solid var(--border); border-left:3px solid var(--accent);
             border-radius:10px; padding:14px 16px; margin-bottom:14px; }}
  .km {{ font-family:ui-monospace,monospace; color:var(--accent); font-size:.8rem; }}
  h2 {{ font-size:1.05rem; margin:2px 0 6px; }}
  a {{ color:var(--text); }}
  p {{ margin:0 0 6px; }}
  .off {{ color:var(--muted); font-size:.75rem; }}
  footer {{ color:var(--muted); font-size:.8rem; margin-top:28px; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">{len(facts)} punten onderweg</div>
{cards}
<footer>{html.escape(CREDIT)}</footer>
</body></html>'''

    path = os.path.join(outdir, 'index.html')
    open(path, 'w').write(doc)
    return path


def main():
    ap = argparse.ArgumentParser(
        description='Collect Wikipedia facts about the points along a GPX route.')
    ap.add_argument('gpx', help='route GPX file')
    ap.add_argument('--out', help='output directory '
                                  '(default: route-facts/<gpx name>)')
    ap.add_argument('--title', help='heading for the overview '
                                    '(default: the route name in the GPX)')
    ap.add_argument('--max-offset', type=int, default=harvest.MAX_OFFSET_M,
                    metavar='M',
                    help=f'how far off the route an article may sit '
                         f'(default {harvest.MAX_OFFSET_M})')
    ap.add_argument('--bucket', type=float, default=selection.BUCKET_KM,
                    metavar='KM',
                    help=f'keep the best article per KM of route '
                         f'(default {selection.BUCKET_KM})')
    ap.add_argument('--cap', type=int, default=selection.CAP,
                    help=f'never keep more than this many '
                         f'(default {selection.CAP})')
    ap.add_argument('--lang', default='en',
                    help='Wikipedia language edition (default en)')
    ap.add_argument('--reselect', action='store_true',
                    help='re-rank the harvest already on disk instead of '
                         'asking Wikipedia again')
    args = ap.parse_args()

    if not os.path.exists(args.gpx):
        sys.exit(f'no such file: {args.gpx}')

    stem = os.path.splitext(os.path.basename(args.gpx))[0]
    outdir = args.out or os.path.join(REPO, 'route-facts', stem)
    title = args.title or route_title(args.gpx)

    cache = os.path.join(outdir, 'harvest.json')
    if args.reselect:
        if not os.path.exists(cache):
            sys.exit(f'nothing to re-select: {cache} does not exist')
        near = json.load(open(cache))
        print(f'{cache}: {len(near)} articles on the route (cached)')
    else:
        near = harvest.run(args.gpx, max_offset=args.max_offset, lang=args.lang)

    if not near:
        sys.exit('no Wikipedia articles found along this route')

    facts = selection.run(near, outdir, args.bucket, args.cap, args.lang)
    # The raw harvest is worth keeping: re-tuning the selection is then instant
    # and costs Wikipedia nothing.
    json.dump(near, open(cache, 'w'), indent=1, ensure_ascii=False)
    sheet = write_sheet(facts, outdir, title)
    print(f'\nopen {sheet}')


if __name__ == '__main__':
    main()
