#!/usr/bin/env python3
"""Generate build/paths_uk.json — the UK map: 107 counties and council areas.

Sources (downloaded once into build/cache/, which is gitignored):

  England / Scotland / Wales   martinjc/UK-GeoJSON, ONS 2013 local authority
                               districts as TopoJSON. One shared topology, so
                               neighbours share arcs exactly.
  Northern Ireland             evansd/uk-ceremonial-counties, from which we take
                               only the six traditional Irish counties. NI is an
                               island, so mixing sources costs us no seams.

England's 47 ceremonial counties are not in any source as such: they are built
here by dissolving the 326 districts, in topology space, so the joins are exact.
Which district belongs to which county is decided by a point-in-polygon test
against the ceremonial county outlines, then checked against COUNTY_SIZES below.

Scotland keeps its 32 council areas and Wales its 22 principal areas — the layer
each nation actually uses — rather than lieutenancies nobody could name.
"""
import json, math, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')

RAW = 'https://raw.githubusercontent.com'
SOURCES = {
    'eng_lad': RAW + '/martinjc/UK-GeoJSON/master/json/administrative/eng/topo_lad.json',
    'sco_lad': RAW + '/martinjc/UK-GeoJSON/master/json/administrative/sco/topo_lad.json',
    'wal_lad': RAW + '/martinjc/UK-GeoJSON/master/json/administrative/wal/topo_lad.json',
    'uk_cer':  RAW + '/evansd/uk-ceremonial-counties/master/uk-ceremonial-counties.geojson',
}


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name + '.json')
    if not os.path.exists(p):
        print('downloading', name)
        urllib.request.urlretrieve(SOURCES[name], p)
    return json.load(open(p))


# ---------------------------------------------------------------- topojson ---
def decode_arcs(topo):
    """Arcs as absolute quantised integer points — exact, so they stitch by ==."""
    out = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x, y))
        out.append(pts)
    return out


def to_lonlat(topo, pt):
    (sx, sy), (tx, ty) = topo['transform']['scale'], topo['transform']['translate']
    return (pt[0] * sx + tx, pt[1] * sy + ty)


def rings_of(geom):
    """Every ring of a Polygon/MultiPolygon geometry, as lists of arc indices."""
    if geom['type'] == 'Polygon':
        return list(geom['arcs'])
    if geom['type'] == 'MultiPolygon':
        return [r for poly in geom['arcs'] for r in poly]
    raise ValueError(geom['type'])


def arc_points(arcs, a):
    return arcs[a] if a >= 0 else arcs[~a][::-1]


def merge_rings(arcs, geoms):
    """Dissolve a group of geometries: cancel the arcs they share, stitch the rest.

    Done on arc indices rather than coordinates, so an internal border vanishes
    completely instead of leaving a hairline where two traced outlines disagree.

    Every ring walks its boundary anticlockwise, so an arc between two members of
    the group is walked once each way and the pair cancels; what survives is the
    outside edge. Counting undirected uses instead would mishandle the one-unit
    stubs the source leaves at points where three districts meet — an arc there
    is used three times, which is neither "shared" nor "not shared".
    """
    fwd, bwd = {}, {}
    for g in geoms:
        for ring in rings_of(g):
            for a in ring:
                (fwd if a >= 0 else bwd)[a if a >= 0 else ~a] = \
                    (fwd if a >= 0 else bwd).get(a if a >= 0 else ~a, 0) + 1
    exterior = []
    for k in set(fwd) | set(bwd):
        f, b = fwd.get(k, 0), bwd.get(k, 0)
        exterior += [k] * (f - b) if f > b else [~k] * (b - f)

    by_start = {}
    for i, a in enumerate(exterior):
        by_start.setdefault(arc_points(arcs, a)[0], []).append(i)

    out, used = [], set()
    for seed in range(len(exterior)):
        if seed in used:
            continue
        ring = list(arc_points(arcs, exterior[seed]))
        used.add(seed)
        while ring[-1] != ring[0]:
            nxt = next((i for i in by_start.get(ring[-1], []) if i not in used), None)
            if nxt is None:
                raise AssertionError('unclosed ring while dissolving')
            used.add(nxt)
            ring.extend(arc_points(arcs, exterior[nxt])[1:])
        if len(ring) >= 4:
            out.append(ring)
    return out


# ------------------------------------------------------------------ geometry ---
def signed_area(r):
    s = 0.0
    for i in range(len(r) - 1):
        s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
    return s / 2


def ring_area(r):
    return abs(signed_area(r))


def contains(ring, pt):
    x, y = pt
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]; x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def rep_point(ring):
    """A point that is actually inside the ring, not just its centroid."""
    cx = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    cy = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    if contains(ring, (cx, cy)):
        return (cx, cy)
    ys = sorted(set(p[1] for p in ring))
    y = ys[len(ys) // 2]
    xs = []
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]; x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    xs.sort()
    if len(xs) >= 2:
        return ((xs[0] + xs[1]) / 2, y)
    return (cx, cy)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    stack = [(0, len(pts) - 1)]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        x1, y1 = pts[a]; x2, y2 = pts[b]
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            if d2 == 0:
                dist = math.hypot(x0 - x1, y0 - y1)
            else:
                dist = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / math.sqrt(d2)
            if dist > best:
                best, bi = dist, i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi)); stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


# --------------------------------------------------------- ceremonial counties ---
# The 47 we map. England's 48th, the City of London, is a square mile inside
# Greater London — too small to click and too odd to ask for, so it is folded in.
# Values are the county's area in km2, from the source data, and exist to catch a
# district that landed in the wrong county: a bad assignment moves these numbers.
COUNTY_SIZES = {
    'Bedfordshire': 1235, 'Berkshire': 1262, 'Bristol': 110, 'Buckinghamshire': 1874,
    'Cambridgeshire': 3400, 'Cheshire': 2344, 'Cornwall': 3567, 'Cumbria': 6820,
    'Derbyshire': 2628, 'Devon': 6710, 'Dorset': 2656, 'Durham': 2682,
    'East Riding of Yorkshire': 2478, 'East Sussex': 1798, 'Essex': 3672,
    'Gloucestershire': 3150, 'Greater London': 1579, 'Greater Manchester': 1276,
    'Hampshire': 3771, 'Herefordshire': 2180, 'Hertfordshire': 1641,
    'Isle of Wight': 380, 'Kent': 3742, 'Lancashire': 3072, 'Leicestershire': 2157,
    'Lincolnshire': 6976, 'Merseyside': 644, 'Norfolk': 5382, 'North Yorkshire': 8659,
    'Northamptonshire': 2368, 'Northumberland': 5027, 'Nottinghamshire': 2161,
    'Oxfordshire': 2606, 'Rutland': 394, 'Shropshire': 3486, 'Somerset': 4179,
    'South Yorkshire': 1552, 'Staffordshire': 2719, 'Suffolk': 3801, 'Surrey': 1670,
    'Tyne and Wear': 543, 'Warwickshire': 1977, 'West Midlands': 901,
    'West Sussex': 1992, 'West Yorkshire': 2031, 'Wiltshire': 3486,
    'Worcestershire': 1742,
}
NI_COUNTIES = ['Antrim', 'Armagh', 'Down', 'Fermanagh', 'Londonderry', 'Tyrone']

# id blocks, so a unit's nation is readable from its number alone
BLOCK = {'eng': 100, 'sco': 200, 'wal': 300, 'ni': 400}


def english_counties():
    """district name -> ceremonial county, by locating each district on the
    ceremonial outlines. Reported in full so the assignment can be read back."""
    cer = fetch('uk_cer')
    outlines = {}
    for f in cer['features']:
        name = f['properties'].get('county')
        if name not in COUNTY_SIZES:
            continue
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        outlines[name] = [[(float(x), float(y)) for x, y in poly[0]] for poly in polys]
    missing = set(COUNTY_SIZES) - set(outlines)
    assert not missing, 'no ceremonial outline for %s' % sorted(missing)

    topo = fetch('eng_lad')
    arcs = decode_arcs(topo)
    lookup = {}
    for g in topo['objects']['lad']['geometries']:
        nm = g['properties']['LAD13NM']
        # the district's largest ring decides — a detached island must not vote
        best = max((([to_lonlat(topo, p) for p in
                      sum((arc_points(arcs, a) for a in ring), [])])
                    for ring in rings_of(g)), key=ring_area)
        pt = rep_point(best + [best[0]])
        hit = [c for c, polys in outlines.items() if any(contains(r, pt) for r in polys)]
        if len(hit) != 1:
            # on a boundary, or in the sea after generalisation: take the nearest
            hit = [min(outlines, key=lambda c: min(
                min(math.hypot(pt[0] - q[0], pt[1] - q[1]) for q in r)
                for r in outlines[c]))]
        lookup[nm] = hit[0]
    return topo, arcs, lookup


def main():
    units = {}          # id -> {'name':..., 'nation':..., 'rings':[[(lon,lat)...]]}

    # --- England: dissolve districts into ceremonial counties ------------------
    topo, arcs, lookup = english_counties()
    groups = {}
    for g in topo['objects']['lad']['geometries']:
        groups.setdefault(lookup[g['properties']['LAD13NM']], []).append(g)
    assert set(groups) == set(COUNTY_SIZES), \
        'county set mismatch: %s' % sorted(set(groups) ^ set(COUNTY_SIZES))
    for i, name in enumerate(sorted(groups)):
        rings = [[to_lonlat(topo, p) for p in r] for r in merge_rings(arcs, groups[name])]
        units[BLOCK['eng'] + i] = {'name': name, 'nation': 'eng', 'rings': rings,
                                   'lads': sorted(g['properties']['LAD13NM']
                                                  for g in groups[name])}

    # --- Scotland and Wales: districts are already the unit --------------------
    for nation, key in (('sco', 'sco_lad'), ('wal', 'wal_lad')):
        t = fetch(key)
        a = decode_arcs(t)
        gs = sorted(t['objects']['lad']['geometries'],
                    key=lambda g: g['properties']['LAD13NM'])
        for i, g in enumerate(gs):
            rings = [[to_lonlat(t, p) for p in
                      sum((arc_points(a, x) for x in ring), [])]
                     for ring in rings_of(g)]
            units[BLOCK[nation] + i] = {'name': g['properties']['LAD13NM'],
                                        'nation': nation, 'rings': rings}

    # --- Northern Ireland: the six traditional counties ------------------------
    cer = fetch('uk_cer')
    for i, name in enumerate(NI_COUNTIES):
        f = next(f for f in cer['features'] if f['properties'].get('county') == name)
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        units[BLOCK['ni'] + i] = {
            'name': name, 'nation': 'ni',
            'rings': [[(float(x), float(y)) for x, y in poly[0]] for poly in polys]}

    # --- trim to landmasses worth drawing -------------------------------------
    # Rockall, St Kilda and the Scillies are real but would only add specks.
    FLOOR = 0.0022          # sq degrees, about 15 km2 at this latitude
    for u in units.values():
        rs = [r for r in u['rings']
              if -8.8 <= sum(p[0] for p in r) / len(r) <= 2.2
              and 49.7 <= sum(p[1] for p in r) / len(r) <= 61.2]
        rs = rs or u['rings']
        rs.sort(key=ring_area, reverse=True)
        u['rings'] = [rs[0]] + [r for r in rs[1:] if ring_area(r) > FLOOR]

    # --- drop holes: a ring wholly inside a bigger ring of the same unit --------
    for u in units.values():
        keep = []
        for i, r in enumerate(u['rings']):
            pt = r[0]
            if any(ring_area(o) > ring_area(r) and contains(o, pt)
                   for j, o in enumerate(u['rings']) if j != i):
                continue
            keep.append(r)
        u['rings'] = keep

    # --- simplify --------------------------------------------------------------
    EPS = 0.0032
    for u in units.values():
        out = []
        for r in u['rings']:
            s = rdp(r, EPS)
            if len(s) >= 4:
                out.append(s)
        u['rings'] = out or [rdp(max(u['rings'], key=ring_area), EPS / 3)]

    # --- project: equirectangular, scaled by cos(mid latitude) -----------------
    K = math.cos(math.radians(54.5))
    def proj(lon, lat):
        return (lon * K, -lat)

    # Shetland sits 80 km beyond the top of the map and would stretch the whole
    # country to fit it. Every UK map ever printed boxes it off; so does this one.
    SHETLAND = next(i for i, u in units.items() if u['name'] == 'Shetland Islands')
    SHS = 1.0               # already legible at true scale; the box is about place

    mainland = [proj(lon, lat) for i, u in units.items() if i != SHETLAND
                for r in u['rings'] for lon, lat in r]
    mnx = min(p[0] for p in mainland); mxx = max(p[0] for p in mainland)
    mny = min(p[1] for p in mainland); mxy = max(p[1] for p in mainland)

    sh = [proj(lon, lat) for r in units[SHETLAND]['rings'] for lon, lat in r]
    shx0 = min(p[0] for p in sh); shx1 = max(p[0] for p in sh)
    shy0 = min(p[1] for p in sh); shy1 = max(p[1] for p in sh)
    # the islands are long and thin; the box is padded so the word "Shetland"
    # fits along its foot without spilling out over the sea
    padx = 0.30 * (shx1 - shx0) * SHS
    padb = 0.16 * (shy1 - shy0) * SHS
    box_w = (shx1 - shx0) * SHS + 2 * padx
    box_h = (shy1 - shy0) * SHS + padb
    # the North Sea, off the top-right — where an atlas puts it
    bx = mxx - box_w - 0.08
    by = mny + 0.10
    def shmap(x, y):
        return (bx + padx + (x - shx0) * SHS, by + (y - shy0) * SHS)

    paths = {}
    for i, u in units.items():
        segs = []
        for r in u['rings']:
            pts = [proj(lon, lat) for lon, lat in r]
            if i == SHETLAND:
                pts = [shmap(x, y) for x, y in pts]
            segs.append(pts)
        paths[i] = segs

    # --- fit into a viewBox ----------------------------------------------------
    allp = [p for segs in paths.values() for s in segs for p in s]
    x0 = min(p[0] for p in allp); x1 = max(p[0] for p in allp)
    y0 = min(p[1] for p in allp); y1 = max(p[1] for p in allp)
    W = 1000.0
    S = W / (x1 - x0)
    H = (y1 - y0) * S
    PAD = 18.0
    W += 2 * PAD; H += 2 * PAD
    x0 -= PAD / S; y0 -= PAD / S

    def fmt(v):
        s = f'{v:.1f}'
        return s[:-2] if s.endswith('.0') else s

    out = {}
    for i, segs in paths.items():
        ds, screen = [], []
        for s in segs:
            c = [((p[0] - x0) * S, (p[1] - y0) * S) for p in s]
            screen.append(c)
            ds.append('M' + ' '.join(f'{fmt(a)},{fmt(b)}' for a, b in c) + 'Z')
        big = max(screen, key=ring_area)
        A = cx = cy = 0.0
        for j in range(len(big) - 1):
            xa, ya = big[j]; xb, yb = big[j + 1]
            cr = xa * yb - xb * ya
            A += cr; cx += (xa + xb) * cr; cy += (ya + yb) * cr
        if abs(A) < 1e-9:
            cx = sum(q[0] for q in big) / len(big); cy = sum(q[1] for q in big) / len(big)
        else:
            A *= 0.5; cx /= (6 * A); cy /= (6 * A)
        if not contains(big, (cx, cy)):
            cx, cy = rep_point(big)
        bx0 = min(q[0] for q in big); bx1 = max(q[0] for q in big)
        by0 = min(q[1] for q in big); by1 = max(q[1] for q in big)
        out[i] = {'name': units[i]['name'], 'nation': units[i]['nation'],
                  'd': ''.join(ds), 'c': [round(cx, 1), round(cy, 1)],
                  'b': [round(bx0, 1), round(by0, 1), round(bx1, 1), round(by1, 1)]}

    inset = {'x': (bx - x0) * S, 'y': (by - y0) * S, 'w': box_w * S, 'h': box_h * S}
    res = {'w': round(W, 1), 'h': round(H, 1),
           'inset': {k: round(v, 1) for k, v in inset.items()},
           'insetId': SHETLAND, 'insetLabel': 'Shetland',
           'units': {str(k): v for k, v in sorted(out.items())}}
    dest = os.path.join(HERE, 'paths_uk.json')
    open(dest, 'w').write(json.dumps(res, ensure_ascii=False, separators=(',', ':')))

    # --- report ----------------------------------------------------------------
    print('viewBox %s x %s   inset %s' % (res['w'], res['h'], res['inset']))
    print('units %d   path bytes %d' % (len(out), sum(len(v['d']) for v in out.values())))
    for n, label in (('eng', 'England'), ('sco', 'Scotland'),
                     ('wal', 'Wales'), ('ni', 'Northern Ireland')):
        print('  %-17s %d' % (label, sum(1 for v in out.values() if v['nation'] == n)))
    print('\ndistricts per English county (area km2 from source in brackets):')
    for i in sorted(units):
        u = units[i]
        if u['nation'] == 'eng':
            print('  %-26s [%5d] %s' % (u['name'], COUNTY_SIZES[u['name']],
                                        ', '.join(u['lads'])))


if __name__ == '__main__':
    main()
