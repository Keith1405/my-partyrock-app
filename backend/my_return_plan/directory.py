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


def listed_in_area(location):
    """Find listed SS neighbourhood centres in PJ, without pretending to use GPS.
    Directory order is retained; these are area matches, not distance rankings.
    """
    text=str(location or "")
    if not re.search(r"\b(?:pj|petaling\s+jaya)\b",text,re.I): return []
    area=re.search(r"\bss\s*(\d{1,2})(?:/(\d{1,2}))?\b",text,re.I)
    if not area: return []
    token=area.group(1)
    street=area.group(2)
    # Refuse extra or contradictory location words instead of guessing.
    rest=re.sub(r"\bss\s*\d{1,2}(?:/\d{1,2})?\b|\b(?:pj|petaling\s+jaya|selangor|malaysia)\b|\b\d{5}\b", "", text, flags=re.I)
    if re.search(r"[A-Za-z0-9]",rest): return []
    codes=re.findall(r"\b\d{5}\b",text)
    if len(set(codes))>1: return []
    pattern=r"\bSS\s*"+re.escape(token)+(r"/"+re.escape(street) if street else "")+r"(?=$|[\s/,.-])"
    points=[p for p in DIRECTORY["locations"] if "petaling jaya" in p["description"].casefold() and re.search(pattern,p["description"],re.I)]
    if codes and any(codes[0] not in p["description"] for p in points): return []
    return points
