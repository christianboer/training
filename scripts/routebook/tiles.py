#!/usr/bin/env python3
"""Stitch a raster basemap for a route map.

Only the basemap is raster. The route line, the markers and every label are
drawn as SVG over the image in the routebook HTML, so they stay vector-crisp at
print resolution. That is why `build_basemap` also writes a JSON sidecar with
the projection: the image is cropped to exactly the requested bounding box, so
placing a coordinate is `(mercator(lat, lon) - origin) * scale`.

Tiles are fetched with curl because this environment's TLS proxy breaks
python's urllib (same reason as scripts/route_photos/mvt.py), and are cached on
disk so re-rendering the book costs no requests at all.
"""
import json
import math
import os
import subprocess
import sys
import time

TILE = 256
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cache', 'tiles')

# A route book wants a calm, legible basemap. OpenTopoMap carries contour lines
# and rights of way, which is what you actually want on the North Downs.
SOURCES = {
    'opentopomap': {
        'url': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        'subdomains': ['a', 'b', 'c'],
        'max_zoom': 16,
        'attribution': 'Kaart: © OpenStreetMap-bijdragers, SRTM · '
                       'weergave © OpenTopoMap (CC BY-SA)',
    },
    'osm': {
        'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        'subdomains': [],
        'max_zoom': 19,
        'attribution': 'Kaart: © OpenStreetMap-bijdragers (ODbL)',
    },
    'cyclosm': {
        'url': 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
        'subdomains': ['a', 'b', 'c'],
        'max_zoom': 18,
        'attribution': 'Kaart: © OpenStreetMap-bijdragers · weergave CyclOSM',
    },
}

USER_AGENT = ('PilgrimsWayRoutebook/1.0 (personal 4-day walk route book; '
              'contact c.boer@blisdigital.com)')


# --- Web Mercator ---------------------------------------------------------
# Normalised to the unit square, so x and y share one scale and the aspect
# ratio of a bounding box in these units *is* its aspect ratio in pixels.

def mercator(lat, lon):
    x = (lon + 180.0) / 360.0
    s = math.sin(math.radians(max(-85.05, min(85.05, lat))))
    y = 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    return x, y


def inverse_mercator(x, y):
    lon = x * 360.0 - 180.0
    lat = math.degrees(2 * math.atan(math.exp((0.5 - y) * 2 * math.pi)) - math.pi / 2)
    return lat, lon


def bounds_of(coords, pad=0.08, aspect=None):
    """Bounding box in mercator units around (lat, lon) pairs.

    `pad` is a fraction of the larger span, so the padding looks even. With
    `aspect` (width / height) the box is grown — never cropped — on whichever
    axis is too small, so the finished image fits its layout slot without
    distortion and without losing any of the route.
    """
    xs, ys = zip(*(mercator(lat, lon) for lat, lon in coords))
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    margin = pad * max(x1 - x0, y1 - y0)
    x0, x1, y0, y1 = x0 - margin, x1 + margin, y0 - margin, y1 + margin

    if aspect:
        w, h = x1 - x0, y1 - y0
        if w / h < aspect:          # too tall for the slot: widen
            need = h * aspect - w
            x0, x1 = x0 - need / 2, x1 + need / 2
        else:                        # too wide: heighten
            need = w / aspect - h
            y0, y1 = y0 - need / 2, y1 + need / 2
    return x0, y0, x1, y1


def pick_zoom(bounds, target_px, max_zoom, aspect=1.75, max_tiles=260):
    """Finest zoom that still renders at least `target_px` wide within the tile
    budget. Zoom levels double, so this normally overshoots and the stitched
    image is scaled back down — which supersamples the map's own labels and is
    the reason the printed page looks sharp.

    Overshooting matters for content too, not just pixels: OpenTopoMap only
    starts labelling hamlets around z13, and on a route book the village names
    are half the point.
    """
    x0, _, x1, _ = bounds
    span = x1 - x0
    z = int(math.ceil(math.log2(target_px / (span * TILE))))
    z = max(1, min(max_zoom, z))
    while z > 1:
        w = span * TILE * 2 ** z
        if (w / TILE + 1) * (w / aspect / TILE + 1) <= max_tiles:
            break
        z -= 1
    return z


# --- tiles ----------------------------------------------------------------

FAIL_TTL = 7 * 24 * 3600      # how long to trust that a tile is broken


def tile_paths(source, z, x, y):
    p = os.path.join(CACHE_DIR, source, str(z), str(x), f'{y}.png')
    return p, p + '.failed'


def fetch_tile(source, z, x, y, pace=0.08, retries=2, timeout=12):
    """A tile, from cache or from the server.

    Two deliberate cheats, both about not waiting:

    The timeout is short. OpenTopoMap renders on demand and a stuck tile does not
    recover on a retry — it hangs again — so failing fast and handing the job to
    the parent-tile fallback beats three thirty-second waits.

    Failures are cached too. Some tiles are broken for good, and without a marker
    on disk every rebuild pays for them again: once in the parallel prefetch and
    then a second time, serially, in the stitch loop. That is how a two-minute
    build became a ten-minute one. Delete the .failed markers to retry them.
    """
    src = SOURCES[source]
    n = 2 ** z
    if not (0 <= x < n and 0 <= y < n):
        return None
    path, failed = tile_paths(source, z, x, y)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    if (os.path.exists(failed)
            and time.time() - os.path.getmtime(failed) < FAIL_TTL):
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)

    subs = src['subdomains']
    url = src['url'].replace('{z}', str(z)).replace('{x}', str(x)).replace('{y}', str(y))
    if subs:
        url = url.replace('{s}', subs[(x + y) % len(subs)])

    for attempt in range(retries):
        time.sleep(pace * (1 + 3 * attempt))
        r = subprocess.run(
            ['curl', '-sfL', '--compressed', '--max-time', str(timeout),
             '-A', USER_AGENT, '-o', path, url],
            capture_output=True)
        if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    if os.path.exists(path):
        os.remove(path)
    open(failed, 'w').close()
    print(f'    ! tile {z}/{x}/{y} failed', file=sys.stderr)
    return None


def prefetch(source, z, xs, ys, workers=4, quiet=False):
    """Warm the cache for a whole tile rectangle, several requests at a time.

    About a fifth of OpenTopoMap's tiles around Canterbury never render and hold
    the connection open until it times out. Fetched one at a time that is ten
    minutes of dead waiting per map; four at a time it is two. Four, not forty:
    they are a volunteer project and the point is to stop blocking, not to hammer
    them.
    """
    from concurrent.futures import ThreadPoolExecutor

    jobs = [(x, y) for x in xs for y in ys
            if not any(os.path.exists(p) for p in tile_paths(source, z, x, y))]
    if not jobs:
        return
    if not quiet:
        print(f'    fetching {len(jobs)} tiles ({workers} at a time)…')
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda j: fetch_tile(source, z, j[0], j[1]), jobs))


def tile_image(source, z, x, y, _depth=0):
    """The tile as a PIL image, falling back to the parent tile when a render
    fails. OpenTopoMap renders on demand and a few tiles time out on their side
    for good; the parent quadrant upscaled is slightly soft but keeps the map
    one consistent style, which a single tile from another basemap would not.
    """
    from PIL import Image

    p = fetch_tile(source, z, x, y)
    if p:
        try:
            with Image.open(p) as t:
                return t.convert('RGB')
        except Exception as e:
            print(f'    ! unreadable {p}: {e}', file=sys.stderr)
            os.remove(p)
    if _depth >= 2 or z <= 1:
        return None
    parent = tile_image(source, z - 1, x // 2, y // 2, _depth + 1)
    if parent is None:
        return None
    half = TILE // 2
    box = ((x % 2) * half, (y % 2) * half, (x % 2) * half + half, (y % 2) * half + half)
    return parent.crop(box).resize((TILE, TILE), Image.LANCZOS)


def build_basemap(coords, out_png, aspect=1.75, target_px=2400, pad=0.08,
                  source='opentopomap', desaturate=0.62, brighten=1.07,
                  quiet=False):
    """Stitch the basemap covering `coords` and write `out_png` plus a JSON
    sidecar describing the projection. Returns the metadata dict.

    The tiles are muted a little on the way out: a route book reads better when
    the terrain sits back and the route line is the only saturated thing on the
    page.
    """
    from PIL import Image, ImageEnhance

    src = SOURCES[source]
    bounds = bounds_of(coords, pad=pad, aspect=aspect)
    z = pick_zoom(bounds, target_px, src['max_zoom'], aspect=aspect)
    x0, y0, x1, y1 = bounds

    scale = TILE * 2 ** z                      # pixels per mercator unit
    px0, py0, px1, py1 = x0 * scale, y0 * scale, x1 * scale, y1 * scale
    tx0, ty0 = int(math.floor(px0 / TILE)), int(math.floor(py0 / TILE))
    tx1, ty1 = int(math.floor(px1 / TILE)), int(math.floor(py1 / TILE))
    cols, rows = tx1 - tx0 + 1, ty1 - ty0 + 1

    if not quiet:
        print(f'  {os.path.basename(out_png)}: z{z}, {cols}x{rows} tiles '
              f'({cols * rows}), {round(px1 - px0)}x{round(py1 - py0)} px')

    prefetch(source, z, range(tx0, tx1 + 1), range(ty0, ty1 + 1), quiet=quiet)

    canvas = Image.new('RGB', (cols * TILE, rows * TILE), (244, 242, 236))
    missing = 0
    for cx in range(cols):
        for cy in range(rows):
            img = tile_image(source, z, tx0 + cx, ty0 + cy)
            if img is None:
                missing += 1
                continue
            canvas.paste(img, (cx * TILE, cy * TILE))

    crop = canvas.crop((round(px0) - tx0 * TILE, round(py0) - ty0 * TILE,
                        round(px1) - tx0 * TILE, round(py1) - ty0 * TILE))
    if crop.width > target_px:
        # Scale back to the size the page actually needs. LANCZOS down from a
        # finer zoom is what makes the map's own type look printed rather than
        # screenshotted.
        crop = crop.resize((target_px, round(crop.height * target_px / crop.width)),
                           Image.LANCZOS)
    if desaturate != 1.0:
        crop = ImageEnhance.Color(crop).enhance(desaturate)
    if brighten != 1.0:
        crop = ImageEnhance.Brightness(crop).enhance(brighten)

    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    crop.save(out_png, 'JPEG', quality=88, optimize=True)

    # Fold the downscale into the projection, so `projector()` maps straight to
    # pixels of the image as saved rather than of the stitched original.
    f = crop.width / (px1 - px0)

    meta = {
        'png': os.path.basename(out_png),
        'width': crop.width,
        'height': crop.height,
        'zoom': z,
        'origin_px': [px0 * f, py0 * f],
        'scale': scale * f,
        'bounds': {'west': inverse_mercator(x0, y0)[1],
                   'north': inverse_mercator(x0, y0)[0],
                   'east': inverse_mercator(x1, y1)[1],
                   'south': inverse_mercator(x1, y1)[0]},
        'source': source,
        'attribution': src['attribution'],
        'tiles': cols * rows,
        'missing_tiles': missing,
    }
    with open(os.path.splitext(out_png)[0] + '.json', 'w') as f:
        json.dump(meta, f, indent=1)
    if missing:
        print(f'    ! {missing} of {cols * rows} tiles missing', file=sys.stderr)
    return meta


def projector(meta):
    """-> f(lat, lon) = (x, y) in image pixels, for the SVG overlay."""
    ox, oy = meta['origin_px']
    scale = meta['scale']

    def project(lat, lon):
        x, y = mercator(lat, lon)
        return x * scale - ox, y * scale - oy
    return project


if __name__ == '__main__':
    import glob
    from gpxread import read_stage
    gpx = sys.argv[1] if len(sys.argv) > 1 else glob.glob(
        os.path.join(BASE_DIR, '../../plan/stages/stage1-*.gpx'))[0]
    stage = read_stage(gpx)
    out = os.path.join(BASE_DIR, 'cache', 'test-map.jpg')
    m = build_basemap([(p[0], p[1]) for p in stage['points']], out)
    print(json.dumps({k: v for k, v in m.items() if k != 'bounds'}, indent=1))
