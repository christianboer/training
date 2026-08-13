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
DAY_MAP_ASPECT = 2.6   # shallower than the routebook's: the list needs the page

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
             'lopers die dag binnenkomen. Zelf een middeleeuwse herberg: het '
             'uithangbord zegt 1388, al is daar wat discussie over.'},
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

# Each day: the places on offer, and the pins that mark them on the map.
#
# No times and no order — that is the whole point. The booklet says what is
# nearby, how far it is, when it is open and what it costs, and they choose. The
# only clock times in the book are the windows in which the walkers pass, which
# live on their own page because those are not theirs to pick.

DAYS = [
    {
        'n': 1, 'date': '2026-09-03', 'title': 'Aankomst in Bletchingley',
        'stage': 1, 'map': False,
        'lead': 'Een reisdag. De lopers komen in de loop van de middag bij de '
                'Whyte Harte binnen — ergens tussen kwart over een en kwart over '
                'twee. Meer dan aankomen hoeft deze dag niet.',
        'stops': [],
        'options': [
            {'n': None, 'name': 'Bletchingley zelf',
             'meta': 'de voordeur uit · gratis',
             'lines': ['Het hotel staat aan de High Street. Beschermd '
                       'dorpsgezicht, middeleeuwse gebouwen, en een kerk met een '
                       'Normandische toren van rond 1090 — de rest is grotendeels '
                       '15e-eeuws.'],
             'access': 'vlak, en zo lang of kort als je wil'},
            {'n': None, 'name': 'Godstone',
             'meta': '± 5 min · gratis',
             'lines': ['Dorpsgroen met een vijver en een paar pubs. Goed voor '
                       'een wandelingetje en een kop thee.'],
             'access': 'vlak'},
            {'n': None, 'name': 'Reigate',
             'meta': '± 10 min · winkels en cafés',
             'lines': ['Een echt stadje met winkelstraten, cafés en een park, '
                       'als er zin is in meer dan een dorp.']},
        ],
    },
    {
        'n': 2, 'date': '2026-09-04', 'title': 'Bletchingley → Wrotham Heath',
        'stage': 2, 'map': True,
        'lead': 'Van west naar oost, dezelfde richting als de lopers, en nergens '
                'meer dan een half uur rijden. Ruim genoeg voor twee of drie van '
                'deze; alles op één dag is te veel.',
        'stops': [
            ('Westerham', 51.2681, 0.0739),
            ('Ide Hill', 51.2457, 0.1312),
            ('Chartwell', 51.2447, 0.0872),
            ('Sevenoaks', 51.2720, 0.1900),
            ('Ightham Mote', 51.2761, 0.2786),
            ('West Malling', 51.2925, 0.4090),
        ],
        'options': [
            {'n': 2, 'name': 'Ide Hill', 'walkers': True,
             'meta': '<b>hier komen de lopers langs</b> · gratis',
             'lines': ['Dorpsplein met wat veel mensen het mooiste uitzicht van '
                       'Kent vinden, en de dorpswinkel waar de lopers hun '
                       'hulppost hebben. Koffie op het groen.']},
            {'n': 1, 'name': 'Westerham',
             'meta': '± 25 min van Bletchingley · gratis',
             'lines': ['Marktplein met een standbeeld van Churchill, '
                       'zelfstandige winkels, antiekzaken en cafés.'],
             'access': 'vlak'},
            {'n': 3, 'name': 'Chartwell',
             'meta': '± 10 min van Ide Hill · £ 21,60 · huis vanaf 11:00, '
                     'laatste toegang 15:40',
             'lines': ['Het huis waar Winston Churchill veertig jaar woonde, met '
                       'het uitzicht over de Weald waar hij zijn schilderijen '
                       'maakte. Er is een restaurant.',
                       'Alleen de tuin kan ook: £ 15,30.'],
             'access': '250 m van de parkeerplaats via een steil pad met 24 '
                       'treden. Er rijdt een busje, maar niet elke dag — vraag '
                       'het bij aankomst, of vraag om "drive and drop". De '
                       'wandeling langs de meren onder het huis is vlakker dan '
                       'de tuin, en een goed uur.'},
            {'n': 5, 'name': 'Ightham Mote',
             'meta': '± 10 min van het hotel · £ 19,00 · huis vanaf 11:00',
             'lines': ['Een 14e-eeuws huis met een slotgracht, een van de meest '
                       'complete middeleeuwse huizen van Engeland. Rustiger dan '
                       'Chartwell en dichter bij het hotel.'],
             'access': 'ingang en café volledig gelijkvloers. Rolstoel en '
                       'tramper te leen, vooraf reserveren'},
            {'n': 4, 'name': 'Sevenoaks, met Knole Park',
             'meta': '± 15 min · stadje gratis · park gratis',
             'lines': ['Een echt winkelstadje: de steegjes tussen High Street, '
                       'The Shambles, Bank Street en Brewery Lane zitten vol '
                       'boetieks, juweliers en cafés.',
                       'Naast het stadje ligt Knole Park, het laatste '
                       'middeleeuwse hertenpark van Kent: duizend acre — ruim '
                       'vierhonderd hectare — met zo’n 350 vrij lopende '
                       'damherten. Te voet is de toegang gratis; parkeren gaat '
                       'via een entreekaartje, dus makkelijker is de '
                       'parkeergarage in Sevenoaks en dan het park in lopen.'],
             'access': 'het park is groot en rustig van reliëf; je bepaalt zelf '
                       'hoe ver'},
        ],
        'far_label': 'Ook nog in de buurt van het hotel',
        'far': [
            {'n': 6, 'name': 'West Malling',
             'meta': '± 10 min van het hotel · gratis',
             'lines': ['Een van de mooiste High Streets van Kent: Georgian en '
                       'Victoriaanse panden, zelfstandige boetieks, antiek, '
                       'interieurwinkels en een paar goede koffiezaken. Er staat '
                       'een Normandische toren uit de vroege 12e eeuw.',
                       'Fijn voor laat in de middag, als de koffers al binnen '
                       'zijn.'],
             'access': 'vlak'},
            {'n': None, 'name': 'Emmetts Garden',
             'meta': '1 km van Ide Hill · National Trust · 7 dagen open',
             'lines': ['Een tuin met uitzicht, voor wie liever een tuin dan een '
                       'huis wil.'],
             'access': 'steile hellingen en treden. Er is een buggy voor het '
                       'steilste stuk, maar die rijdt op vrijwilligers — dezelfde '
                       'dag bellen'},
        ],
    },
    {
        'n': 3, 'date': '2026-09-05', 'title': 'Wrotham Heath → Charing Heath',
        'stage': 3, 'map': True,
        'lead': 'De rijkste dag van de vier. Een gratis klooster waar de lopers '
                'langskomen, een grafmonument van zesduizend jaar oud, een '
                'kasteel in een meer — en als het regent of als er zin is in '
                'winkelen, een outlet op twintig minuten.',
        'stops': [
            ('Aylesford Priory', 51.2972, 0.4722),
            ("Kit's Coty", 51.3172, 0.5006),
            ('Leeds Castle', 51.2486, 0.6300),
            ('Lenham', 51.2415, 0.7180),
        ],
        'options': [
            {'n': 1, 'name': 'Aylesford Priory (The Friars)', 'walkers': True,
             'meta': '<b>hier komen de lopers langs</b> · ± 15 min · gratis · '
                     '365 dagen open',
             'lines': ['Een 13e-eeuws karmelietenklooster. Terrein dag en nacht '
                       'toegankelijk, theetuin vanaf 10:00, een cadeauwinkel en '
                       'een werkende pottenbakkerij.',
                       'Het klooster ligt óp hun route, dus dit is de plek waar '
                       'jullie ze het vroegst kunnen zien.'],
             'access': 'vlak en stil. Er loopt ook een pad langs de Medway'},
            {'n': 2, 'name': "Kit's Coty House",
             'meta': '± 8 min van Aylesford · gratis · altijd',
             'lines': ['Een megalithisch grafmonument van rond 4000 v.Chr., pal '
                       'langs de weg — dus zo’n zesduizend jaar oud. Vijf '
                       'minuten kijken. Beheerd door English Heritage, en het '
                       'ligt naast de hulppost bij Bluebell Hill.'],
             'access': 'korte vlakke aanloop'},
            {'n': 3, 'name': 'Leeds Castle',
             'meta': '± 20 min · £ 34,50 online (£ 38,50 aan de poort) · park tot 18:00, kasteel tot 17:00, laatste toegang 16:00',
             'lines': ['Een kasteel op een eiland in een meer, met tweehonderd '
                       'hectare park, tuinen, een doolhof, zwarte zwanen en '
                       'meerdere eetgelegenheden. Een halve dag als je wil.'],
             'access': 'het best geregeld van alles in dit boekje. Een gratis '
                       'toegankelijk busje rijdt de hele dag, invalidenparkeren '
                       'ligt op maximaal 100 m daarvan, en rolstoelen zijn '
                       'gratis te leen. Het treintje is niet '
                       'rolstoeltoegankelijk, het busje wel'},
            {'n': 4, 'name': 'Lenham',
             'meta': '± 10 min van The Red Lion · gratis',
             'lines': ['Schilderachtig dorpsplein met een herberg uit 1602, een '
                       'tithe barn, een Grade I-kerk, een theewinkel en wat '
                       'antiek. Fijn voor laat in de middag.'],
             'access': 'vlak'},
        ],
        'far': [
            {'n': None, 'name': 'Ashford Designer Outlet',
             'meta': '± 20 min van The Red Lion · 80 tot 100 winkels · '
                     'za 09:00 – 21:00, zo 10:00 – 18:00',
             'lines': ['Als er gewinkeld moet worden, of als het regent. Het ligt '
                       'dichter bij het hotel van zaterdag dan je zou denken.'],
             'access': 'alles binnen en gelijkvloers'},
            {'n': None, 'name': 'Faversham',
             'meta': '± 25 min · gratis · zaterdagmarkt',
             'lines': ['Het oudste marktstadje van Kent, aan een getijdenkreek, '
                       'met zelfstandige winkels en Shepherd Neame — de oudste '
                       'brouwerij van Engeland, sinds 1698 op dezelfde plek.',
                       'Op zaterdag is er charter-markt, en op de eerste '
                       'zaterdag van de maand ook een ambachtenmarkt. Even '
                       'checken of dat deze zaterdag zo is.'],
             'access': 'vlak; er lopen rustige kadepaden langs de kreek'},
            {'n': None, 'name': 'Rochester',
             'meta': '± 25 min van het hotel · kathedraal op donatiebasis',
             'lines': ['Kathedraal, Normandisch kasteel en een High Street vol '
                       'Dickens, als er zin is in een stad in plaats van een '
                       'kasteel.']},
        ],
    },
    {
        'n': 4, 'date': '2026-09-06', 'title': 'Charing Heath → Canterbury → naar huis',
        'stage': 4, 'map': True,
        'lead': 'De dag van de finish. Alles gaat bij het uitchecken de auto in — '
                'ook de bagage van de lopers, want die stappen in Canterbury in. '
                'Daarna rijden jullie samen door naar Folkestone.',
        'stops': [
            ('Charing', 51.2089, 0.7906),
            ('Lenham', 51.2415, 0.7180),
            ('Chilham', 51.2444, 0.9611),
            ('Canterbury', 51.2777, 1.0740),
        ],
        'options': [
            {'n': 3, 'name': 'Chilham', 'walkers': True,
             'meta': '<b>hier komen de lopers langs</b> · ± 20 min · gratis · '
                     'theehuis 09:30 – 16:30',
             'lines': ['Een middeleeuws dorpsplein met Tudor-vakwerkhuizen, een '
                       '16e-eeuwse kerk en het kasteel. Aan het plein zit The '
                       'Church Mouse Tea Rooms, de hulppost van de lopers: '
                       'koffie met scones terwijl zij door het dorp komen.',
                       'De kasteeltuinen zijn alleen op dinsdag en donderdag '
                       'open, dus vandaag niet.'],
             'access': 'vier smalle, steile straatjes klimmen naar het plein — '
                       'parkeer zo dicht bij het plein als het kan'},
            {'n': 1, 'name': 'Charing',
             'meta': 'naast het hotel · gratis',
             'lines': ['Aan de Pilgrims’ Way. De ruïne van het Archbishop’s '
                       'Palace gaat terug tot de achtste eeuw en was een '
                       'pleisterplaats voor pelgrims op weg naar Canterbury — '
                       'precies de rol die jullie deze week vervullen.'],
             'access': 'vlak'},
            {'n': 2, 'name': 'Lenham',
             'meta': '± 10 min · gratis',
             'lines': ['Als Charing te klein voelt: het dorpsplein van Lenham '
                       'met de theewinkel. Let op dat zondagse openingstijden '
                       'kort zijn.'],
             'access': 'vlak'},
            {'n': 4, 'name': 'Canterbury',
             'meta': 'kathedraal £ 19,50 · zondag: kerk vanaf 12:30, laatste '
                     'toegang 16:00',
             'lines': ['De kathedraal waar dit pad achthonderd jaar naartoe '
                       'loopt, de oude straatjes voor het winkelen, de Westgate '
                       'Towers, en punteren over de Stour.',
                       'Kaartjes voor de kathedraal kunnen aan de deur.'],
             'access': 'grotendeels gelijkvloers; de krypte en de trap naar het '
                       'koor hebben treden'},
        ],
    },
]


# Wetenswaardigheden, in Dutch.
#
# The routebook carries these in English because they are verbatim Wikipedia. The
# crew booklet cannot: one of its two readers does not read English. So they are
# translated here — and a translation is legally a derivative work, which is why
# each item names its article, the page says the translation is ours, and the
# translations themselves go out under the same CC BY-SA 4.0. Attribution plus
# "indicate what changed" plus share-alike is the whole of the licence; dropping
# any of the three is not an option.
#
# Only figures were converted (feet and miles to metres and kilometres). Nothing
# was added, and where a source is vague the translation stays vague.

FACTS = [
    ('Donderdag &middot; Bletchingley', [
        ('Bletchingley', 'Bletchingley',
         'Bletchingley (vroeger &ldquo;Blechingley&rdquo;) is een dorp in Surrey. '
         'Het ligt aan de A25 ten oosten van Redhill en ten westen van Godstone, '
         'heeft een beschermd dorpsgezicht met middeleeuwse gebouwen en ligt '
         'grotendeels op een brede steilrand van de Greensand Ridge, die door de '
         'Greensand Way wordt gevolgd.'),
    ]),
    ('Vrijdag &middot; tussen Bletchingley en Wrotham Heath', [
        ('Ide Hill', 'Ide Hill',
         'Ide Hill is een dorp in de gemeente Sundridge met Ide Hill, in het '
         'district Sevenoaks in Kent. Het ligt op een van de hoogste punten van '
         'de Greensand Ridge, ongeveer drie mijl (vijf kilometer) zuidwestelijk '
         'van Sevenoaks.'),
        ('One Tree Hill en Bitchet Common', 'One Tree Hill and Bitchet Common',
         'One Tree Hill en Bitchet Common is een gebied van 79,2 hectare met de '
         'status van biologisch Site of Special Scientific Interest, ten oosten '
         'van Sevenoaks in Kent. Het ligt in het Kent Downs Area of Outstanding '
         'Natural Beauty, en One Tree Hill wordt beheerd door de National Trust. '
         'Er staat gemengd bos op de Lower Greensand, deels van oude oorsprong.'),
    ]),
    ('Zaterdag &middot; tussen Wrotham Heath en Charing Heath', [
        ('Aylesford Priory', 'Aylesford Priory',
         'Aylesford Priory, of &ldquo;The Friars&rdquo;, werd gesticht in 1242, '
         'toen leden van de karmelietenorde vanuit de berg Karmel in het Heilige '
         'Land in Engeland aankwamen. Richard de Grey, een kruisvaarder, '
         'steunde hen en droeg de orde een stuk land over op zijn landgoed in '
         'Aylesford in Kent.'),
        ("Kit's Coty House", "Kit's Coty House",
         'Kit&rsquo;s Coty House of Kit&rsquo;s Coty is een langgraf met '
         'grafkamer bij het dorp Aylesford in het zuidoosten van Kent. Het werd '
         'rond 4000 v.Chr. gebouwd, in het vroege neolithicum van de Britse '
         'prehistorie, en is vandaag in ruïneuze staat bewaard.'),
        ('White Horse Stone', 'White Horse Stone',
         'De White Horse Stone is de naam van twee afzonderlijke '
         'sarsen-megalieten op de flanken van Blue Bell Hill, bij het dorp '
         'Aylesford in het zuidoosten van Kent. De Lower White Horse Stone werd '
         'vóór 1834 verwoest; op dat moment nam de overgebleven Upper White '
         'Horse Stone de naam en de bijbehorende volksverhalen over.'),
        ('Lenham Cross', 'Lenham Cross',
         'Het Lenham Cross is een krijtkruis dat is uitgesneden in de heuvelflank '
         'ten noorden van Lenham in Kent. Het Latijnse kruis is 61 meter hoog, '
         'met armen van 21 meter breed.'),
    ]),
    ('Zondag &middot; tussen Charing Heath en Canterbury', [
        ("Archbishop's Palace, Charing", "Archbishop's Palace, Charing",
         'Archbishop&rsquo;s Palace in Charing is een beschermd monument in '
         'Charing, Kent. Het paleis is een belangrijke erfgoedplek die teruggaat '
         'tot de achtste eeuw, en een van de eerste die eigendom was van het '
         'aartsbisdom Canterbury.'),
        ("All Saints' Church, Boughton Aluph", "All Saints' Church, Boughton Aluph",
         'All Saints&rsquo; Church is een 13e-eeuwse pelgrimskerk in Boughton '
         'Aluph bij Ashford, Kent, met de monumentenstatus Grade&nbsp;I. De kerk '
         'hoort bij de Church of England.'),
        ("Julliberrie's Grave", "Julliberrie's Grave",
         'Julliberrie&rsquo;s Grave, ook bekend als The Giant&rsquo;s Grave of '
         'The Grave, is een langgraf zónder grafkamer bij het dorp Chilham in het '
         'zuidoosten van Kent. Het is vermoedelijk gebouwd in het vierde '
         'millennium v.Chr., tijdens het vroege neolithicum van Groot-Brittannië, '
         'en is vandaag alleen als ruïne bewaard.'),
        ('Westgate, Canterbury', 'Westgate, Canterbury',
         'De Westgate is een middeleeuws poortgebouw in Canterbury, Kent. Deze 18 '
         'meter hoge westelijke poort van de stadsmuur is de grootste bewaard '
         'gebleven stadspoort van Engeland.'),
        ('Canterbury Cathedral', 'Canterbury Cathedral',
         'Canterbury Cathedral is de kathedraal van de aartsbisschop van '
         'Canterbury, de geestelijk leider van de Church of England en '
         'symbolisch leider van de wereldwijde Anglicaanse Gemeenschap. De '
         'kathedraal staat in Canterbury, Kent, op de plek van een van de oudste '
         'christelijke bouwwerken van Engeland, en maakt deel uit van een '
         'werelderfgoedlocatie.'),
    ]),
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
    <p><strong>Dit is geen programma.</strong> Per dag staat een handvol plekken
    waar jullie uit kunnen kiezen, met hoe ver het is, wanneer het open is en wat
    het kost. Twee of drie op een dag is ruim; alles is te veel. Wat jullie
    overslaan, slaan jullie over.</p>
    <p>Het enige dat wel vastligt: de bagage moet ’s middags bij het volgende
    hotel zijn, en op zondag rijden we na de finish samen door naar Folkestone.</p>
    <p>De genummerde bolletjes op de dagkaarten komen terug in de lijst ernaast.
    Er staat geen autoroute op de kaart — die zou een weg verzinnen die er
    misschien niet is; de nummers wijzen de plekken aan, de navigatie doet de
    rest.</p>
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
    <div class="sub">Alleen als jullie ze willen zien. Een venster, geen
      tijdstip — en eerder vroeg dan laat.</div>
  </div>
  <table class="windows">
    <thead><tr><th></th><th>Plek</th><th class="r">Bij km</th>
      <th class="r">Reken op</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="prose" style="margin-top:6mm">
    <p>Dit is de enige pagina met klokken erop, en die zijn niet van jullie maar
    van hen. Ze gaan uit van <strong>vertrek om 8:00</strong> en zijn de looptijd
    volgens het plan, met wat marge voor pauzes. Vertrekken ze later, schuift
    alles even ver mee.</p>
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


def render_options(opts):
    """The menu markup, shared by the day pages and the 'further afield' blocks."""
    items = []
    for opt in opts:
        num = (f'<div class="n">{opt["n"]}</div>' if opt.get('n')
               else '<div class="n blank">&middot;</div>')
        body = ''.join(f'<p>{p}</p>' for p in opt['lines'])
        access = (f'<div class="access">{opt["access"]}</div>'
                  if opt.get('access') else '')
        items.append(f'''
    <div class="option{' walkers' if opt.get('walkers') else ''}">
      {num}
      <div class="what">
        <h4>{esc(opt['name'])}</h4>
        <div class="meta">{opt['meta']}</div>
        {body}{access}
      </div>
    </div>''')
    return ''.join(items)


def far_block(day):
    """Options that are a real detour live on the facing page: on the day page
    they would push the list off the bottom, and they are not on the corridor the
    map shows anyway."""
    if not day.get('far'):
        return ''
    return f'''
  <div class="label" style="margin-top:6mm">{esc(day.get('far_label',
      'Verder weg, voor een grotere dag'))}</div>
  <div class="options">{render_options(day['far'])}</div>'''


def page_day(day, m, ph, folio, extra=''):
    """One day as a menu. The walkers' stop is listed first and shaded, because
    it is the only item with a moment attached to it."""
    items = render_options(day['options'])

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
  <div class="label" style="margin-top:5mm">Waar je uit kunt kiezen</div>
  <div class="options">{items}</div>
  {extra}
  <div class="folio {'left' if folio % 2 == 0 else 'right'}">{folio}</div>
</section>'''


def page_day2_places(ph, folio, day=None):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Vrijdag &middot; hoe het eruitziet</h3>
    <span class="of">Bletchingley &rarr; Wrotham Heath</span>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('westerham'), 'Westerham',
                'Het marktplein, met de Tudor-panden en de winkels erachter.')}
    {photo_card(ph.get('chartwell'), 'Chartwell',
                'Het huis gezien over de tuinterrassen. Onder de tuin liggen de '
                'meren, met een vlakker pad eromheen.')}
  </div>
  <div class="callout">
    <span class="label">Als jullie er één uitkiezen</span>
    <h3>Chartwell of Ightham Mote</h3>
    <p>Twee huizen op één dag kost samen ruim tachtig pond, en dat hoeft niet.
    Chartwell is het bezoek waar je het over gaat hebben; Ightham Mote is
    rustiger, gelijkvloers en tien minuten van het hotel. Beide staan op de
    vorige pagina met wat ze kosten en hoe het lopen is.</p>
    <p>En als er die dag helemaal geen huis in zit: Westerham, Sevenoaks en
    West Malling zijn gratis, en met Knole Park heb je zo een uur gewandeld.</p>
  </div>
  {far_block(day) if day else ''}
  <div class="folio right">{folio}</div>
</section>'''


def page_day3_places(ph, folio, day=None):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Zaterdag &middot; hoe het eruitziet</h3>
    <span class="of">Wrotham Heath &rarr; Charing Heath</span>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('leeds'), 'Leeds Castle', 'Op een eiland in het meer, met '
                'tweehonderd hectare park eromheen.', wide=True)}
    {photo_card(ph.get('aylesford'), 'Aylesford Priory',
                'De binnenhof. Gratis, vlak en stil — en het ligt op hun route.')}
    {photo_card(ph.get('kits_coty'), "Kit's Coty House",
                'Drie staande stenen en een deksteen, zo’n zesduizend jaar oud.')}
  </div>
  {far_block(day) if day else ''}
  <div class="folio right">{folio}</div>
</section>'''


def page_day4_places(ph, folio, day=None):
    return f'''
<section class="page">
  <div class="recto-head">
    <h3>Zondag &middot; het laatste stuk</h3>
    <span class="of">Charing Heath &rarr; Canterbury</span>
  </div>
  <div class="callout" style="margin-top:4mm">
    <span class="label">Als jullie één ding uit dit boekje doen</span>
    <h3>Loop de laatste kilometers mee</h3>
    <p>Vanaf <strong>Westgate Gardens</strong> loopt de <strong>Great Stour
    Way</strong> langs de rivier de stad uit — vlak en verhard. En de lopers komen
    precies over dat pad binnen, via Chartham.</p>
    <p>Dus: parkeer bij Westgate, loop het pad op langs het water, en kom ze
    tegemoet. Ze zijn daar tussen <strong>kwart over twaalf en kwart voor
    een</strong>. Loop dan met ze de laatste twee of drie kilometer de stad in —
    voor jullie is dat vijf à zes kilometer over vlak pad, en dan komt iedereen
    samen te voet in Canterbury aan, na 170 kilometer.</p>
    <p>Liever niet wandelen? Ga bij de <strong>Westgate Towers</strong> staan en
    wacht ze daar op.</p>
  </div>
  <div class="photo-grid">
    {photo_card(ph.get('stour'), 'De Great Stour bij Canterbury',
                'Het pad waarover ze binnenkomen.')}
    {photo_card(ph.get('cathedral'), 'De kathedraal',
                'Op zondag gaat de kerk zelf om 12:30 open, dus dat valt mooi '
                'achter de finish.')}
  </div>
  <div class="callout" style="margin-top:4mm">
    <span class="label">Het enige waar de klok wel telt</span>
    <h3>De trein naar huis</h3>
    <p>Inchecken kan tot uiterlijk een uur voor vertrek, en op een zomerse zondag
    is anderhalf uur verstandiger. Vanuit Canterbury is het ongeveer 35 minuten
    naar de terminal. Reken dus terug vanaf de trein die geboekt is — en vul de
    <strong>Advance Passenger Information</strong> uiterlijk 24 uur vooraf in,
    want zonder dat mag je niet mee.</p>
  </div>
  <div class="folio right">{folio}</div>
</section>'''


WIKI_URL = 'https://nl.wikipedia.org/'   # unused; kept out of the page on purpose


def page_facts(groups, folio, first=False, note=''):
    """The translated snippets. `first` carries the heading; the second page
    continues without one, so the spread reads as one piece."""
    blocks = []
    for heading, items in groups:
        rows = ''.join(f'''
      <div class="fact-item">
        <h4>{esc(name)}</h4>
        <span class="km">Wikipedia: {esc(article)}</span>
        <p>{text}</p>
      </div>''' for name, article, text in items)
        blocks.append(f'''
  <div class="label" style="margin-top:5mm">{heading}</div>
  <div class="facts-grid" style="margin-top:2.5mm">{rows}</div>''')

    head = '''
  <div class="title-block">
    <div class="label">Onderweg</div>
    <h2>Wat jullie passeren</h2>
    <div class="sub">Kleine stukjes geschiedenis van de plekken waar jullie deze
      week langsrijden — dezelfde die in het boekje van de lopers staan, hier in
      het Nederlands.</div>
  </div>''' if first else '''
  <div class="recto-head">
    <h3>Wat jullie passeren</h3>
    <span class="of">vervolg</span>
  </div>'''

    return f'''
<section class="page">
  {head}
  {''.join(blocks)}
  {note}
  <div class="folio {'left' if folio % 2 == 0 else 'right'}">{folio}</div>
</section>'''


FACTS_NOTE = '''
  <div class="callout" style="margin-top:6mm">
    <span class="label">Over deze tekstjes</span>
    <h3>Waar ze vandaan komen</h3>
    <p>Het zijn vertalingen van fragmenten uit de Engelse Wikipedia, die daar
    onder de licentie <strong>CC&nbsp;BY-SA&nbsp;4.0</strong> staan. Bij elk
    stukje staat het artikel waar het uit komt.</p>
    <p>De vertaling is van ons — dat is de enige bewerking, op het omrekenen van
    voet en mijlen naar meters en kilometers na. Die licentie werkt door: ook
    deze vertalingen staan onder CC&nbsp;BY-SA&nbsp;4.0.</p>
  </div>'''


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
                'Een van de oudste herbergen van Engeland — het uithangbord '
                'zegt 1388. Hier komen de lopers aan het eind van hun eerste '
                'dag binnen.')}
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
        pages.append(places(ph, folio + 1, day=day))
        folio += 2

    # The translated snippets fill their own spread, so the day pages can stay
    # menus. Split by day group, not by count: a day should not break mid-list.
    assert folio % 2 == 0, f'wetenswaardigheden op recto {folio}'
    pages.append(page_facts(FACTS[:3], folio, first=True))
    pages.append(page_facts(FACTS[3:], folio + 1, note=FACTS_NOTE))
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
