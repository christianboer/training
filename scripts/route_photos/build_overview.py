"""Build a local HTML contact sheet of route photos, positioned along the stage profile.

Usage: python3 build_overview.py <stage.gpx> <photodir> <stage title>
Writes <photodir>/index.html referencing the downloaded images relatively.
"""
import datetime
import html
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}


def profile(gpx_path, n=240):
    root = ET.parse(gpx_path).getroot()
    # Not every GPX carries elevation on every point — carry the last known value
    # forward rather than dropping to sea level and drawing a cliff.
    pts = []
    last_ele = 0.0
    for p in root.findall('.//gpx:trkpt', NS):
        el = p.find('gpx:ele', NS)
        if el is not None and el.text:
            last_ele = float(el.text)
        pts.append((float(p.attrib['lat']), float(p.attrib['lon']), last_ele))

    def hav(a, b, c, d):
        R = 6371000
        dlat, dlon = math.radians(c - a), math.radians(d - b)
        h = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(a)) *
             math.cos(math.radians(c)) * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))

    dist = [0.0]
    for i in range(1, len(pts)):
        dist.append(dist[-1] + hav(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]))
    step = max(1, len(pts) // n)
    return [(dist[i] / 1000, pts[i][2]) for i in range(0, len(pts), step)] + \
           [(dist[-1] / 1000, pts[-1][2])]


def run(gpx, photodir, title):
    photos = json.load(open(os.path.join(photodir, 'manifest.json')))
    # Prefer the downloaded file; fall back to Strava's CDN when it isn't there,
    # so the sheet still works after the images have been cleaned up.
    local = 0
    for p in photos:
        if os.path.exists(os.path.join(photodir, p.get('file', ''))):
            p['_src'] = p['file']
            local += 1
        else:
            p['_src'] = p.get('url') or p.get('full_url', '')
    photos = [p for p in photos if p['_src']]
    prof = profile(gpx)
    max_km = prof[-1][0]
    eles = [e for _, e in prof]
    lo, hi = min(eles) - 15, max(eles) + 25
    flat = max(eles) - min(eles) < 1  # GPX without elevation: say so, don't fake a profile

    W, H = 1200, 170
    px = lambda km: 40 + km / max_km * (W - 70)
    py = lambda e: 15 + (hi - e) / (hi - lo) * (H - 45)
    line = 'M ' + ' L '.join(f'{px(k):.1f},{py(e):.1f}' for k, e in prof)
    area = line + f' L {px(max_km):.1f},{H - 30:.1f} L 40,{H - 30:.1f} Z'

    marks = '\n'.join(
        f'<g class="mk" data-i="{i}"><line x1="{px(p["route_km"]):.1f}" y1="15" '
        f'x2="{px(p["route_km"]):.1f}" y2="{H-30}" /><circle cx="{px(p["route_km"]):.1f}" '
        f'cy="{H-30}" r="3.5"/></g>'
        for i, p in enumerate(photos))

    ticks = '\n'.join(
        f'<text x="{px(k):.1f}" y="{H-12}" text-anchor="middle" class="ax">{k}</text>'
        for k in range(0, int(max_km) + 1, 5))

    cards = []
    for i, p in enumerate(photos):
        ts = p.get('timestamp')
        date = (datetime.datetime.fromtimestamp(int(ts) / 1000).strftime('%b %Y')
                if ts else '')
        cards.append(f'''<figure class="card" id="p{i}">
  <img src="{html.escape(p['_src'])}" alt="Route photo at km {p['route_km']}" loading="lazy">
  <figcaption><span class="km">km {p['route_km']:.1f}</span>
  <span class="meta">{html.escape(date)} · {p['offset_m']} m van de route</span></figcaption>
</figure>''')

    doc = f'''<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — routefoto's</title>
<style>
  :root {{ --bg:#0f172a; --card:#1e293b; --border:#334155; --text:#e2e8f0;
           --muted:#94a3b8; --accent:#f97316; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
         font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  header {{ padding:28px 32px 8px; }}
  h1 {{ margin:0 0 4px; font-size:1.6rem; }}
  .sub {{ color:var(--muted); font-size:.9rem; }}
  .profile {{ padding:8px 32px 20px; }}
  svg {{ width:100%; height:auto; display:block; }}
  .fill {{ fill:var(--accent); fill-opacity:.12; }}
  .stroke {{ fill:none; stroke:var(--accent); stroke-width:2; }}
  .mk line {{ stroke:#38bdf8; stroke-width:1; opacity:.35; }}
  .mk circle {{ fill:#38bdf8; cursor:pointer; }}
  .mk:hover circle {{ fill:#fff; r:5; }}
  .ax {{ fill:var(--muted); font-size:11px; font-family:ui-monospace,monospace; }}
  .grid {{ display:grid; gap:16px; padding:0 32px 48px;
           grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }}
  .card {{ margin:0; background:var(--card); border:1px solid var(--border);
           border-radius:10px; overflow:hidden; scroll-margin-top:20px; }}
  .card img {{ width:100%; aspect-ratio:3/4; object-fit:cover; display:block;
               cursor:zoom-in; }}
  figcaption {{ padding:8px 10px; display:flex; flex-direction:column; gap:2px; }}
  .km {{ font-family:ui-monospace,monospace; color:var(--accent); font-size:.85rem; }}
  .meta {{ color:var(--muted); font-size:.75rem; }}
  .card:target {{ outline:2px solid var(--accent); }}
  dialog {{ border:none; background:transparent; padding:0; max-width:96vw; }}
  dialog::backdrop {{ background:rgba(0,0,0,.85); }}
  dialog img {{ max-width:96vw; max-height:92vh; border-radius:8px; }}
  footer {{ color:var(--muted); font-size:.78rem; padding:0 32px 40px; max-width:70ch; }}
</style></head><body>
<header>
  <h1>{html.escape(title)}</h1>
  <div class="sub">{len(photos)} foto's langs de route · hoogste Strava-score per bucket ·
  allemaal vlak langs het pad{' · geen hoogtedata in deze GPX, de lijn is dus vlak' if flat else ''}</div>
</header>
<div class="profile">
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
  <path class="fill" d="{area}"/><path class="stroke" d="{line}"/>
  {marks}
  {ticks}
  <text x="{W-20}" y="{H-12}" text-anchor="end" class="ax">km</text>
</svg>
</div>
<div class="grid">
{chr(10).join(cards)}
</div>
<dialog id="lb"><img alt=""></dialog>
<footer>
  Foto's zijn gemaakt door andere Strava-gebruikers en komen uit de publieke
  community-photo laag van Strava's kaart. Lokaal bewaard voor routeverkenning;
  niet verspreiden of publiceren.
</footer>
<script>
  const lb = document.getElementById('lb'), lbImg = lb.querySelector('img');
  document.querySelectorAll('.card img').forEach(img => img.addEventListener('click', () => {{
    lbImg.src = img.src; lb.showModal();
  }}));
  lb.addEventListener('click', () => lb.close());
  document.querySelectorAll('.mk').forEach(g => g.addEventListener('click', () => {{
    const el = document.getElementById('p' + g.dataset.i);
    el.scrollIntoView({{behavior:'smooth', block:'center'}});
    el.style.outline = '2px solid var(--accent)';
    setTimeout(() => el.style.outline = '', 1600);
  }}));
</script>
</body></html>'''

    out = os.path.join(photodir, 'index.html')
    open(out, 'w').write(doc)
    src = 'local files' if local == len(photos) else \
          f'{local} local, {len(photos) - local} from Strava\'s CDN'
    print(f'wrote {out} ({len(photos)} photos, {src})')
    return out


def main():
    run(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == '__main__':
    main()
