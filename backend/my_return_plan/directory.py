"""Offline directory ranking. Postcode/town coordinates are approximate, not GPS."""
import json, math, re
from pathlib import Path
BASE=Path(__file__).parent
with (BASE/"collection_points.json").open(encoding="utf-8") as f: DIRECTORY=json.load(f)
with (BASE/"postal_coordinates.json").open(encoding="utf-8") as f: POSTAL=json.load(f)

def _normal(text): return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
def locate(text):
    text=str(text or ""); norm=_normal(text)
    codes=re.findall(r"\b\d{5}\b",text)
    if len(set(codes))>1: return None
    rows=POSTAL["places"]
    if codes:
        rows=[r for r in rows if r["postcode"]==codes[0]]
        # A wrong postcode must not silently fall back to a different town.
        if not rows: return None
        rest=_normal(re.sub(r"\b\d{5}\b","",text))
        if rest and not any(rest in _normal(r["place"]+" "+r["state"]) for r in rows): return None
    else:
        rows=[r for r in rows if norm==_normal(r["place"]) or norm==_normal(r["place"]+" "+r["state"])] if norm else []
        if len({r["state"] for r in rows})>1: return None
    if not rows: return None
    # Never average locations far apart simply because they share a name/code.
    if max(r["latitude"] for r in rows)-min(r["latitude"] for r in rows)>0.3 or max(r["longitude"] for r in rows)-min(r["longitude"] for r in rows)>0.3: return None
    return {"label": (codes[0]+" " if codes else "")+rows[0]["place"]+", "+rows[0]["state"], "latitude":sum(r["latitude"] for r in rows)/len(rows), "longitude":sum(r["longitude"] for r in rows)/len(rows)}

def distance(a,b):
    lat1,lat2=map(math.radians,[a["latitude"],b["latitude"]])
    dlat=lat2-lat1; dlon=math.radians(b["longitude"]-a["longitude"])
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))

def nearest(location, limit=3):
    origin=locate(location)
    if not origin: return None, []
    points=sorted((dict(p, distance_km=distance(origin,p)) for p in DIRECTORY["locations"]),key=lambda p:p["distance_km"])
    return origin, points[:limit]
