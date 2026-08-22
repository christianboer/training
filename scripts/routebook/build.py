#!/usr/bin/env python3
"""Build the Pilgrims' Way routebook: HTML -> A4 PDF via headless Chrome.

    python3 scripts/routebook/build.py [--no-maps] [--open]

Everything on the page comes from data already in the repo:

    site/data/training.json   stage distances, ascent, planned times, aid stations
    plan/stages/*.gpx         the route geometry and the course POIs
    route-facts/stage*/       the Wikipedia snippets, with their source links
    route-photos/stage*/      the Strava community photo manifests

Output lands in `routebook/` at the repo root, which is gitignored — the photos
are other Strava users' work and the PDF is for the crew, not for publishing.

Sizes for anything drawn over a map are computed here rather than set in CSS,
because a stroke width only means something once you know how many pixels of
image are landing on how many millimetres of paper. The stylesheet owns colour;
this file owns scale.
"""
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import photos as photolib
import profile_svg
from gpxread import point_at_km, read_stage, simplify
from tiles import build_basemap, projector

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(BASE, '../..'))
OUT = os.path.join(REPO, 'routebook')

# Layout constants that the drawing code needs to know about, in millimetres.
PAGE_CONTENT_MM = 180.0        # 210 - 2 x 15mm margin
MAP_MM = PAGE_CONTENT_MM
STAGE_MAP_ASPECT = 2.0         # these stages are long and thin; so is their map
# The route is roughly four times as wide as it is tall, so a page-shaped
# overview map has to pad enormously north and south — at 1.15 it reached from
# London to the Channel and the walk became a thread in the middle. Keep the map
# the shape of the thing it shows, and give the rest of the page to the profile
# of the whole route.
OVERVIEW_ASPECT = 2.0          # same shape as the stage maps, for consistency

# Contour lines are worth a lot on a walking map, so the stage maps use
# OpenTopoMap. The overview does not: at 170 km across, contours read as noise,
# and a handful of OpenTopoMap tiles in that region are permanently broken on
# their side — the parent-tile fallback left three visibly different patches on
# the page. Standard OSM has no gaps and renders roads and towns more clearly,
# which is what a locator map is for.
STAGE_MAP_SOURCE = 'opentopomap'
OVERVIEW_SOURCE = 'osm'

# The cover photo, by stage and uuid prefix — a choice, not a ranking. This one
# is the Inglis Memorial on Colley Hill at first light, km 34.1 of stage 1, so
# the cover is a place they will actually walk past.
#
# It is printed as a band rather than full-bleed, and that is a resolution
# decision as much as a design one: Strava's largest rendition is ~1600 px, and
# a full-bleed A4 would spread that over 210 x 297 mm at about 190 dpi — soft,
# and softer still on a portrait crop of a landscape photo. At 180 mm wide the
# same file lands near 226 dpi and prints sharp.
COVER_PHOTO = (1, '8693A75D')
# The manifest timestamps this one at 19:07 local on 11 September — evening sun,
# not morning, which is what the low light and the south-westerly view over the
# Weald agree with. Worth checking rather than guessing: it would have gone to
# print as "first light".
COVER_CAPTION = 'Colley Hill in de avondzon'

MONTHS = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
          'augustus', 'september', 'oktober', 'november', 'december']
DAYS = ['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag',
        'zondag']
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}


def nl_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return f'{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}'


def whole_sentences(text, keep_at_least=0.55):
    """Cut a truncated Wikipedia extract back to its last complete sentence.

    The harvest stores extracts clipped to a length, so some end mid-word —
    "in the parishes of Guildford and Me…". In a printed book that reads as a
    mistake rather than as a summary.

    Ending on the last full sentence is the nicest outcome, but only when there
    is a sentence break late enough to keep most of the text; on a long single
    sentence it would throw away three quarters of the entry. Failing that, drop
    the dangling half-word and keep the ellipsis, which at least reads as
    deliberately abridged.
    """
    t = text.strip()
    if not t.endswith(('…', '...')):
        return t
    body = t.rstrip('…. ')
    cut = max(body.rfind('. '), body.rfind('.\n'))
    if cut > len(body) * keep_at_least:
        return body[:cut + 1]
    space = body.rfind(' ')
    return body[:space] + '…' if space > 0 else t


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def hm(hours):
    h = int(hours)
    return f'{h}u{round((hours - h) * 60):02d}'


def nl_num(x, dec=1):
    """Dutch number formatting: comma for decimals, point for thousands.

    Worth a helper rather than a `.replace()` at the call site — a blanket
    replace on a rendered row also rewrites commas inside place names."""
    s = f'{x:,.{dec}f}'
    return s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')


def pace(min_per_km):
    """Minutes per kilometre as mm:ss.

    The plan stores this as decimal minutes, and 7.31 read as a time is wrong by
    twelve seconds a kilometre — nine minutes over a stage. Nobody reading a
    route book converts decimal minutes in their head, so don't ask them to."""
    m = int(min_per_km)
    s = round((min_per_km - m) * 60)
    if s == 60:
        m, s = m + 1, 0
    return f'{m}:{s:02d}'


# --- the map overlay ------------------------------------------------------

def overlay_svg(meta, track, pins, facts, shots, mm_width=MAP_MM):
    """SVG drawn over the basemap, in image-pixel units.

    `u` is user units per printed millimetre, which is what turns a design
    decision ("the route line is 0.9 mm wide") into a number the renderer can
    use — and keeps it right whether the image came out 2400 px or 1600 px wide.
    """
    u = meta['width'] / mm_width
    pr = projector(meta)
    W, H = meta['width'], meta['height']
    o = [f'<svg class="overlay" viewBox="0 0 {W} {H}" '
         f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">']

    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (pr(p[0], p[1]) for p in track))
    o.append(f'<polyline class="track-case" points="{pts}" '
             f'stroke-width="{1.7 * u:.2f}"/>')
    o.append(f'<polyline class="track" points="{pts}" stroke-width="{0.85 * u:.2f}"/>')

    # numbered Wikipedia facts, at the article's own position — they sit a little
    # off the path, and showing that is more honest than snapping them onto it
    for f in facts:
        x, y = pr(f['lat'], f['lon'])
        o.append(f'<g class="fact"><circle cx="{x:.1f}" cy="{y:.1f}" '
                 f'r="{1.45 * u:.2f}" stroke-width="{0.18 * u:.2f}"/>'
                 f'<text x="{x:.1f}" y="{y + 0.52 * u:.1f}" '
                 f'font-size="{2.0 * u:.2f}">{f["n"]}</text></g>')

    # where each photo was taken, keyed to the letters on the facing page
    for s in shots:
        x, y = pr(s['lat'], s['lon'])
        w = 2.6 * u
        o.append(f'<g class="shot">'
                 f'<rect class="core" x="{x - w / 2:.1f}" y="{y - w / 2:.1f}" '
                 f'width="{w:.1f}" height="{w:.1f}" rx="{0.3 * u:.2f}"/>'
                 f'<rect x="{x - w / 2:.1f}" y="{y - w / 2:.1f}" width="{w:.1f}" '
                 f'height="{w:.1f}" rx="{0.3 * u:.2f}" stroke-width="{0.22 * u:.2f}"/>'
                 f'<text x="{x:.1f}" y="{y + 0.62 * u:.1f}" '
                 f'font-size="{1.85 * u:.2f}">{s["tag"]}</text></g>')

    for p in pins:
        x, y = pr(p['lat'], p['lon'])
        kind = p['kind']
        anchor, dx, dy = 'middle', 0, -2.4 * u
        if kind == 'start':
            anchor, dx, dy = 'start', 1.9 * u, 0.9 * u
        elif kind == 'finish':
            anchor, dx, dy = 'end', -1.9 * u, 0.9 * u
        o.append(f'<g class="pin {kind}">'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.5 * u:.2f}" '
                 f'stroke-width="{0.28 * u:.2f}"/>'
                 f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" '
                 f'font-size="{2.5 * u:.2f}" stroke-width="{0.55 * u:.2f}">'
                 f'{esc(p["name"])}</text></g>')

    o.append(scalebar_svg(meta, u))
    o.append(north_svg(meta, u))
    o.append('</svg>')
    return '\n'.join(o)


def scalebar_svg(meta, u):
    """A real scale bar. Metres per pixel comes from the projection, so it stays
    true whatever zoom the stitcher picked."""
    lat = (meta['bounds']['north'] + meta['bounds']['south']) / 2
    m_per_px = 40075016.686 * math.cos(math.radians(lat)) / meta['scale']
    for km in (10, 5, 2, 1):
        px = km * 1000 / m_per_px
        if px < meta['width'] * 0.26:
            break
    x0, y0 = 3.2 * u, meta['height'] - 4.6 * u
    t = 0.9 * u
    return (f'<g class="scalebar" stroke-width="{0.22 * u:.2f}">'
            f'<path d="M{x0:.1f},{y0 - t:.1f} V{y0:.1f} H{x0 + px:.1f} '
            f'V{y0 - t:.1f}"/>'
            f'<line x1="{x0 + px / 2:.1f}" y1="{y0:.1f}" '
            f'x2="{x0 + px / 2:.1f}" y2="{y0 - t * 0.55:.1f}"/>'
            f'<text x="{x0:.1f}" y="{y0 + 2.4 * u:.1f}" font-size="{2.1 * u:.2f}" '
            f'stroke-width="{0.5 * u:.2f}">0</text>'
            f'<text x="{x0 + px:.1f}" y="{y0 + 2.4 * u:.1f}" '
            f'font-size="{2.1 * u:.2f}" stroke-width="{0.5 * u:.2f}" '
            f'text-anchor="middle">{km} km</text></g>')


def north_svg(meta, u):
    x, y = meta['width'] - 4.4 * u, 4.2 * u
    s = 1.5 * u
    return (f'<g class="north">'
            f'<path d="M{x:.1f},{y - s * 1.5:.1f} L{x + s * 0.72:.1f},{y + s:.1f} '
            f'L{x:.1f},{y + s * 0.45:.1f} L{x - s * 0.72:.1f},{y + s:.1f} Z"/>'
            f'<text x="{x:.1f}" y="{y + s * 3.1:.1f}" font-size="{2.1 * u:.2f}" '
            f'stroke-width="{0.5 * u:.2f}">N</text></g>')


ACORN = ('<svg class="acorn" width="26" height="26" viewBox="0 0 24 24" '
         'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
         '<path d="M12 2.6v2.4" stroke="#b4472e" stroke-width="1.5" '
         'stroke-linecap="round" fill="none"/>'
         '<path d="M5.4 6.2h13.2a1 1 0 0 1 0 3.2H5.4a1 1 0 0 1 0-3.2z" '
         'fill="#b4472e"/>'
         '<path d="M6.6 10.2h10.8c0 5.4-2.2 10.4-5.4 10.4S6.6 15.6 6.6 10.2z" '
         'fill="none" stroke="#b4472e" stroke-width="1.5"/></svg>')


# --- data ----------------------------------------------------------------

def load_facts(stage):
    path = os.path.join(REPO, 'route-facts', f'stage{stage}', 'facts.json')
    if not os.path.exists(path):
        return []
    d = json.load(open(path))
    return d if isinstance(d, list) else d.get('facts', [])


def load_harvest(stage):
    path = os.path.join(REPO, 'route-facts', f'stage{stage}', 'harvest.json')
    if not os.path.exists(path):
        return []
    d = json.load(open(path))
    return d if isinstance(d, list) else d.get('articles', d.get('items', []))


# Canterbury Cathedral is the whole point of the walk and the route ends 372 m
# short of it, so the ranking in selection.py — which rewards proximity — never
# picks it. Pinning it here is a judgement about what the book is about, and the
# right place for that judgement is the book, not the general-purpose selector.
PINNED = {4: 'Canterbury Cathedral'}

# Wikipedia's geosearch is indifferent to whether a thing is interesting. A
# stadium and a power station are on the route but nobody wants to read about
# them over dinner.
FACT_BLOCKLIST = {'Kingsmead Stadium', 'Canterbury power station',
                  # both two sentences of pure designation - a 0.7 ha and a
                  # 4 ha geological SSSI, on stage 3 since the Aug 22 re-route
                  'Houlder and Monarch Hill Pits, Upper Halling',
                  'Lenham Quarry'}

FACT_CAP = 8      # what fits the facing page without crowding the photos


def thin_facts(facts, cap=FACT_CAP):
    """Keep `cap` facts spread along the stage rather than the first `cap`.

    facts.json is ordered by kilometre, so a plain slice would throw away the
    entire back half of the day — on stage 1 everything past km 30, finish
    included. Same banding as the photo picker: cut the stage into `cap` bands
    and keep one from each, preferring the longer articles as a rough stand-in
    for "worth reading"."""
    if len(facts) <= cap:
        return facts
    lo = min(f['km'] for f in facts)
    hi = max(f['km'] for f in facts)
    span = (hi - lo) or 1.0
    kept, used = [], set()
    for i in range(cap):
        a, b = lo + span * i / cap, lo + span * (i + 1) / cap
        band = [f for f in facts if id(f) not in used
                and (a <= f['km'] < b or (i == cap - 1 and f['km'] == hi))]
        if band:
            pick = max(band, key=lambda f: len(f.get('text', '')))
            used.add(id(pick))
            kept.append(pick)
    # bands can come up empty on a clustered stage; top up with the best of the rest
    if len(kept) < cap:
        rest = sorted((f for f in facts if id(f) not in used),
                      key=lambda f: len(f.get('text', '')), reverse=True)
        kept.extend(rest[:cap - len(kept)])
    return sorted(kept, key=lambda f: f['km'])


def collect(no_maps=False):
    data = json.load(open(os.path.join(REPO, 'site/data/training.json')))
    plans = {s['stage']: s for s in data['race_plan']['stages']}
    profiles = {s['stage']: s for s in data['course_profile']['stages']}

    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'photos'), exist_ok=True)

    stages = []
    for n in (1, 2, 3, 4):
        gpx = glob.glob(os.path.join(REPO, f'plan/stages/stage{n}-*.gpx'))[0]
        geo = read_stage(gpx)
        plan, prof = plans[n], profiles[n]

        facts = thin_facts([f for f in load_facts(n)
                            if f['title'] not in FACT_BLOCKLIST])
        harvest = {a['title']: a for a in load_harvest(n)}
        for i, f in enumerate(facts, 1):
            f['n'] = i
            a = harvest.get(f['title'])
            if a:
                f['lat'], f['lon'] = a['lat'], a['lon']
            else:                                   # place it on the path instead
                p = point_at_km(geo['points'], f['km'])
                f['lat'], f['lon'] = p[0], p[1]

        pinned = None
        if n in PINNED:
            a = harvest.get(PINNED[n])
            if a:
                pinned = a
            else:
                print(f'  ! pinned article "{PINNED[n]}" not in stage {n} harvest',
                      file=sys.stderr)

        shots = photolib.gather(n, slots=4, quiet=True)
        for i, s in enumerate(shots):
            s['tag'] = 'ABCD'[i]
            dest = os.path.join(OUT, 'photos', os.path.basename(s['path']))
            shutil.copyfile(s['path'], dest)
            s['rel'] = f'photos/{os.path.basename(s["path"])}'

        map_rel = f'maps/stage{n}.jpg'
        map_abs = os.path.join(OUT, map_rel)
        meta_path = os.path.splitext(map_abs)[0] + '.json'
        if no_maps and os.path.exists(meta_path):
            meta = json.load(open(meta_path))
        else:
            meta = build_basemap([(p[0], p[1]) for p in geo['points']], map_abs,
                                 aspect=STAGE_MAP_ASPECT, target_px=2400,
                                 source=STAGE_MAP_SOURCE)

        pins = [{'kind': 'start', 'name': plan['name'].split('→')[0].strip(),
                 'lat': geo['points'][0][0], 'lon': geo['points'][0][1]},
                {'kind': 'finish', 'name': plan['name'].split('→')[-1].strip(),
                 'lat': geo['points'][-1][0], 'lon': geo['points'][-1][1]}]
        for poi in geo['pois']:
            pins.insert(1, {'kind': 'aid', 'name': poi['name'],
                            'lat': poi['lat'], 'lon': poi['lon']})

        stages.append({
            'n': n, 'plan': plan, 'prof': prof, 'geo': geo, 'facts': facts,
            'pinned': pinned, 'shots': shots, 'meta': meta, 'map_rel': map_rel,
            'pins': pins,
            'track': simplify(geo['points'], 25),
        })

    # overview: all four stages on one map
    ov_rel = 'maps/overview.jpg'
    ov_abs = os.path.join(OUT, ov_rel)
    ov_meta_path = os.path.splitext(ov_abs)[0] + '.json'
    all_coords = [(p[0], p[1]) for s in stages for p in s['geo']['points']]
    if no_maps and os.path.exists(ov_meta_path):
        ov_meta = json.load(open(ov_meta_path))
    else:
        ov_meta = build_basemap(all_coords, ov_abs, aspect=OVERVIEW_ASPECT,
                                target_px=2200, pad=0.05,
                                source=OVERVIEW_SOURCE)

    # the cover photo: a named choice, fetched at the largest rendition
    cst, cuuid = COVER_PHOTO
    cp = photolib.find(cst, cuuid)
    cover = None
    if cp:
        path = photolib.fetch(cp, cst, quiet=True, full=True)
        if path:
            dest = os.path.join(OUT, 'photos', os.path.basename(path))
            shutil.copyfile(path, dest)
            cover = {'rel': f'photos/{os.path.basename(path)}', 'km': cp['route_km'],
                     'stage': cst}
    if not cover:
        print(f'  ! cover photo {cuuid} not found on stage {cst}', file=sys.stderr)
        cover = stages[0]['shots'][0]
        cover.setdefault('km', 0)

    return data, stages, {'meta': ov_meta, 'rel': ov_rel}, cover


# --- pages ---------------------------------------------------------------

def totals(stages):
    return {
        'km': sum(s['plan']['km'] for s in stages),
        'asc': sum(s['plan']['ascent_m'] for s in stages),
        'hours': sum(s['plan']['planned_hours'] for s in stages),
    }


def page_cover(stages, cover):
    t = totals(stages)
    return f'''
<section class="page cover">
  <div class="eyebrow">Routeboek</div>
  <figure class="hero">
    <img src="{cover['rel']}" alt="">
    <figcaption>{esc(COVER_CAPTION)} &middot; etappe {ROMAN[cover['stage']]}, km
      {nl_num(cover['km'])} &middot; foto: Strava-community</figcaption>
  </figure>
  <div class="acorn">{ACORN}</div>
  <h1>Pilgrims&rsquo;&nbsp;Way<em>Guildford &rarr; Canterbury</em></h1>
  <div class="hair"></div>
  <div class="meta">
    <strong>3 &ndash; 6 september 2026</strong><br>
    {nl_num(t['km'])} km &middot; {nl_num(t['asc'], 0)} hoogtemeters &middot; vier dagen
  </div>
</section>'''


def whole_route_profile(stages):
    """The four stages laid end to end as one 170 km profile.

    Each stage's profile restarts at km 0, so they are offset by the running
    total. Bands and the roman numerals mark where one day ends and the next
    begins — which is the point: it puts each day's climbing next to the others
    on one axis, which four separate charts on four separate pages cannot do.
    """
    prof, bands, wpts = [], [], []
    offset = 0.0
    for s in stages:
        pr = s['prof']
        prof += [{'km': offset + p['km'], 'ele': p['ele']} for p in pr['profile']]
        bands.append({'from_km': offset, 'to_km': offset + pr['total_km'],
                      'label': ROMAN[s['n']]})
        if s['n'] == 1:
            first = pr['waypoints'][0]
            wpts.append({'name': first['name'], 'type': 'start', 'km': 0.0,
                         'ele': first['ele']})
        last = pr['waypoints'][-1]
        offset += pr['total_km']
        wpts.append({'name': last['name'],
                     'type': 'finish' if s['n'] == 4 else 'aid_station',
                     'km': offset, 'ele': last['ele']})

    return profile_svg.render(prof, wpts, bands=bands,
                              x_domain=(0, math.ceil(offset / 10) * 10),
                              width=1000, height=290)


def page_overview(stages, ov, folio):
    """The whole walk on one map, above the whole walk in profile."""
    t = totals(stages)
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Overzicht &middot; vier etappes</div>
    <h2>{nl_num(t['km'])} kilometer over de North Downs</h2>
    <div class="sub">De Pilgrims&rsquo; Way: het oude pelgrimspad naar het graf van
      Thomas Becket in Canterbury.</div>
  </div>
  <div class="mapbox" style="margin-top:5mm">
    <img src="{ov['rel']}" alt="Overzichtskaart">
    {overlay_multi(ov['meta'], stages)}
    <div class="attrib">{esc(ov['meta']['attribution'])}</div>
  </div>
  <div class="legend">
    <div><svg width="22" height="8"><line x1="1" y1="4" x2="21" y2="4" stroke="#b4472e" stroke-width="3" stroke-linecap="round"/></svg> Route</div>
    <div><svg width="10" height="10"><circle cx="5" cy="5" r="4" fill="#3f5c3a"/></svg> Start</div>
    <div><svg width="10" height="10"><circle cx="5" cy="5" r="4" fill="#2f6c8c"/></svg> Overnachting</div>
    <div><svg width="10" height="10"><circle cx="5" cy="5" r="4" fill="#23201b"/></svg> Canterbury</div>
  </div>
  <div class="rule" style="margin-top:5mm"></div>
  <div class="label">De hele tocht in profiel &middot; {nl_num(t['km'])} km, {nl_num(t['asc'], 0)} hoogtemeters</div>
  <div class="profilebox whole">
    {whole_route_profile(stages)}
    <div class="axis-note"><span>Hoogte in meters &middot; afstand in kilometers vanaf Guildford</span>
      <span>I &ndash; IV: de vier dagen</span></div>
  </div>
  <div class="folio left">{folio}</div>
</section>'''


def ascent_note(stages):
    """Say where the climbing figures come from, per stage, from the data.

    Only the stages that actually differ get named. Hardcoding "we follow
    Strava" would be wrong for three of the four — and this is a claim printed
    and handed to the family, so let it read itself off `ascent_source` instead
    of off memory."""
    odd = [s for s in stages if s['prof'].get('total_ascent_gpx')]
    if not odd:
        return ('<p>De hoogtemeters komen uit de GPX-bestanden van de etappes.</p>')
    which = ' en '.join(f'etappe&nbsp;{ROMAN[s["n"]]}' for s in odd)
    detail = '; '.join(
        f'{nl_num(s["prof"]["total_ascent"], 0)} hm tegen '
        f'{nl_num(s["prof"]["total_ascent_gpx"], 0)} in de GPX' for s in odd)
    return (f'<p>De hoogtemeters komen uit de GPX van elke etappe, behalve bij '
            f'{which}: die route bestaat ook op Strava en daar staat {detail}. '
            f'De planning is op het Strava-cijfer gemaakt, dus dat houden we aan '
            f'&mdash; beter &eacute;&eacute;n basis dan de mooiste.</p>')


def page_itinerary(stages, folio):
    rows = []
    for s in stages:
        p = s['plan']
        aid = ', '.join(a['name'] for a in p.get('aid_stations', [])) or '&mdash;'
        rows.append(f'''<tr>
          <td class="num">{ROMAN[s['n']]}</td>
          <td class="name">{esc(p['name'])}<span class="day">{nl_date(p['date'])}</span></td>
          <td>{nl_num(p['km'])}</td><td>{nl_num(p['ascent_m'], 0)}</td>
          <td>{p['planned_time'].replace('h', 'u')}</td>
          <td class="name" style="font-size:8.2pt">{esc(aid)}</td></tr>''')
    t = totals(stages)
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">De vier dagen</div>
    <h2>Wat er elke dag te doen staat</h2>
  </div>
  <table class="days">
    <thead><tr><th></th><th class="name">Etappe</th><th>km</th><th>hm</th>
      <th>gepland</th><th class="name">Hulppost</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
    <tfoot><tr><td></td><td class="name">Totaal</td>
      <td>{nl_num(t['km'])}</td><td>{nl_num(t['asc'], 0)}</td>
      <td>{hm(t['hours'])}</td><td></td></tr></tfoot>
  </table>
  <div class="rule"></div>
  <div class="prose">
    <p><strong>Hoe je dit boekje leest.</strong> Elke etappe heeft twee
    pagina&rsquo;s naast elkaar: links de kaart, het hoogteprofiel en de cijfers van
    de dag, rechts de foto&rsquo;s en de wetenswaardigheden. De genummerde bolletjes
    op de kaart komen terug bij de verhaaltjes op de rechterpagina; de letters
    <strong>A&ndash;D</strong> wijzen naar de foto&rsquo;s en staan op de plek waar
    ze gemaakt zijn.</p>
    <p>Kaart en profiel staan bij alle vier de etappes op <strong>dezelfde
    schaal</strong> &mdash; 0 tot 250 meter hoogte, 0 tot 45 kilometer &mdash;
    zodat je in &eacute;&eacute;n oogopslag ziet dat dag&nbsp;3 vlak is en
    dag&nbsp;4 kort.</p>
    {ascent_note(stages)}
  </div>
  <div class="folio right">{folio}</div>
</section>'''


def overlay_multi(meta, stages, mm_width=MAP_MM):
    """The overview map: four tracks, and a pin at each overnight stop."""
    u = meta['width'] / mm_width
    pr = projector(meta)
    o = [f'<svg class="overlay" viewBox="0 0 {meta["width"]} {meta["height"]}" '
         f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">']
    for s in stages:
        pts = ' '.join(f'{x:.1f},{y:.1f}'
                       for x, y in (pr(p[0], p[1]) for p in simplify(s['geo']['points'], 60)))
        o.append(f'<polyline class="track-case" points="{pts}" '
                 f'stroke-width="{1.5 * u:.2f}"/>')
    for s in stages:
        pts = ' '.join(f'{x:.1f},{y:.1f}'
                       for x, y in (pr(p[0], p[1]) for p in simplify(s['geo']['points'], 60)))
        o.append(f'<polyline class="track" points="{pts}" stroke-width="{0.8 * u:.2f}"/>')

    stops = [(stages[0]['plan']['name'].split('→')[0].strip(),
              stages[0]['geo']['points'][0], 'start')]
    for s in stages:
        stops.append((s['plan']['name'].split('→')[-1].strip(),
                      s['geo']['points'][-1],
                      'finish' if s['n'] == 4 else 'aid'))
    for name, p, kind in stops:
        x, y = pr(p[0], p[1])
        o.append(f'<g class="pin {kind}"><circle cx="{x:.1f}" cy="{y:.1f}" '
                 f'r="{1.5 * u:.2f}" stroke-width="{0.28 * u:.2f}"/>'
                 f'<text x="{x:.1f}" y="{y - 2.4 * u:.1f}" text-anchor="middle" '
                 f'font-size="{2.6 * u:.2f}" stroke-width="{0.6 * u:.2f}">'
                 f'{esc(name)}</text></g>')
    o.append(scalebar_svg(meta, u))
    o.append(north_svg(meta, u))
    o.append('</svg>')
    return '\n'.join(o)


def page_stage_left(s, folio):
    p, pr_, meta = s['plan'], s['prof'], s['meta']
    legs = pr_['waypoints']
    leg_rows = ''.join(
        f'<tr><td>{esc(w["name"])}</td><td>{nl_num(w["km"])}</td>'
        f'<td>{nl_num(w["leg_km"])}</td><td>{nl_num(w["leg_gain_m"], 0)}</td></tr>'
        for w in legs)

    prof = profile_svg.render(
        pr_['profile'], pr_['waypoints'],
        markers=[{'km': f['km'], 'label': str(f['n'])} for f in s['facts']])

    carry = p.get('longest_carry_km')
    # the paved/unpaved split is optional: it needs an OSM harvest
    # (scripts/route_surface/), so the band falls back to five cells without it
    surf = pr_.get('surface') or {}
    surf_cell = ('<div><span class="label">Onverhard</span>'
                 f'<span class="v">{nl_num(surf["unpaved_pct"], 0)}'
                 '<small> %</small></span></div>') if surf else ''
    return f'''
<section class="page">
  <div class="stage-head">
    <div class="numeral">{ROMAN[s['n']]}</div>
    <div class="who">
      <div class="date">{nl_date(p['date'])}</div>
      <h2>{esc(p['name'])}</h2>
      <div class="role">{esc(STAGE_NOTE[s['n']])}</div>
    </div>
  </div>
  <div class="stats">
    <div><span class="label">Afstand</span><span class="v">{nl_num(p['km'])}<small> km</small></span></div>
    <div><span class="label">Klimmen</span><span class="v">{nl_num(p['ascent_m'], 0)}<small> hm</small></span></div>
    <div><span class="label">Gepland</span><span class="v">{p['planned_time'].replace('h', 'u')}</span></div>
    <div><span class="label">Tempo</span><span class="v">{pace(p['pace_min_km'])}<small> min/km</small></span></div>
    <div><span class="label">Hoogste punt</span><span class="v">{pr_['max_ele']}<small> m</small></span></div>
    {surf_cell}
  </div>
  <div class="mapbox">
    <img src="{s['map_rel']}" alt="Kaart etappe {s['n']}">
    {overlay_svg(meta, s['track'], s['pins'], s['facts'], s['shots'])}
    <div class="attrib">{esc(meta['attribution'])}</div>
  </div>
  <div class="profilebox">
    {prof}
    <div class="axis-note"><span>Hoogte in meters &middot; afstand in kilometers</span>
      <span>Zelfde schaal op elke etappe</span></div>
  </div>
  <div class="twocol">
    <table class="mini">
      <caption>Onderweg</caption>
      <thead><tr><th>Punt</th><th>bij km</th><th>leg</th><th>hm</th></tr></thead>
      <tbody>{leg_rows}</tbody>
    </table>
    <div class="notebox">
      <span class="label">Voeding &amp; water</span>
      <strong>{nl_num(p['carbs_g'], 0)} g</strong> koolhydraten en
      <strong>{nl_num(p['fluid_l'])} L</strong>
      vocht over de dag, gerekend op 60&nbsp;g en 0,5&nbsp;L per uur.
      {f"Langste stuk zonder bijvullen: <strong>{nl_num(carry)} km</strong>." if carry else ""}
    </div>
  </div>
  <div class="folio left">{folio}</div>
</section>'''


STAGE_NOTE = {
    1: 'De North Downs op: van de Wey bij Guildford over St Martha’s Hill '
       'en Newlands Corner naar de rand van Surrey.',
    2: 'Door de Kentse heuvels langs Ide Hill, met het hoogste punt van de '
       'hele tocht onderweg.',
    3: 'De langste dag: langs de Coldrum Stones, de Medway over bij Halling '
       'en dan de hele dag over de kam — Bluebell Hill, Detling, Hollingbourne.',
    4: 'De kortste dag, met Canterbury aan het eind: de stad waar dit pad al '
       'acht eeuwen naartoe loopt.',
}


def page_stage_right(s, folio):
    p = s['plan']
    shots = ''.join(f'''
    <figure class="shot-fig">
      <span class="tag">{sh['tag']}</span>
      <img src="{sh['rel']}" alt="">
      <figcaption><span>bij km {nl_num(sh['km'])}</span>
        <span>Strava-community</span></figcaption>
    </figure>''' for sh in s['shots'])

    facts = ''.join(f'''
    <div class="fact-item">
      <span class="n">{f['n']}</span>
      <h4>{esc(f['title'])}</h4>
      <span class="km">km {nl_num(f['km'])}
        &middot; {f['off']} m van het pad</span>
      <p>{esc(whole_sentences(f['text']))}</p>
    </div>''' for f in s['facts'])

    pinned = ''
    if s['pinned']:
        a = s['pinned']
        pinned = f'''
  <div class="pinned">
    <span class="label">Het einddoel &middot; {a['offset_m']} m naast de route</span>
    <h4>{esc(a['title'])}</h4>
    <p>{esc(whole_sentences(a['extract']))}</p>
    <span class="src">{esc(a['url'])}</span>
  </div>'''

    return f'''
<section class="page">
  <div class="recto-head">
    <h3>{esc(p['name'])}</h3>
    <span class="of">Etappe {ROMAN[s['n']]} &middot; onderweg</span>
  </div>
  <div class="shots">{shots}</div>
  <div class="facts">
    <div class="label" style="margin-bottom:2.5mm">Wat je passeert</div>
    <div class="facts-grid">{facts}</div>
  </div>
  {pinned}
  <div class="folio right">{folio}</div>
</section>'''


def page_colophon(data, folio):
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Verantwoording</div>
    <h2>Waar dit boekje vandaan komt</h2>
    <div class="sub">Alles hierin is publiek beschikbaar materiaal. Dit staat er
      omdat de licenties het vragen &mdash; en omdat het aardig is om te weten.</div>
  </div>
  <dl class="sources">
    <dt>Kaarten</dt>
    <dd>Kaartgegevens &copy; OpenStreetMap-bijdragers, beschikbaar onder de Open
      Database License. De vier etappekaarten gebruiken de weergave van
      OpenTopoMap (&copy; OpenTopoMap, CC&nbsp;BY-SA) om de hoogtelijnen, uit SRTM,
      mee te krijgen; de overzichtskaart gebruikt de standaardweergave van
      OpenStreetMap, die op die schaal beter leesbaar is. De routelijn en alle
      markeringen zijn onze eigen GPX, over hun kaart heen getekend.</dd>

    <dt>Wetenswaardigheden</dt>
    <dd>Alle tekstjes komen van de Engelse Wikipedia en staan hier onder
      CC&nbsp;BY-SA&nbsp;4.0. Ze zijn geselecteerd met Wikipedia&rsquo;s geosearch-API en
      daarna gefilterd op werkelijke afstand tot het pad, en verder onbewerkt
      overgenomen. Elk artikel is te vinden op
      <code>en.wikipedia.org</code> onder de genoemde titel.</dd>

    <dt>Foto&rsquo;s</dt>
    <dd>De foto&rsquo;s onderweg zijn gemaakt door andere Strava-gebruikers en komen
      van de publieke fotolaag op Strava&rsquo;s routekaart. Ze staan hier ter
      ori&euml;ntatie, voor eigen gebruik binnen onze eigen ploeg. Ze blijven van
      hun makers: niet verspreiden, niet publiceren.</dd>

    <dt>Route, cijfers en profiel</dt>
    <dd>De vier GPX-bestanden komen uit Garmin Connect. Afstand, hoogteprofiel en
      hoogste punt zijn daaruit berekend. Waar de klim in de tabel afwijkt van de
      GPX volgen we de waarde van Strava, omdat de planning op die basis is
      gemaakt. Geplande tijden, tempo en de voedingsbudgetten komen uit het
      trainingsplan.</dd>

    <dt>Verhard of onverhard</dt>
    <dd>Het percentage onverhard in de kop van elke etappe is berekend uit de
      <code>surface</code>-tags van OpenStreetMap, ook onder de Open Database
      License. Elk stukje van het spoor is op de dichtstbijzijnde weg gelegd;
      waar niemand de ondergrond heeft ingevoerd is die afgeleid uit het wegtype,
      en op deze route geldt dat voor ongeveer de helft van de afstand. Reken het
      dus als een goede schatting, niet als een meting.</dd>

    <dt>Gemaakt op</dt>
    <dd>{nl_date(data['generated_at'][:10])}</dd>
  </dl>
  <div class="folio left">{folio}</div>
</section>'''


def build_html(data, stages, ov, cover):
    """Assemble the pages in reading order.

    Printed double-sided, the pages that face each other are (2,3), (4,5), (6,7)
    and so on — so a stage's map page has to land on an even number for its photo
    page to sit beside it rather than a page-turn away. That is why the overview
    is split across pages 2 and 3: it fills the first spread and pushes stage 1
    onto page 4.
    """
    css = open(os.path.join(BASE, 'style.css')).read()
    pages = [page_cover(stages, cover),     # 1, recto, no folio printed
             page_overview(stages, ov, 2),
             page_itinerary(stages, 3)]
    folio = 4
    for s in stages:
        assert folio % 2 == 0, f'stage {s["n"]} map page landed on recto {folio}'
        pages.append(page_stage_left(s, folio))
        pages.append(page_stage_right(s, folio + 1))
        folio += 2
    pages.append(page_colophon(data, folio))
    return f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<title>Pilgrims' Way — Routeboek</title>
<style>{css}</style>
</head><body>
{''.join(pages)}
</body></html>'''


# --- render --------------------------------------------------------------

CHROME_CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
]


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    hits = sorted(glob.glob(os.path.expanduser(
        '~/Library/Caches/ms-playwright/chromium-*/chrome-mac/'
        'Chromium.app/Contents/MacOS/Chromium')))
    return hits[-1] if hits else None


def render_pdf(html_path, pdf_path):
    chrome = find_chrome()
    if not chrome:
        print('  ! no Chrome found; the HTML is still usable', file=sys.stderr)
        return False
    r = subprocess.run([
        chrome, '--headless', '--disable-gpu', '--no-sandbox',
        '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=15000',
        f'--print-to-pdf={pdf_path}', f'file://{html_path}',
    ], capture_output=True, text=True, timeout=300)
    if not os.path.exists(pdf_path):
        print(f'  ! chrome failed: {r.stderr[-600:]}', file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-maps', action='store_true',
                    help='reuse the basemaps already in routebook/maps')
    ap.add_argument('--open', action='store_true')
    args = ap.parse_args()

    print('Collecting…')
    data, stages, ov, cover = collect(no_maps=args.no_maps)

    html_path = os.path.join(OUT, 'routeboek.html')
    with open(html_path, 'w') as f:
        f.write(build_html(data, stages, ov, cover))
    print(f'  {html_path}')

    pdf_path = os.path.join(OUT, 'pilgrims-way-routeboek.pdf')
    if render_pdf(html_path, pdf_path):
        print(f'  {pdf_path} ({os.path.getsize(pdf_path) // 1024} KB)')
        if args.open:
            subprocess.run(['open', pdf_path])


if __name__ == '__main__':
    main()
