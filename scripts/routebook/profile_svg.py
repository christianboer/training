#!/usr/bin/env python3
"""Elevation profiles as inline SVG.

Geometry only — every colour and type size comes from the routebook stylesheet,
because the SVG is inlined into the page and CSS classes reach straight into it.
That keeps one palette in one file instead of two.

All four stages are drawn on the *same* domain (0-250 m, 0-45 km) so the pages
can be compared: stage 3 should look flat next to stage 1 and stage 4 should
look short, and it only does that if the axes do not rescale per page.
"""

Y_DOMAIN = (0, 250)      # metres, shared by every stage
X_DOMAIN = (0, 45)       # kilometres, shared by every stage
Y_STEP = 50              # gridline spacing in metres
X_STEP = 5               # km tick spacing

# viewBox units. Not millimetres — CSS scales the SVG to its slot. What matters
# is that the ratio matches the printed slot (180 x 34 mm), because a viewBox
# that does not would have to be stretched to fit, and anisotropic scaling
# squashes the type and thickens the strokes on one axis only.
W, H = 1000, 189
PAD = {'left': 32, 'right': 12, 'top': 21, 'bottom': 25}


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def render(profile, waypoints=(), markers=(), x_domain=X_DOMAIN, y_domain=Y_DOMAIN,
           width=W, height=H, bands=()):
    """profile: [{km, ele}] · waypoints: [{name, type, km, ele}] ·
    markers: [{km, label, kind}] for the numbered facts ·
    bands: [{from_km, to_km, label}] to divide one profile into stages.
    """
    x0d, x1d = x_domain
    y0d, y1d = y_domain
    px0, px1 = PAD['left'], width - PAD['right']
    py0, py1 = PAD['top'], height - PAD['bottom']

    def sx(km):
        return px0 + (km - x0d) / (x1d - x0d) * (px1 - px0)

    def sy(ele):
        return py1 - (min(max(ele, y0d), y1d) - y0d) / (y1d - y0d) * (py1 - py0)

    out = [f'<svg class="profile" viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="Hoogteprofiel">']

    # stage bands, behind everything: on the whole-route profile they are what
    # lets you see one day against the next
    for i, b in enumerate(bands):
        x, xe = sx(b['from_km']), sx(b['to_km'])
        out.append(f'<g class="prof-band {"odd" if i % 2 else "even"}">'
                   f'<rect x="{x:.1f}" y="{py0:.1f}" width="{xe - x:.1f}" '
                   f'height="{py1 - py0:.1f}"/>'
                   f'<text x="{(x + xe) / 2:.1f}" y="{py0 + 15:.1f}">'
                   f'{_esc(b["label"])}</text></g>')

    # horizontal gridlines + metre labels
    out.append('<g class="prof-grid">')
    e = y0d
    while e <= y1d:
        y = sy(e)
        out.append(f'<line x1="{px0:.1f}" y1="{y:.1f}" x2="{px1:.1f}" y2="{y:.1f}"'
                   f'{" class=\"base\"" if e == y0d else ""}/>')
        out.append(f'<text class="prof-ylabel" x="{px0 - 6:.1f}" y="{y + 3.5:.1f}">'
                   f'{e}</text>')
        e += Y_STEP
    out.append('</g>')

    # km ticks
    out.append('<g class="prof-ticks">')
    k = x0d
    while k <= x1d:
        x = sx(k)
        out.append(f'<line x1="{x:.1f}" y1="{py1:.1f}" x2="{x:.1f}" y2="{py1 + 5:.1f}"/>')
        out.append(f'<text class="prof-xlabel" x="{x:.1f}" y="{py1 + 17:.1f}">{k}</text>')
        k += X_STEP
    out.append('</g>')

    # the profile itself: filled area under a stroked ridge line
    pts = [(sx(p['km']), sy(p['ele'])) for p in profile]
    ridge = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    out.append(f'<polygon class="prof-area" points="{pts[0][0]:.1f},{py1:.1f} '
               f'{ridge} {pts[-1][0]:.1f},{py1:.1f}"/>')
    out.append(f'<polyline class="prof-line" points="{ridge}"/>')

    # numbered fact markers, low on the plot so they never fight the ridge
    for m in markers:
        x = sx(m['km'])
        out.append(f'<g class="prof-marker">'
                   f'<circle cx="{x:.1f}" cy="{py1 - 9:.1f}" r="8"/>'
                   f'<text x="{x:.1f}" y="{py1 - 5.5:.1f}">{_esc(m["label"])}</text>'
                   f'</g>')

    # waypoints: hairline to the ridge, dot, label
    for w in waypoints:
        x, y = sx(w['km']), sy(w['ele'])
        kind = w.get('type', 'poi')
        anchor = ('start' if kind == 'start' else
                  'end' if kind == 'finish' else 'middle')
        dx = 5 if anchor == 'start' else -5 if anchor == 'end' else 0
        out.append(f'<g class="prof-wpt {kind}">'
                   f'<line x1="{x:.1f}" y1="{py0 - 4:.1f}" x2="{x:.1f}" y2="{y:.1f}"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5"/>'
                   f'<text x="{x + dx:.1f}" y="{py0 - 9:.1f}" text-anchor="{anchor}">'
                   f'{_esc(w["name"])}</text></g>')

    out.append('</svg>')
    return '\n'.join(out)


if __name__ == '__main__':
    import json
    import os
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')
    d = json.load(open(os.path.join(base, 'site/data/training.json')))
    s = d['course_profile']['stages'][0]
    svg = render(s['profile'], s['waypoints'],
                 markers=[{'km': 12, 'label': '1'}, {'km': 30, 'label': '2'}])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache/test-profile.html')
    with open(out, 'w') as f:
        f.write('<style>body{background:#fff;margin:40px}svg{width:900px;height:270px}'
                '.prof-grid line{stroke:#d8d2c4;stroke-width:1}'
                '.prof-grid line.base{stroke:#8a8172}'
                '.prof-area{fill:#c8d5c0}.prof-line{fill:none;stroke:#3f5c3a;stroke-width:2}'
                'text{font:11px Avenir Next;fill:#6b6355}'
                '.prof-wpt line{stroke:#8a8172;stroke-dasharray:2 2}'
                '.prof-wpt circle{fill:#b4472e}.prof-wpt text{fill:#2c2823;font-weight:600}'
                '.prof-marker circle{fill:#b4472e}.prof-marker text{fill:#fff;'
                'text-anchor:middle;font-size:10px;font-weight:700}</style>' + svg)
    print(f'wrote {out}')
