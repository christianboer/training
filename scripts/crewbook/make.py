#!/usr/bin/env python3
"""Build the crew booklet: HTML -> A4 PDF via headless Chrome.

    python3 scripts/crewbook/make.py [--no-maps] [--open]

A twelve-page booklet for the two who travel by car — the day programme from
`plan/support-crew-dagen.md`, the hotels with tappable navigation links, and a map
per day showing where the walkers are and where they should be.

Deliberately the routebook's sibling: it borrows `../routebook/style.css`, its
tile stitcher and its page geometry, and adds `crew.css` for the components that
are new here.

**One difference that matters.** Every photograph comes from Wikimedia Commons
under CC BY-SA, CC BY or CC0, so unlike the routebook — which embeds other
people's Strava photos and must stay in the family — this PDF may be shared, as
long as the credits stay on the page. That is why `make.py` prints a photographer
under every picture and a full credit list on the last page. Do not strip them,
and do not add a Strava photo to this booklet: one unlicensed image would take
the whole thing back into "never publish".

Called make.py rather than build.py so it cannot be confused with the routebook's
build.py — neither by python's import machinery nor by pgrep.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '../..'))
ROUTEBOOK = os.path.join(REPO, 'scripts', 'routebook')
sys.path.insert(0, HERE)
sys.path.insert(1, ROUTEBOOK)

import commons
from build import ROMAN, esc, find_chrome, nl_date, nl_num   # routebook helpers
from gpxread import read_stage, simplify
from tiles import build_basemap, projector

OUT = os.path.join(REPO, 'crewbook')
MAP_MM = 180.0
DAY_MAP_ASPECT = 2.0

# --- the material ---------------------------------------------------------
#
# Photographs are pinned by exact Commons title. Search results drift; a booklet
# should rebuild identically next month.

PHOTO = {
    'cover':      'File:Leeds Castle across the Great Lake - geograph.org.uk - 4209999.jpg',
    'whyte_harte': 'File:The Whyte Harte Hotel - geograph.org.uk - 1937559.jpg',
    'red_lion':   'File:The Red Lion, Charing Heath - geograph.org.uk - 2077087.jpg',
    'westerham':  'File:Westerham - Market Square - geograph.org.uk - 6602829.jpg',
    'chartwell':  'File:Chartwell - Once the home of Sir Winston Churchill - geograph.org.uk - 4118422.jpg',
    'aylesford':  'File:Aylesford Priory courtyard, 2014 - 2.jpg',
    'kits_coty':  "File:Kit's Coty, Nov 2021 02.jpg",
    'leeds':      'File:Leeds Castle from the west.jpg',
    'charing':    "File:Archbishop's Palace, Charing, Dec 2020.jpg",
    'chilham':    'File:Chilham Village, Kent, England.jpg',
    'stour':      'File:Great Stour, Canterbury - geograph.org.uk - 2211697.jpg',
    'cathedral':  'File:Canterbury Cathedral Nave 1, Kent, UK - Diliff.jpg',
}


def maps_link(query):
    """A Google Maps directions link. Tappable in the PDF: Chrome's print-to-pdf
    turns <a href> into a real link annotation, so on a phone this opens
    navigation straight to the door."""
    return ('https://www.google.com/maps/dir/?api=1&destination='
            + urllib.parse.quote(query))


HOTELS = [
    {'night': 'donderdag 3 september', 'photo': 'whyte_harte',
     'name': 'The Whyte Harte Hotel',
     'addr': ['11–21 High Street', 'Bletchingley, Redhill RH1 4PB'],
     'tel': None,
     'q': 'Whyte Harte Hotel, 11-21 High Street, Bletchingley, RH1 4PB',
     'note': 'Staat aan de High Street, op een paar honderd meter van waar de '
             'lopers die dag binnenkomen. Zelf een 16e-eeuwse herberg.'},
    {'night': 'vrijdag 4 september', 'photo': None,
     'slug': 'wrotham', 'at': (51.2998, 0.3400),
     'name': 'Holiday Inn Maidstone–Sevenoaks',
     'addr': ['London Road', 'Wrotham Heath, Sevenoaks TN15 7RS'],
     'tel': '01732 756900',
     'q': 'Holiday Inn Maidstone Sevenoaks, London Road, Wrotham Heath, TN15 7RS',
     'note': 'Let op: het heet Maidstone, maar het staat in Wrotham Heath — '
             'dertien kilometer westelijker. Dat is precies waar de etappe van '
             'die dag eindigt, dus dat is goed.'},
    {'night': 'zaterdag 5 september', 'photo': 'red_lion',
     'name': 'The Red Lion',
     'addr': ['Charing Heath Road', 'Charing Heath, Ashford TN27 0AU'],
     'tel': '01233 712418',
     'q': 'The Red Lion, Charing Heath Road, Charing Heath, TN27 0AU',
     'note': 'Gebouwd in 1562 als rietgedekte boerderij, sinds 1762 een herberg. '
             'Ligt aan de Pilgrims’ Way, pal bij het eind van de etappe.'},
]

TUNNEL = {'name': 'Eurotunnel LeShuttle, Folkestone',
          'addr': ['Ashford Road, Folkestone CT18 8XX', 'M20, afrit 11A'],
          'q': 'Eurotunnel Terminal Building, Folkestone'}

# Meeting windows: moving times from the plan plus room for stops, on an 8:00
# start. Windows, not times — last year they ran about an hour and three quarters
# inside the planned total, so early is far likelier than late.
WINDOWS = [
    ('vr', 'Ide Hill, dorpsplein', '22,5', '10:30 – 11:15', False),
    ('za', 'Aylesford Priory', '13,4', '09:30 – 09:50', False),
    ('za', 'Bluebell Hill', '20,6', '10:25 – 10:50', False),
    ('zo', 'Chilham, dorpsplein', '24,3', '10:45 – 11:20', False),
    ('zo', 'langs de Stour, Canterbury', '33 – 34', '12:15 – 12:45', False),
    ('zo', 'de finish in Canterbury', '36,0', '12:30 – 13:00', True),
]

# Each day: the stops that get a numbered pin on the map, in order.
DAYS = [
    {
        'n': 1, 'date': '2026-09-03', 'title': 'Aankomst in Bletchingley',
        'stage': 1, 'map': False,
        'lead': 'Een reisdag. De lopers zijn ’s ochtends uit Guildford vertrokken '
                'en komen naar verwachting tussen 13:15 en 14:15 bij de Whyte '
                'Harte binnen.',
        'stops': [],
        'slots': [
            ('in de middag', None, None, 'Aankomst bij The Whyte Harte',
             ['Bagage naar binnen, en dan is het wachten op twee bezwete '
              'wandelaars. Reken op ergens tussen 13:15 en 14:15.']),
            ('als er zin is', None, None, 'Een rondje Bletchingley',
             ['Het hotel staat aan de High Street, dus dit is de voordeur uit. '
              'Beschermd dorpsgezicht, middeleeuwse gebouwen, een 13e-eeuwse '
              'kerk.',
              'Godstone ligt vijf minuten verderop en heeft een dorpsgroen met '
              'een vijver en een paar pubs.']),
        ],
    },
    {
        'n': 2, 'date': '2026-09-04', 'title': 'Bletchingley → Wrotham Heath',
        'stage': 2, 'map': True,
        'lead': 'Van west naar oost, dezelfde richting als de lopers. Ruim een '
                'uur rijden over de hele dag, dus de dag wordt begrensd door wat '
                'je wilt zien, niet door de afstand.',
        'stops': [
            ('Westerham', 51.2681, 0.0739),
            ('Ide Hill', 51.2457, 0.1312),
            ('Chartwell', 51.2447, 0.0872),
            ('Holiday Inn, Wrotham Heath', 51.2998, 0.3400),
        ],
        'slots': [
            ('09:30', None, None, 'Vertrek uit Bletchingley',
             ['Bagage in de auto.']),
            ('10:00 – 10:30', '± 25 min', 1, 'Westerham',
             ['Een dorp met een groen, een standbeeld van Churchill en een rij '
              'zelfstandige winkels en antiekzaken. Vlak, en goed voor een '
              'eerste koffie.']),
            ('10:45 – 11:20', '± 12 min', 2, 'Ide Hill — hier zien jullie ze',
             ['Dorpsplein met wat veel mensen het mooiste uitzicht van Kent '
              'vinden, en de dorpswinkel waar de lopers hun hulppost hebben.',
              'Reken op 10:30 – 11:15.']),
            ('11:35 – 14:15', '± 10 min', 3, 'Chartwell',
             ['Het huis waar Winston Churchill veertig jaar woonde. Huis open '
              'vanaf 11:00, laatste toegang 15:40, en er is een restaurant voor '
              'de lunch.',
              'De wandeling langs de meren onder het huis is een goed uur en '
              'aanzienlijk vlakker dan de tuin zelf.']),
            ('14:45', '± 30 min', 4, 'Naar het hotel',
             ['Rond 15:15 binnen bij het Holiday Inn in Wrotham Heath.']),
        ],
    },
    {
        'n': 3, 'date': '2026-09-05', 'title': 'Wrotham Heath → Charing Heath',
        'stage': 3, 'map': True,
        'lead': 'De rustigste dag qua rijden en de rijkste qua bezoek. Een gratis '
                'klooster, een grafmonument van vijfduizend jaar oud, en ’s '
                'middags een kasteel in een meer.',
        'stops': [
            ('Aylesford Priory', 51.2972, 0.4722),
            ("Kit's Coty House", 51.3172, 0.5006),
            ('Leeds Castle', 51.2486, 0.6300),
            ('The Red Lion, Charing Heath', 51.2085, 0.7570),
        ],
        'slots': [
            ('09:15', None, None, 'Vertrek uit Wrotham Heath', []),
            ('09:30 – 11:00', '± 15 min', 1,
             'Aylesford Priory — hier zien jullie ze',
             ['Een 13e-eeuws karmelietenklooster. Gratis, 365 dagen open, '
              'terrein dag en nacht toegankelijk. Theetuin vanaf 10:00, een '
              'cadeauwinkel en een werkende pottenbakkerij.',
              'Het klooster ligt óp de route, bij kilometer 13,4: wie er om '
              '09:30 is, ziet de lopers langskomen en gaat daarna theedrinken. '
              'Reken op 09:30 – 09:50.']),
            ('11:15 – 11:45', '± 8 min', 2, "Kit's Coty House",
             ['Een megalithisch grafmonument van rond 4000 v.Chr., pal langs de '
              'weg, gratis, met een korte vlakke aanloop. Vijf minuten kijken, '
              'vijfduizend jaar oud.',
              'Het ligt naast de hulppost bij Bluebell Hill, dus met een beetje '
              'geluk vangen jullie de lopers hier een tweede keer — reken op '
              '10:25 – 10:50.']),
            ('12:05 – 15:40', '± 20 min', 3, 'Leeds Castle',
             ['Een kasteel op een eiland in een meer, met tweehonderd hectare '
              'park, tuinen, een doolhof, zwarte zwanen en meerdere '
              'eetgelegenheden.',
              'Van alles in dit boekje het best geregeld voor wie niet ver of '
              'niet steil wil lopen — zie de laatste pagina. Het park is groot '
              'en rustig van reliëf: een uur wandelen kan hier makkelijk.']),
            ('15:45', '± 18 min', 4, 'Naar The Red Lion',
             ['Rond 16:00 binnen.']),
        ],
    },
    {
        'n': 4, 'date': '2026-09-06', 'title': 'Charing Heath → Canterbury → naar huis',
        'stage': 4, 'map': True,
        'lead': 'De dag van de finish, en daarna door naar de tunnel. Alles gaat '
                'bij het uitchecken de auto in — ook de bagage van de lopers, '
                'want die stappen in Canterbury in.',
        'stops': [
            ('Charing', 51.2089, 0.7906),
            ('Chilham', 51.2444, 0.9611),
            ('Canterbury, Westgate', 51.2777, 1.0740),
        ],
        'slots': [
            ('09:30 – 10:00', '± 5 min', 1, 'Charing',
             ['Naast het hotel, aan de Pilgrims’ Way. De ruïne van het '
              'Archbishop’s Palace gaat terug tot de achtste eeuw en was een '
              'pleisterplaats voor pelgrims op weg naar Canterbury — precies de '
              'rol die jullie deze week vervullen.']),
            ('10:25 – 11:25', '± 20 min', 2, 'Chilham — hier zien jullie ze',
             ['Een middeleeuws dorpsplein met Tudor-vakwerkhuizen, een '
              '16e-eeuwse kerk en het kasteel. Aan het plein zit The Church '
              'Mouse Tea Rooms, de hulppost van de lopers: open 09:30 – 16:30. '
              'Koffie met scones terwijl zij door het dorp komen.',
              'Reken op 10:45 – 11:20. De kasteeltuinen zijn alleen op dinsdag '
              'en donderdag open, dus vandaag niet. En vier smalle, steile '
              'straatjes klimmen naar het plein: parkeer zo dicht bij het plein '
              'als het kan.']),
            ('11:45', '± 18 min', 3, 'Naar Canterbury',
             ['Parkeren bij Westgate. En dan het mooiste van de week — zie de '
              'volgende pagina.']),
        ],
    },
]


# --- maps -----------------------------------------------------------------

def day_map(day, no_maps=False):
    """Basemap for one day: the walkers' stage plus the crew's stops.

    No car route is drawn between the stops. We have no routing data, and a
    straight line between two villages would suggest a road that is not there —
    the numbers keyed to the timeline say everything that needs saying.
    """
    if not day['map']:
        return None
    rel = f'maps/dag{day["n"]}.jpg'
    abs_path = os.path.join(OUT, rel)
    meta_path = os.path.splitext(abs_path)[0] + '.json'

    gpx = glob.glob(os.path.join(REPO, f'plan/stages/stage{day["stage"]}-*.gpx'))[0]
    geo = read_stage(gpx)
    coords = [(p[0], p[1]) for p in geo['points']]
    coords += [(lat, lon) for _, lat, lon in day['stops']]

    if no_maps and os.path.exists(meta_path):
        meta = json.load(open(meta_path))
    else:
        meta = build_basemap(coords, abs_path, aspect=DAY_MAP_ASPECT,
                             target_px=2400, source='osm')
    return {'rel': rel, 'meta': meta, 'track': simplify(geo['points'], 40)}


def point_map(lat, lon, rel, aspect=1.48, span=0.0055, no_maps=False):
    """A small locator map around one point.

    For the Holiday Inn, which is a modern chain hotel and so has no freely
    licensed photograph anywhere. A map crop is honest about that and more use to
    a driver than a stock picture of a lobby would be."""
    abs_path = os.path.join(OUT, rel)
    meta_path = os.path.splitext(abs_path)[0] + '.json'
    if no_maps and os.path.exists(meta_path):
        return {'rel': rel, 'meta': json.load(open(meta_path))}
    box = [(lat - span * 0.6, lon - span), (lat + span * 0.6, lon + span)]
    meta = build_basemap(box, abs_path, aspect=aspect, target_px=900, pad=0.02,
                         source='osm')
    return {'rel': rel, 'meta': meta}


def point_marker_svg(m, lat, lon, mm_width=62.0):
    u = m['meta']['width'] / mm_width
    x, y = projector(m['meta'])(lat, lon)
    return (f'<svg class="overlay" viewBox="0 0 {m["meta"]["width"]} '
            f'{m["meta"]["height"]}" xmlns="http://www.w3.org/2000/svg" '
            f'aria-hidden="true"><g class="pin aid">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.7 * u:.2f}" '
            f'stroke-width="{0.35 * u:.2f}"/></g></svg>')


def day_overlay(m, day, mm_width=MAP_MM):
    u = m['meta']['width'] / mm_width
    pr = projector(m['meta'])
    o = [f'<svg class="overlay" viewBox="0 0 {m["meta"]["width"]} '
         f'{m["meta"]["height"]}" xmlns="http://www.w3.org/2000/svg" '
         f'aria-hidden="true">']
    pts = ' '.join(f'{x:.1f},{y:.1f}'
                   for x, y in (pr(p[0], p[1]) for p in m['track']))
    o.append(f'<polyline class="track-case" points="{pts}" '
             f'stroke-width="{1.6 * u:.2f}"/>')
    o.append(f'<polyline class="track" points="{pts}" stroke-width="{0.8 * u:.2f}"/>')
    for i, (name, lat, lon) in enumerate(day['stops'], 1):
        x, y = pr(lat, lon)
        o.append(f'<g class="fact"><circle cx="{x:.1f}" cy="{y:.1f}" '
                 f'r="{2.0 * u:.2f}" stroke-width="{0.25 * u:.2f}"/>'
                 f'<text x="{x:.1f}" y="{y + 0.72 * u:.1f}" '
                 f'font-size="{2.6 * u:.2f}">{i}</text></g>')
        o.append(f'<g class="pin"><text x="{x:.1f}" y="{y - 3.0 * u:.1f}" '
                 f'text-anchor="middle" font-size="{2.5 * u:.2f}" '
                 f'stroke-width="{0.55 * u:.2f}">{esc(name)}</text></g>')
    o.append('</svg>')
    return '\n'.join(o)


def overview_map(days, no_maps=False):
    rel = 'maps/overzicht.jpg'
    abs_path = os.path.join(OUT, rel)
    meta_path = os.path.splitext(abs_path)[0] + '.json'
    tracks, coords = [], []
    for n in (1, 2, 3, 4):
        gpx = glob.glob(os.path.join(REPO, f'plan/stages/stage{n}-*.gpx'))[0]
        geo = read_stage(gpx)
        tracks.append(simplify(geo['points'], 80))
        coords += [(p[0], p[1]) for p in geo['points']]
    if no_maps and os.path.exists(meta_path):
        meta = json.load(open(meta_path))
    else:
        meta = build_basemap(coords, abs_path, aspect=2.0, target_px=2200,
                             pad=0.05, source='osm')
    return {'rel': rel, 'meta': meta, 'tracks': tracks}


def overview_overlay(ov, mm_width=MAP_MM):
    u = ov['meta']['width'] / mm_width
    pr = projector(ov['meta'])
    o = [f'<svg class="overlay" viewBox="0 0 {ov["meta"]["width"]} '
         f'{ov["meta"]["height"]}" xmlns="http://www.w3.org/2000/svg" '
         f'aria-hidden="true">']
    for t in ov['tracks']:
        pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (pr(p[0], p[1]) for p in t))
        o.append(f'<polyline class="track-case" points="{pts}" '
                 f'stroke-width="{1.5 * u:.2f}"/>')
    for t in ov['tracks']:
        pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (pr(p[0], p[1]) for p in t))
        o.append(f'<polyline class="track" points="{pts}" '
                 f'stroke-width="{0.8 * u:.2f}"/>')
    for name, lat, lon, kind in [
            ('Guildford', 51.2358, -0.5807, 'start'),
            ('Bletchingley', 51.2386, -0.0986, 'aid'),
            ('Wrotham Heath', 51.2998, 0.3400, 'aid'),
            ('Charing Heath', 51.2085, 0.7570, 'aid'),
            ('Canterbury', 51.2797, 1.0830, 'finish')]:
        x, y = pr(lat, lon)
        o.append(f'<g class="pin {kind}"><circle cx="{x:.1f}" cy="{y:.1f}" '
                 f'r="{1.5 * u:.2f}" stroke-width="{0.28 * u:.2f}"/>'
                 f'<text x="{x:.1f}" y="{y - 2.5 * u:.1f}" text-anchor="middle" '
                 f'font-size="{2.6 * u:.2f}" stroke-width="{0.6 * u:.2f}">'
                 f'{esc(name)}</text></g>')
    o.append('</svg>')
    return '\n'.join(o)


# --- photos ---------------------------------------------------------------

def gather_photos(quiet=False):
    """-> {key: meta with local rel path}. Missing ones are simply absent, and
    every page guards for that, so one unavailable file cannot break the book."""
    os.makedirs(os.path.join(OUT, 'photos'), exist_ok=True)
    out = {}
    for key, title in PHOTO.items():
        m = commons.fetch(title, width=1600, quiet=quiet)
        if not m:
            continue
        dest = os.path.join(OUT, 'photos', os.path.basename(m['path']))
        shutil.copyfile(m['path'], dest)
        m['rel'] = f'photos/{os.path.basename(m["path"])}'
        out[key] = m
    return out


def credit(p):
    return esc(commons.credit_line(p)) if p else ''


def photo_card(p, title, text, wide=False):
    if not p:
        return ''
    return f'''
  <div class="photo-card{' wide' if wide else ''}">
    <img src="{p['rel']}" alt="">
    <div class="credit">{credit(p)}</div>
    <h4>{esc(title)}</h4>
    <p>{text}</p>
  </div>'''


# --- pages ---------------------------------------------------------------

def page_cover(ph):
    hero = ph.get('cover')
    img = (f'<figure class="hero"><img src="{hero["rel"]}" alt="">'
           f'<figcaption>Leeds Castle &middot; {credit(hero)}</figcaption>'
           f'</figure>') if hero else ''
    return f'''
<section class="page cover">
  <div class="eyebrow">Voor de ploeg</div>
  {img}
  <div class="acorn"></div>
  <h1>Kent, met de auto<em>vier dagen langs de Pilgrims&rsquo; Way</em></h1>
  <div class="hair"></div>
  <div class="meta"><strong>3 &ndash; 6 september 2026</strong></div>
  <div class="who-for">
    Guildford &rarr; Canterbury &middot; 170 kilometer<br>
    Zij lopen. Jullie rijden, kijken, en staan op de goede plek.
  </div>
</section>'''


def page_overview(ov, ph):
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Overzicht</div>
    <h2>De vier dagen</h2>
    <div class="sub">De rode lijn is hun route. Jullie kruisen die elke dag
      minstens één keer.</div>
  </div>
  <div class="mapbox" style="margin-top:5mm">
    <img src="{ov['rel']}" alt="Overzichtskaart">
    {overview_overlay(ov)}
    <div class="attrib">{esc(ov['meta']['attribution'])}</div>
  </div>
  <table class="windows" style="margin-top:6mm">
    <thead><tr><th></th><th>Van hotel naar hotel</th><th class="r">Rijden</th>
      <th class="r">Hoogtepunt van de dag</th></tr></thead>
    <tbody>
      <tr><td class="day">do</td><td>aankomst in Bletchingley</td>
        <td class="r">&mdash;</td><td class="r">Bletchingley zelf</td></tr>
      <tr><td class="day">vr</td><td>Bletchingley &rarr; Wrotham Heath</td>
        <td class="r">± 1 uur</td><td class="r">Chartwell</td></tr>
      <tr><td class="day">za</td><td>Wrotham Heath &rarr; Charing Heath</td>
        <td class="r">± 1 uur</td><td class="r">Leeds Castle</td></tr>
      <tr class="finish"><td class="day">zo</td>
        <td>Charing Heath &rarr; Canterbury &rarr; de tunnel</td>
        <td class="r">± 1½ uur</td><td class="r">de finish</td></tr>
    </tbody>
  </table>
  <div class="prose" style="margin-top:5mm">
    <p><strong>Elke dag hetzelfde ritme.</strong> Een rustige ochtend, ergens
    onderweg de lopers zien, ’s middags één grotere bezienswaardigheid, en om
    16:00 in het volgende hotel. Op zondag geldt dat laatste niet: dan gaat het
    na de finish door naar Folkestone.</p>
    <p>De genummerde bolletjes op de dagkaarten komen terug in het programma
    ernaast. Er staat geen autoroute op de kaart getekend — die verzint een weg
    die er misschien niet is; de nummers wijzen de plekken aan, de navigatie doet
    de rest.</p>
  </div>
  <div class="folio left">2</div>
</section>'''


def page_hotels(ph):
    # locator maps are attached to HOTELS by main() before this runs
    cards = []
    for h in HOTELS:
        p = ph.get(h['photo']) if h['photo'] else None
        if p:
            shot = (f'<div class="shot"><img src="{p["rel"]}" alt="">'
                    f'<div class="credit">{credit(p)}</div></div>')
        elif h.get('locator'):
            lm = h['locator']
            shot = (f'<div class="shot"><div class="mapbox">'
                    f'<img src="{lm["rel"]}" alt="">{lm["svg"]}</div>'
                    f'<div class="credit">Kaart: &copy; OpenStreetMap-bijdragers. '
                    f'Van dit hotel bestaat geen vrij te gebruiken foto.</div></div>')
        else:
            shot = ''
        tel = f'<div class="tel">{h["tel"]}</div>' if h['tel'] else ''
        cards.append(f'''
  <div class="hotel">
    {shot}
    <div class="body">
      <div class="night">{h['night']}</div>
      <h3>{esc(h['name'])}</h3>
      <div class="addr"><strong>{esc(h['addr'][0])}</strong><br>
        {esc(h['addr'][1])}</div>
      {tel}
      <div class="note">{esc(h['note'])}</div>
      <a class="nav" href="{maps_link(h['q'])}">Navigeer erheen</a>
    </div>
  </div>''')

    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Waar jullie slapen</div>
    <h2>De drie hotels</h2>
    <div class="sub">Alle drie staan op een paar honderd meter van de plek waar de
      etappe die dag eindigt. Er hoeft dus niemand gehaald te worden.</div>
  </div>
  <div class="hotels">{''.join(cards)}</div>
  <div class="callout">
    <span class="label">Zondag &middot; naar huis</span>
    <h3>{esc(TUNNEL['name'])}</h3>
    <p>{esc(TUNNEL['addr'][0])} &middot; {esc(TUNNEL['addr'][1])}</p>
    <p>Inchecken kan tot uiterlijk <strong>een uur</strong> voor vertrek, maar
    LeShuttle adviseert 60 tot 90 minuten, en op een zomerse zondag nog een half
    uur extra. De <strong>Advance Passenger Information moet 24 uur vooraf online
    zijn ingevuld</strong> — zonder dat mag je niet mee.</p>
    <p>Zoek in de kaart op <em>Eurotunnel Terminal Building</em>: de postcode
    alleen leidt soms naar een ventweg naast de terminal.</p>
    <a class="nav plain" href="{maps_link(TUNNEL['q'])}">Navigeer naar de terminal</a>
  </div>
  <div class="folio right">3</div>
</section>'''


def page_windows():
    rows = ''.join(
        f'<tr{" class=\"finish\"" if fin else ""}><td class="day">{d}</td>'
        f'<td>{esc(place)}</td><td class="r">km {km}</td>'
        f'<td class="win">{w}</td></tr>'
        for d, place, km, w, fin in WINDOWS)
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Waar en wanneer</div>
    <h2>Zo vinden jullie ze onderweg</h2>
    <div class="sub">Een venster, geen tijdstip — en eerder vroeg dan laat.</div>
  </div>
  <table class="windows">
    <thead><tr><th></th><th>Plek</th><th class="r">Bij km</th>
      <th class="r">Reken op</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="prose" style="margin-top:6mm">
    <p>Deze tijden gaan uit van <strong>vertrek om 8:00</strong> en zijn de
    looptijd volgens het plan, met wat marge voor pauzes. Vertrekken ze later,
    schuift alles even ver mee.</p>
    <p><strong>Reken op vroeg.</strong> De geplande tijden zijn ruim genomen:
    vorig jaar deden ze hun vierdaagse bijna twee uur sneller dan hetzelfde model
    voorspelde. De kans dat jullie staan te wachten is dus groter dan de kans dat
    jullie ze missen.</p>
    <p>Het simpelste is een berichtje: <strong>bij vertrek en bij de
    hulppost</strong>. Dan wordt het venster een tijdstip.</p>
  </div>
  <div class="callout">
    <span class="label">Als het misgaat</span>
    <h3>Ze staan stil, of jullie missen elkaar</h3>
    <p>De hulpposten zijn de afgesproken plekken, en ze staan alle vier ook in
    hun eigen boekje: <strong>Ryka’s Cafe</strong> (donderdag),
    <strong>Ide Hill Community Shop</strong> (vrijdag),
    <strong>Shell Bluebell Hill</strong> (zaterdag) en
    <strong>The Church Mouse Tea Rooms</strong> in Chilham (zondag).</p>
    <p>Lukt het niet, rijd dan gewoon door naar het hotel van die avond — daar
    komen ze hoe dan ook langs.</p>
  </div>
  <div class="folio left">4</div>
</section>'''


def page_day(day, m, ph, folio, extra=''):
    slots = []
    for when, drive, n, head, paras in day['slots']:
        num = (f'<div class="n">{n}</div>' if n
               else '<div class="n blank"></div>')
        body = ''.join(f'<p>{p}</p>' for p in paras)
        dr = f'<div class="drive">{drive} rijden</div>' if drive else ''
        slots.append(f'''
    <div class="slot">
      <div class="when">{when}{f'<small>{drive}</small>' if drive else ''}</div>
      {num}
      <div class="what"><h4>{esc(head)}</h4>{body}</div>
    </div>''')

    mapbox = ''
    if m:
        mapbox = f'''
  <div class="mapbox" style="margin-top:4mm">
    <img src="{m['rel']}" alt="Kaart van de dag">
    {day_overlay(m, day)}
    <div class="attrib">{esc(m['meta']['attribution'])}</div>
  </div>'''

    return f'''
<section class="page">
  <div class="stage-head">
    <div class="numeral">{ROMAN[day['n']]}</div>
    <div class="who">
      <div class="date">{nl_date(day['date'])}</div>
      <h2>{esc(day['title'])}</h2>
      <div class="role">{esc(day['lead'])}</div>
    </div>
  </div>
  {mapbox}
  <div class="timeline">{''.join(slots)}</div>
  {extra}
  <div class="folio {'left' if folio % 2 == 0 else 'right'}">{folio}</div>
</section>'''


def page_day2_places(ph, folio):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Vrijdag &middot; wat jullie zien</h3>
    <span class="of">Bletchingley &rarr; Wrotham Heath</span>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('westerham'), 'Westerham',
                'Marktplein met een standbeeld van Churchill, zelfstandige '
                'winkels en antiekzaken. Vlak, en een prettige eerste stop.')}
    {photo_card(ph.get('chartwell'), 'Chartwell',
                'Churchills huis, veertig jaar lang. Huis vanaf 11:00, laatste '
                'toegang 15:40, restaurant voor de lunch.')}
  </div>
  <div class="callout">
    <span class="label">Eén keuze op deze dag</span>
    <h3>Chartwell, of Ightham Mote</h3>
    <p>Twee huizen op één dag kost samen ruim tachtig pond en dat hoeft niet.
    <strong>Chartwell</strong> is het bezoek waar jullie het over gaan hebben —
    dat is mijn advies.</p>
    <p>Maar kies <strong>Ightham Mote</strong> als een dag zonder gedoe zwaarder
    weegt: een 14e-eeuws huis met slotgracht, gelijkvloerse ingang, gelijkvloers
    café, tien minuten van het hotel, en iets goedkoper. Bij Chartwell is het
    250 meter van de parkeerplaats naar het huis over een steil pad met 24
    treden — er rijdt een busje, maar niet elke dag.</p>
  </div>
  <div class="prose" style="margin-top:5mm">
    <p><strong>De wandeling van deze dag.</strong> Onder Chartwell liggen de
    meren, met een pad eromheen: een goed uur, en veel vlakker dan de tuin op de
    helling. Wie liever een tuin dan een huis wil: <strong>Emmetts
    Garden</strong> ligt op één kilometer van Ide Hill, zeven dagen per week
    open — maar met steile hellingen en treden.</p>
  </div>
  <div class="folio right">{folio}</div>
</section>'''


def page_day3_places(ph, folio):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Zaterdag &middot; wat jullie zien</h3>
    <span class="of">Wrotham Heath &rarr; Charing Heath</span>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('leeds'), 'Leeds Castle', 'Een kasteel op een eiland in '
                'een meer, met tweehonderd hectare park, een doolhof en zwarte '
                'zwanen. De hele middag waard.', wide=True)}
    {photo_card(ph.get('aylesford'), 'Aylesford Priory',
                'Karmelietenklooster uit de 13e eeuw. Gratis, vlak, stil — en '
                'het ligt op hun route, dus jullie zien ze hier langskomen.')}
    {photo_card(ph.get('kits_coty'), "Kit's Coty House",
                'Een grafmonument van rond 4000 v.Chr., pal langs de weg. Vijf '
                'minuten kijken, vijfduizend jaar oud.')}
  </div>
  <div class="callout">
    <span class="label">Leeds Castle &middot; zonder ver of steil te lopen</span>
    <h3>Hier is het goed geregeld</h3>
    <p>Er rijdt de hele dag een <strong>gratis toegankelijk busje</strong> over
    het terrein, vanaf de kassa. Invalidenparkeren ligt op maximaal honderd meter
    daarvan, en <strong>rolstoelen zijn gratis te leen</strong> bij het
    bezoekerscentrum, zolang de voorraad strekt.</p>
    <p>Er rijdt ook een treintje van de ingang naar het kasteel, maar dat is
    níet rolstoeltoegankelijk — het busje wel.</p>
  </div>
  <div class="folio right">{folio}</div>
</section>'''


def page_day4_places(ph, folio):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Zondag &middot; het laatste stuk</h3>
    <span class="of">Charing Heath &rarr; Canterbury</span>
  </div>
  <div class="callout" style="margin-top:4mm">
    <span class="label">Het mooiste van de hele week</span>
    <h3>Loop de laatste kilometers mee</h3>
    <p>Vanaf <strong>Westgate Gardens</strong> loopt de <strong>Great Stour
    Way</strong> langs de rivier de stad uit — vlak en verhard. En de lopers
    komen precies over dat pad binnen, via Chartham.</p>
    <p>Dus: parkeer bij Westgate, loop rond <strong>12:05</strong> het pad op
    langs het water, kom ze tussen <strong>12:15 en 12:45</strong> tegen bij
    Tannery Field of Bingley Island, en loop met ze de laatste twee of drie
    kilometer de stad in. Voor jullie is dat vijf à zes kilometer over vlak,
    verhard pad — en dan komt iedereen samen te voet in Canterbury aan, na 170
    kilometer.</p>
    <p>Liever niet wandelen? Ga bij de <strong>Westgate Towers</strong> staan en
    wacht ze daar op.</p>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('stour'), 'De Great Stour bij Canterbury',
                'Het pad waarover ze binnenkomen. Verhard, vlak, langs het '
                'water.')}
    {photo_card(ph.get('cathedral'), 'De kathedraal',
                'Op zondag: terrein vanaf 11:30, de kerk zelf vanaf 12:30, '
                'laatste toegang 16:00. Kaartjes kunnen aan de deur.')}
  </div>
  <div class="prose" style="margin-top:4mm">
    <p><strong>De rest van de dag.</strong> Rond 13:00 samen de kathedraal in —
    anderhalf uur is genoeg om het goed te zien. Om ongeveer 15:00 weg, en dan
    rond 15:35 bij de terminal in Folkestone. Thuis rond half elf.</p>
  </div>
  <div class="folio right">{folio}</div>
</section>'''


def page_practical(ph, folio):
    creds = ''.join(
        f'<div><strong>{esc(p["title"].replace("File:", ""))}</strong><br>'
        f'{credit(p)}</div>'
        for p in ph.values())
    return f'''
<section class="page">
  <div class="title-block">
    <div class="label">Praktisch</div>
    <h2>Kosten, kaartjes en kleine lettertjes</h2>
  </div>
  <table class="windows" style="margin-top:4mm">
    <thead><tr><th></th><th>Entree</th><th class="r">Per persoon</th>
      <th class="r">Samen</th></tr></thead>
    <tbody>
      <tr><td class="day">vr</td><td>Chartwell, huis + tuin</td>
        <td class="r">£ 21,60</td><td class="win">£ 43,20</td></tr>
      <tr><td class="day">za</td><td>Leeds Castle, online geboekt</td>
        <td class="r">£ 34,50</td><td class="win">£ 69,00</td></tr>
      <tr><td class="day">zo</td><td>Kathedraal Canterbury</td>
        <td class="r">£ 19,50</td><td class="win">£ 39,00</td></tr>
      <tr class="finish"><td></td><td>Totaal over vier dagen</td><td></td>
        <td class="win">± £ 151</td></tr>
    </tbody>
  </table>
  <div class="prose" style="margin-top:4mm">
    <p><strong>Gratis</strong>, en niet de minste onderdelen: Aylesford Priory,
    Kit’s Coty House, Westerham, Ide Hill, Charing, Chilham, de Great Stour Way
    en het terrein van de kathedraal.</p>
    <p><strong>Vooraf regelen.</strong> Chartwell werkt met tijdvakken voor het
    huis — boek dat, en vraag meteen of het mobiliteitsbusje die dag rijdt. Leeds
    Castle is online vier pond per persoon goedkoper dan aan de poort. Voor de
    kathedraal hoeft niets vooraf.</p>
    <p><strong>Openingsdagen.</strong> De National Trust opent per dag, en de
    kalender voor september 2026 stond bij het maken van dit boekje nog niet
    vast. Eén keer nakijken een week voor vertrek is verstandig.</p>
  </div>

  <div class="rule" style="margin-top:5mm"></div>
  <div class="label">Zonder ver of steil te lopen</div>
  <div class="prose" style="margin-top:2mm">
    <p><strong>Leeds Castle</strong> is het best geregeld: een gratis
    toegankelijk busje dat de hele dag rijdt, invalidenparkeren op maximaal
    honderd meter daarvan, en rolstoelen gratis te leen.
    <strong>Aylesford Priory</strong> en de <strong>Great Stour Way</strong> zijn
    vlak. <strong>Ightham Mote</strong> heeft een gelijkvloerse ingang en café.
    <strong>Chartwell</strong> is het lastigst: 250 meter over een steil pad met
    24 treden, met een busje dat niet elke dag rijdt. In <strong>Chilham</strong>
    klimmen vier steile straatjes naar het plein — parkeer boven.</p>
  </div>

  <div class="rule" style="margin-top:5mm"></div>
  <div class="label">Foto&rsquo;s</div>
  <div class="prose" style="margin-top:2mm">
    <p>Alle foto&rsquo;s in dit boekje komen van Wikimedia Commons en staan onder
    een Creative Commons-licentie of in het publieke domein. De fotograaf en de
    licentie horen bij de foto te blijven staan — daarom staan ze erbij.</p>
  </div>
  <div class="credits">{creds}</div>
  <div class="prose" style="margin-top:3mm">
    <p style="font-size:8.4pt">Kaarten: kaartgegevens &copy;
    OpenStreetMap-bijdragers, onder de Open Database License. De rode routelijn
    en de nummers zijn van ons, over hun kaart heen getekend.</p>
  </div>
  <div class="folio left">{folio}</div>
</section>'''


def build_html(days, maps, ov, ph):
    css = open(os.path.join(ROUTEBOOK, 'style.css')).read()
    css += '\n' + open(os.path.join(HERE, 'crew.css')).read()

    pages = [page_cover(ph), page_overview(ov, ph), page_hotels(ph),
             page_windows()]
    folio = 5
    # Thursday is only an arrival, so it shares the spread with the windows page
    # and gets the hotel photograph rather than a map it does not need.
    thursday_extra = f'''
  <div class="photo-grid" style="margin-top:6mm">
    {photo_card(ph.get('whyte_harte'), 'The Whyte Harte, Bletchingley',
                'Een 16e-eeuwse herberg aan de High Street. Hier komen de lopers '
                'aan het eind van hun eerste dag binnen.')}
    {photo_card(ph.get('charing'), 'Wat er de komende dagen aankomt',
                'Het Archbishop’s Palace in Charing, zondagochtend. Achthonderd '
                'jaar lang stopten pelgrims hier op weg naar Canterbury.')}
  </div>
  <div class="prose" style="margin-top:5mm">
    <p>Morgen begint het echte programma. Op de volgende pagina&rsquo;s staat per
    dag wat er te zien is, waar jullie de lopers kunnen opvangen, en hoe lang het
    rijden is. <strong>Elke dag om 16:00 in het volgende hotel</strong> — behalve
    zondag, want dan gaat het na de finish door naar de tunnel.</p>
  </div>'''
    pages.append(page_day(days[0], None, ph, folio, extra=thursday_extra))
    folio += 1
    for day, places in ((days[1], page_day2_places),
                        (days[2], page_day3_places),
                        (days[3], page_day4_places)):
        assert folio % 2 == 0, f'dag {day["n"]} kaartpagina op recto {folio}'
        pages.append(page_day(day, maps.get(day['n']), ph, folio))
        pages.append(places(ph, folio + 1))
        folio += 2
    pages.append(page_practical(ph, folio))

    return f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<title>Kent met de auto — boekje voor de ploeg</title>
<style>{css}</style>
</head><body>
{''.join(pages)}
</body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-maps', action='store_true')
    ap.add_argument('--open', action='store_true')
    args = ap.parse_args()

    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    print('Foto’s van Commons…')
    ph = gather_photos()
    print('Kaarten…')
    # The Holiday Inn has no free photograph, so it gets a locator map instead.
    for h in HOTELS:
        if h['photo'] or 'at' not in h:
            continue
        lat, lon = h['at']
        lm = point_map(lat, lon, f'maps/hotel-{h["slug"]}.jpg',
                       no_maps=args.no_maps)
        lm['svg'] = point_marker_svg(lm, lat, lon)
        h['locator'] = lm

    ov = overview_map(DAYS, no_maps=args.no_maps)
    maps = {}
    for day in DAYS:
        m = day_map(day, no_maps=args.no_maps)
        if m:
            maps[day['n']] = m

    html_path = os.path.join(OUT, 'ploegboekje.html')
    with open(html_path, 'w') as f:
        f.write(build_html(DAYS, maps, ov, ph))
    print(f'  {html_path}')

    pdf_path = os.path.join(OUT, 'kent-met-de-auto.pdf')
    chrome = find_chrome()
    if not chrome:
        print('  ! geen Chrome gevonden', file=sys.stderr)
        return
    subprocess.run([chrome, '--headless', '--disable-gpu', '--no-sandbox',
                    '--no-pdf-header-footer',
                    '--run-all-compositor-stages-before-draw',
                    '--virtual-time-budget=15000',
                    f'--print-to-pdf={pdf_path}', f'file://{html_path}'],
                   capture_output=True, text=True, timeout=300)
    if os.path.exists(pdf_path):
        print(f'  {pdf_path} ({os.path.getsize(pdf_path) // 1024} KB)')
        if args.open:
            subprocess.run(['open', pdf_path])


if __name__ == '__main__':
    main()
