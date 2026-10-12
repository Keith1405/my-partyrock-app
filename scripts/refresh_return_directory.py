"""Refresh bundled public data. Run manually, inspect the diff, then deploy."""
import io, json, re, urllib.request, zipfile
from datetime import date
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/"backend/my_return_plan"
def read(url):
    req=urllib.request.Request(url,headers={"User-Agent":"SmartMedCycle/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        data=response.read(5_000_001)
        if len(data)>5_000_000: raise ValueError("Source unexpectedly large")
        return data
source="https://www.mymedisafe.org.my/index.html"
text=read(source).decode("utf-8")
match=re.search(r"const\s+jsonData\s*=\s*\{\s*locations:\s*",text)
if not match: raise ValueError("Locator source format changed; existing data kept")
rows,_=json.JSONDecoder(strict=False).raw_decode(text[match.end():].lstrip())
points=[];seen=set()
for row in rows:
    try: lat=float(row["latitude"]);lon=float(row["longitude"])
    except (ValueError,TypeError,KeyError): continue
    if not (0.5<=lat<=7.5 and 99<=lon<=120) or not row.get("name"): continue
    key=(row["name"].casefold(),lat,lon)
    if key in seen: continue
    seen.add(key)
    points.append({k:str(row.get(k) or "").strip() for k in ("name","description","phone")} | {"latitude":lat,"longitude":lon})
if len(points)<500: raise ValueError("Unexpected directory size; existing data kept")
postal_source="https://download.geonames.org/export/zip/MY.zip"
with zipfile.ZipFile(io.BytesIO(read(postal_source))) as z: text=z.read("MY.txt").decode("utf-8")
places=[]
for line in text.splitlines():
    f=line.split("\t")
    if len(f)<11: continue
    try: lat=float(f[9]);lon=float(f[10])
    except ValueError: continue
    if not (0.5<=lat<=7.5 and 99<=lon<=120): continue
    places.append({"postcode":f[1],"place":f[2],"state":f[3],"latitude":lat,"longitude":lon})
if len(places)<1000: raise ValueError("Unexpected postal data size; existing data kept")
for filename,data in [("collection_points.json", {"source_url":source,"checked_on":date.today().isoformat(),"locations":points}), ("postal_coordinates.json", {"source_url":postal_source,"checked_on":date.today().isoformat(),"license":"GeoNames CC BY 4.0 — https://www.geonames.org/", "places":places})]:
    target=BASE/filename; temporary=target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");temporary.replace(target)
print(f"Refreshed {len(points)} points and {len(places)} postal rows. Review and deploy the changes.")
