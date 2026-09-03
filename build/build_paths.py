import json, math

SRC='/private/tmp/claude-501/-Users-joe-repos-japan-map-game/9eaf78b2-039b-4879-99c3-c1cadbfd559e/scratchpad/japan.geojson'
d=json.load(open(SRC))

def rdp(pts, eps):
    if len(pts) < 3: return pts
    stack=[(0,len(pts)-1)]; keep=[False]*len(pts); keep[0]=keep[-1]=True
    while stack:
        a,b=stack.pop()
        if b<=a+1: continue
        x1,y1=pts[a]; x2,y2=pts[b]
        dx,dy=x2-x1,y2-y1; d2=dx*dx+dy*dy
        best=-1.0; bi=-1
        for i in range(a+1,b):
            x0,y0=pts[i]
            if d2==0: dist=math.hypot(x0-x1,y0-y1)
            else: dist=abs(dy*x0-dx*y0+x2*y1-y2*x1)/math.sqrt(d2)
            if dist>best: best=dist; bi=i
        if best>eps:
            keep[bi]=True; stack.append((a,bi)); stack.append((bi,b))
    return [p for p,k in zip(pts,keep) if k]

def ring_area(r):
    s=0.0
    for i in range(len(r)-1):
        s += r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1]
    return abs(s)/2

# --- gather polygons per prefecture (outer rings only; holes are negligible here) ---
prefs={}
for f in d['features']:
    p=f['properties']; pid=p['id']; g=f['geometry']
    polys = g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    rings=[]
    for poly in polys:
        outer=[(float(x),float(y)) for x,y in poly[0]]
        rings.append(outer)
    prefs[pid]={'ja':p['nam_ja'],'en':p['nam'],'rings':rings}

# --- drop far-flung territories that would wreck the frame ---
def keep_ring(pid, r):
    lons=[c[0] for c in r]; lats=[c[1] for c in r]
    clon=sum(lons)/len(lons); clat=sum(lats)/len(lats)
    if pid==13 and (clat<32 or clon>141.5): return False      # Izu/Ogasawara islands
    if pid==47 and not (126.0<clon<128.6): return False       # inset shows the Okinawa-honto group
    if pid==46 and clat<26.5: return False                    # far Satsunan outliers
    if clon>146.5 or clon<122: return False
    return True

for pid,v in prefs.items():
    v['rings']=[r for r in v['rings'] if keep_ring(pid,r)]

# --- keep only meaningful landmasses: biggest ring + rings above a size floor ---
FLOOR = 0.0025   # sq degrees ~ 25 km^2
for pid,v in prefs.items():
    rs=sorted(v['rings'], key=ring_area, reverse=True)
    kept=[rs[0]]+[r for r in rs[1:] if ring_area(r)>FLOOR]
    v['rings']=kept

# --- simplify ---
EPS=0.004
for v in prefs.values():
    out=[]
    for r in v['rings']:
        s=rdp(r,EPS)
        if len(s)>=4: out.append(s)
    v['rings']=out

# --- project: equirectangular scaled by cos(mid lat) ---
K=math.cos(math.radians(37.0))
def proj(lon,lat): return (lon*K, -lat)

# Okinawa (47) -> inset, translated in projected space into the empty NW corner
mainland=[]
for pid,v in prefs.items():
    for r in v['rings']:
        for lon,lat in r:
            if pid!=47: mainland.append(proj(lon,lat))
mnx=min(p[0] for p in mainland); mxx=max(p[0] for p in mainland)
mny=min(p[1] for p in mainland); mxy=max(p[1] for p in mainland)

ok=[proj(lon,lat) for r in prefs[47]['rings'] for lon,lat in r]
okx0=min(p[0] for p in ok); okx1=max(p[0] for p in ok)
oky0=min(p[1] for p in ok); oky1=max(p[1] for p in ok)
OKS=3.5   # scale up the Okinawa inset so the islands are visible/clickable
# place inset box top-left of the mainland frame
pad=0.25
box_w=(okx1-okx0)*OKS; box_h=(oky1-oky0)*OKS
bx=mnx+pad; by=mny+pad
def okmap(x,y): return (bx+(x-okx0)*OKS, by+(y-oky0)*OKS)

paths={}
for pid,v in prefs.items():
    segs=[]
    for r in v['rings']:
        pts=[proj(lon,lat) for lon,lat in r]
        if pid==47: pts=[okmap(x,y) for x,y in pts]
        segs.append(pts)
    paths[pid]=segs

# --- fit everything into a viewBox ---
allp=[p for segs in paths.values() for s in segs for p in s]
x0=min(p[0] for p in allp); x1=max(p[0] for p in allp)
y0=min(p[1] for p in allp); y1=max(p[1] for p in allp)
W=1000.0
S=W/(x1-x0)
H=(y1-y0)*S
PAD=18.0
W+=2*PAD; H+=2*PAD
x0-=PAD/S; y0-=PAD/S

def fmt(v):
    s=f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s

out={}
for pid,segs in paths.items():
    ds=[]; screen=[]
    for s in segs:
        c=[( (p[0]-x0)*S, (p[1]-y0)*S ) for p in s]
        screen.append(c)
        ds.append('M'+' '.join(f'{fmt(a)},{fmt(b)}' for a,b in c)+'Z')
    big=max(screen,key=ring_area)
    # area-weighted centroid of the largest ring
    A=0.0; cx=0.0; cy=0.0
    for i in range(len(big)-1):
        xa,ya=big[i]; xb,yb=big[i+1]
        cr=xa*yb-xb*ya; A+=cr; cx+=(xa+xb)*cr; cy+=(ya+yb)*cr
    if abs(A)<1e-9:
        cx=sum(q[0] for q in big)/len(big); cy=sum(q[1] for q in big)/len(big)
    else:
        A*=0.5; cx/=(6*A); cy/=(6*A)
    bx0=min(q[0] for q in big); bx1=max(q[0] for q in big)
    by0=min(q[1] for q in big); by1=max(q[1] for q in big)
    out[pid]={'ja':prefs[pid]['ja'],'en':prefs[pid]['en'],'d':''.join(ds),
              'c':[round(cx,1),round(cy,1)],'b':[round(bx0,1),round(by0,1),round(bx1,1),round(by1,1)]}

inset={'x':(bx-x0)*S,'y':(by-y0)*S,'w':box_w*S,'h':box_h*S}
res={'w':round(W,1),'h':round(H,1),'inset':{k:round(val,1) for k,val in inset.items()},'prefs':out}
open('/private/tmp/claude-501/-Users-joe-repos-japan-map-game/9eaf78b2-039b-4879-99c3-c1cadbfd559e/scratchpad/paths.json','w').write(json.dumps(res,ensure_ascii=False,separators=(',',':')))
print('viewBox', W, round(H,1), 'inset', res['inset'])
print('bytes', sum(len(v['d']) for v in out.values()))
print('rings per pref sample', {out[i]['ja']: len(paths[i]) for i in (1,13,47,42,46,12)})
