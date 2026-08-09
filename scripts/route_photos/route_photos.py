#!/usr/bin/env python3
"""Find the Strava community photos that sit on a route, for any GPX.

    python3 route_photos.py <route.gpx>

Harvests Strava's public photo tiles along the route, keeps the ones that are
actually on the path, thins them to one per stretch, and writes a contact sheet
you can open in a browser. Everything lands in route-photos/<gpx name>/.

    python3 route_photos.py mijn-route.gpx --no-images    # manifest only, ~0 MB
    python3 route_photos.py mijn-route.gpx --bucket 500 --max-offset 50
    python3 route_photos.py mijn-route.gpx --out /tmp/recon --title "Verkenning"

The photos belong to other Strava users. Keep the output local — don't commit
the images and don't republish them.
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

import build_overview
import harvest
import select_download

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}


def route_title(gpx_path):
    """The <metadata><name> Strava/Garmin write, falling back to the filename."""
    try:
        name = ET.parse(gpx_path).getroot().find('.//gpx:metadata/gpx:name', NS)
        if name is not None and name.text and name.text.strip():
            return name.text.strip()
    except ET.ParseError:
        pass
    return os.path.splitext(os.path.basename(gpx_path))[0]


def main():
    ap = argparse.ArgumentParser(
        description='Collect the Strava community photos along a GPX route.')
    ap.add_argument('gpx', help='route GPX file')
    ap.add_argument('--out', help='output directory '
                                  '(default: route-photos/<gpx name>)')
    ap.add_argument('--title', help='heading for the contact sheet '
                                    '(default: the route name in the GPX)')
    ap.add_argument('--bucket', type=int, default=250, metavar='M',
                    help='keep the best photo per M metres of route (default 250)')
    ap.add_argument('--max-offset', type=int, default=25, metavar='M',
                    help='how far off the route a photo may sit (default 25)')
    ap.add_argument('--zoom', type=int, default=16,
                    help='tile zoom; 16 gives individual photos (default 16)')
    ap.add_argument('--no-images', action='store_true',
                    help='write only the manifest, do not download the photos')
    args = ap.parse_args()

    if not os.path.exists(args.gpx):
        sys.exit(f'no such file: {args.gpx}')

    stem = os.path.splitext(os.path.basename(args.gpx))[0]
    outdir = args.out or os.path.join(REPO, 'route-photos', stem)
    title = args.title or route_title(args.gpx)

    photos = harvest.run(args.gpx, z=args.zoom)
    if not photos:
        sys.exit('no photos found along this route')

    select_download.run(photos, outdir, args.bucket, args.max_offset,
                        fetch_images=not args.no_images)
    sheet = build_overview.run(args.gpx, outdir, title)
    print(f'\nopen {sheet}')


if __name__ == '__main__':
    main()
