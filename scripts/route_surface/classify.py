#!/usr/bin/env python3
"""Turn OSM tags into "verhard" or "onverhard".

Every judgement in this file is a judgement, not a fact, which is why the
harvest keeps the raw tags: re-running `--reclassify` re-buckets what is already
on disk without touching Overpass.

Two levels of confidence, and the output reports them separately:

  tagged    the way carries surface=*, so this is what a surveyor wrote down
  inferred  it does not, so we go on `highway=*` — a footpath in Kent is a
            footpath, but the guess can be wrong either way

`compacted` and `fine_gravel` are the contentious ones. Both are counted
*unverhard*: they are what the North Downs Way chalk tracks are tagged as, and
underfoot they are nothing like tarmac even though a road bike would manage.

The trap is `highway=footway` with no `surface`. In the countryside that is a
field path; in a village it is the pavement beside a street, and calling 1.6 km
of Halling pavement "onverhard" was the one plainly wrong answer the first run
gave. Three signals separate them, in order of how much they can be trusted:

  footway=sidewalk / crossing   OSM says so outright
  designation=public_footpath   a right of way across land, so not a pavement
  _sidewalk_of                  set by match(): this footway carries the name of
                                a road in the same harvest, which is how OSM
                                draws a pavement ("Meadow Crescent" twice, once
                                as residential and once as footway)
"""

# surface=* values, from taginfo's UK distribution
PAVED_SURFACES = {
    'asphalt', 'paved', 'concrete', 'concrete:plates', 'concrete:lanes',
    'paving_stones', 'sett', 'cobblestone', 'unhewn_cobblestone', 'bricks',
    'brick', 'chipseal', 'metal', 'wood', 'tartan', 'acrylic',
    'paving_stones:30', 'asphalt;paving_stones',
}
UNPAVED_SURFACES = {
    'unpaved', 'gravel', 'fine_gravel', 'compacted', 'dirt', 'earth', 'ground',
    'grass', 'grass_paver', 'mud', 'sand', 'pebblestone', 'rock', 'stone',
    'woodchips', 'clay', 'shells', 'salt', 'snow', 'gravel;grass',
}

# highway=* fallbacks, used only when surface is absent
PAVED_HIGHWAYS = {
    'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary',
    'primary_link', 'secondary', 'secondary_link', 'tertiary',
    'tertiary_link', 'residential', 'living_street', 'unclassified',
    'service', 'pedestrian', 'cycleway',
}
UNPAVED_HIGHWAYS = {
    'track', 'path', 'footway', 'bridleway', 'steps', 'via_ferrata',
}

PAVED, UNPAVED, UNKNOWN = 'verhard', 'onverhard', 'onbekend'


# footway=* values that mean "part of a street", so surfaced whatever else
STREET_FOOTWAYS = {'sidewalk', 'crossing', 'traffic_island'}

# designation=* values that mean a right of way over land, so not a pavement
RIGHTS_OF_WAY = {'public_footpath', 'public_bridleway', 'restricted_byway',
                 'byway_open_to_all_traffic', 'permissive_path',
                 'public_right_of_way'}


def classify(tags):
    """-> (verdict, basis, evidence). basis is 'tagged' | 'inferred' | 'none'."""
    if not tags:
        return UNKNOWN, 'none', ''

    surface = (tags.get('surface') or '').strip().lower()
    if surface in PAVED_SURFACES:
        return PAVED, 'tagged', f'surface={surface}'
    if surface in UNPAVED_SURFACES:
        return UNPAVED, 'tagged', f'surface={surface}'

    # tracktype is a smoothness grade for tracks; grade1 is the metalled one
    highway = (tags.get('highway') or '').strip().lower()
    tracktype = (tags.get('tracktype') or '').strip().lower()
    if highway == 'track' and tracktype:
        verdict = PAVED if tracktype == 'grade1' else UNPAVED
        return verdict, 'tagged', f'tracktype={tracktype}'

    # a pavement or a crossing is part of the road, however it is drawn
    footway = (tags.get('footway') or '').strip().lower()
    if footway in STREET_FOOTWAYS:
        return PAVED, 'tagged', f'footway={footway}'

    designation = (tags.get('designation') or '').strip().lower()
    if designation in RIGHTS_OF_WAY:
        return UNPAVED, 'inferred', f'designation={designation}'

    if tags.get('_sidewalk_of'):
        return PAVED, 'inferred', 'footway named after a road (pavement)'

    if highway in PAVED_HIGHWAYS:
        return PAVED, 'inferred', f'highway={highway}'
    if highway in UNPAVED_HIGHWAYS:
        return UNPAVED, 'inferred', f'highway={highway}'

    if surface:
        return UNKNOWN, 'none', f'surface={surface}'
    return UNKNOWN, 'none', f'highway={highway}' if highway else ''
