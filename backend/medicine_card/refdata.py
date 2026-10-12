"""
SmartMed Cycle — reference-data retrieval helpers (free NLM services).

RxNorm/RxNav (exact + approximate match, ingredient resolution) and
MedlinePlus Connect (patient drug page). All free, no auth, no licence.
Never invents data: returns a real result or signals verification failed.
"""
import json
import time
import urllib.parse
import urllib.request

_TIMEOUT = 4
_UA = "SmartMedCycle/1.0 (patient medicine-prep tool)"

_CACHE = {}
_CACHE_TTL = 12 * 60 * 60

def _cache_get(key):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None

def _cache_put(key, value):
    _CACHE[key] = (time.time() + _CACHE_TTL, value)

def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))

def _rxcui_exact(name):
    url = (
        "https://rxnav.nlm.nih.gov/REST/rxcui.json?name="
        + urllib.parse.quote(name)
        + "&search=2"
    )
    try:
        data = _get_json(url)
        ids = (data.get("idGroup") or {}).get("rxnormId") or []
        return ids[0] if ids else None
    except Exception:
        return None

def _rxcui_approx(name):
    url = (
        "https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term="
        + urllib.parse.quote(name)
        + "&maxEntries=5"
    )
    try:
        data = _get_json(url)
        cands = ((data.get("approximateGroup") or {}).get("candidate")) or []
        out = []
        seen = set()
        for c in cands:
            rxcui = c.get("rxcui")
            if not rxcui or rxcui in seen:
                continue
            seen.add(rxcui)
            out.append(
                {"rxcui": rxcui, "name": c.get("name", ""), "score": int(c.get("score", 0))}
            )
        return out
    except Exception:
        return []

def _ingredients(rxcui):
    url = (
        "https://rxnav.nlm.nih.gov/REST/rxcui/"
        + urllib.parse.quote(str(rxcui))
        + "/related.json?tty=IN+PIN"
    )
    try:
        data = _get_json(url)
        groups = ((data.get("relatedGroup") or {}).get("conceptGroup")) or []
        names = []
        for g in groups:
            for concept in g.get("conceptProperties") or []:
                nm = concept.get("name")
                if nm and nm not in names:
                    names.append(nm)
        return names
    except Exception:
        return []

def _rxcui_name(rxcui):
    url = "https://rxnav.nlm.nih.gov/REST/rxcui/" + urllib.parse.quote(str(rxcui)) + "/property.json?propName=RxNorm%20Name"
    try:
        data = _get_json(url)
        props = ((data.get("propConceptGroup") or {}).get("propConcept")) or []
        return props[0].get("propValue") if props else None
    except Exception:
        return None

def _medlineplus_by_rxcui(rxcui, language="English"):
    lang = "en"
    url = (
        "https://connect.medlineplus.gov/service"
        "?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88"
        "&mainSearchCriteria.v.c=" + urllib.parse.quote(str(rxcui))
        + "&knowledgeResponseType=application/json"
        + "&informationRecipient.languageCode.c=" + lang
    )
    try:
        data = _get_json(url)
        entries = ((data.get("feed") or {}).get("entry")) or []
        for e in entries:
            title = (e.get("title") or {}).get("_value") or e.get("title")
            links = e.get("link") or []
            href = None
            for l in links:
                if l.get("href"):
                    href = l["href"]
                    break
            if title and href:
                return {"title": title if isinstance(title, str) else str(title), "url": href}
        return None
    except Exception:
        return None

def _verify_nlm(name, language="English"):
    name = (name or "").strip()
    result = {
        "query": name,
        "status": "unverified",
        "rxcui": None,
        "matched_name": None,
        "ingredients": [],
        "candidates": [],
        "sources": [],
        "note": "",
    }
    if not name:
        result["note"] = "empty name"
        return result

    cache_key = "verify:" + name.lower()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    rxcui = _rxcui_exact(name)
    if rxcui:
        ingredients = _ingredients(rxcui)
        matched = _rxcui_name(rxcui) or name
        result.update(
            status="verified",
            rxcui=rxcui,
            matched_name=matched,
            ingredients=ingredients,
            note="exact RxNorm match",
        )
        result["sources"].append(
            {"title": "RxNorm (US NLM) — " + matched, "url": "https://rxnav.nlm.nih.gov/REST/rxcui/%s" % rxcui}
        )
        mp = _medlineplus_by_rxcui(rxcui, language)
        if mp:
            result["sources"].append({"title": "MedlinePlus — " + mp["title"], "url": mp["url"]})
        _cache_put(cache_key, result)
        return result

    cands = _rxcui_approx(name)
    if cands:
        result.update(
            status="ambiguous",
            candidates=[{"name": c["name"], "score": c["score"]} for c in cands[:5]],
            note="approximate matches only — not auto-identified",
        )
        _cache_put(cache_key, result)
        return result

    result["note"] = "no RxNorm match (may be a Malaysia-only brand, misspelling, or offline)"
    _cache_put(cache_key, result)
    return result

def reference_block(verifications):
    lines = ["RETRIEVED REFERENCE DATA (identity records; results may be cached):"]
    if not verifications:
        lines.append("- (no medicine names were extracted to verify)")
        return "\n".join(lines)
    for v in verifications:
        lines.append("")
        lines.append(f"- Query: \"{v['query']}\"")
        lines.append(f"  status: {v['status']}  ({v['note']})")
        if v["matched_name"]:
            lines.append(f"  matched_name: {v['matched_name']}")
        if v["ingredients"]:
            lines.append(f"  active_ingredients: {', '.join(v['ingredients'])}")
        if v["candidates"]:
            cand = "; ".join(f"{c['name']} ({c.get('registration', c.get('score', 'candidate'))})" for c in v["candidates"])
            lines.append(f"  approximate_candidates: {cand}")
        if v["sources"]:
            for s in v["sources"]:
                lines.append(f"  source: {s['title']} — {s['url']}")
    return "\n".join(lines)

from html.parser import HTMLParser
import re
from datetime import datetime, timezone

_QUEST = "https://quest3plus.bpfk.gov.my/pmo2/"
class _Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row=[]
        if tag in ("td", "th") and self.row is not None: self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split())); self.cell=None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row=None

def _quest_read(path, fields=None):
    url=urllib.parse.urljoin(_QUEST, path)
    if not url.startswith(_QUEST): raise ValueError("unexpected NPRA URL")
    data=urllib.parse.urlencode(fields).encode() if fields else None
    req=urllib.request.Request(url, data=data, headers={"User-Agent":"Mozilla/5.0 SmartMedCycle/1.0", "Referer":_QUEST+"index.php"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
        if not response.geturl().startswith(_QUEST): raise ValueError("unexpected redirect")
        text=response.read(2_000_001)
        if len(text)>2_000_000: raise ValueError("response too large")
        return text.decode("utf-8", "replace")

def _npra(name):
    result={"query":name,"status":"unverified","rxcui":None,"matched_name":None,"ingredients":[],"candidates":[],"sources":[],"note":""}
    registration=bool(re.fullmatch(r"MAL[0-9A-Za-z]+",name,re.I))
    try:
        html=_quest_read("content.php", {"func":"search","searchBy":"2" if registration else "1","searchTxt":name,"cat":"1"})
        if "searchTable" not in html: raise ValueError("NPRA search format unavailable")
        parser=_Rows(); parser.feed(html)
        records=[]
        for row in parser.rows:
            if len(row)>=3 and re.fullmatch(r"MAL[0-9A-Za-z]+",row[1],re.I):
                records.append({"registration":row[1],"name":row[2]})
        if not records and re.search(r"\d", name) and not registration:
            broad=re.split(r"\s+\d",name,1)[0].strip()
            if broad and broad!=name:
                html=_quest_read("content.php", {"func":"search","searchBy":"1","searchTxt":broad,"cat":"1"})
                parser=_Rows(); parser.feed(html)
                records=[{"registration":row[1],"name":row[2]} for row in parser.rows if len(row)>=3 and re.fullmatch(r"MAL[0-9A-Za-z]+",row[1],re.I)]
        exact=[r for r in records if r["registration"].casefold()==name.casefold() or r["name"].casefold()==name.casefold()]
        chosen=exact[0] if len(exact)==1 else None
        if not chosen:
            result.update(status="ambiguous" if records else "unverified", candidates=records[:6], note="NPRA Malaysia: select the exact product name, strength and form (or enter its MAL registration number)." if records else "No NPRA pharmaceutical record returned. Recheck the packaging; do not guess the ingredient.")
        else:
            path=_quest_read("content.php",{"func":"detail","reg":chosen["registration"],"cat":"1"}).strip()
            if not re.fullmatch(r"detail\.php\?type=product&id=[A-Za-z0-9]+",path): raise ValueError("NPRA detail format unavailable")
            detail=_quest_read(path)
            if chosen["registration"] not in detail: raise ValueError("registration mismatch")
            table=re.search(r'<table\b[^>]*id=["\']tab1["\'][^>]*>(.*?)</table>', detail,re.S|re.I)
            if not table: raise ValueError("ingredient table unavailable")
            ingredients=_Rows(); ingredients.feed(table.group(0))
            names=[row[1] for row in ingredients.rows if len(row)==2 and row[0].isdigit() and row[1]]
            if not names: raise ValueError("no active ingredients returned")
            result.update(status="verified",matched_name=chosen["name"],ingredients=names,note="Exact NPRA Malaysian product record; identity only, not a dose or safety approval.")
            result["sources"]=[{"title":"NPRA QUEST3+ — "+chosen["registration"],"url":_QUEST+path}]
        result["checked_at"]=datetime.now(timezone.utc).isoformat()
        return result
    except Exception:
        result["note"]="NPRA lookup unavailable. Product identity has not been confirmed; retry or ask a pharmacist."
        return result


def verify_medicine(name, language="English"):
    name=(name or "").strip()
    if not name or len(name)>150:
        return {"query":name,"status":"unverified","rxcui":None,"matched_name":None,"ingredients":[],"candidates":[],"sources":[],"note":"Enter the product name as printed, not a long question."}
    key="npra:"+name.casefold()
    cached=_cache_get(key)
    if cached is not None: return cached
    result=_npra(name)
    if result["status"]=="unverified" and result["note"].startswith("No NPRA"):
        generic=re.split(r"\s+\d",name,1)[0].strip()
        nlm=_verify_nlm(generic,language)
        if nlm["status"]=="verified" and generic.casefold() in {i.casefold() for i in nlm["ingredients"]}:
            result=nlm
            result["query"]=name
            result["note"]="Generic ingredient identity from RxNorm; not confirmation of a Malaysian brand or supplied formulation."
    # An empty or offline Malaysian lookup never authorizes a US brand substitution.
    # Explicit generic ingredient input can still be discussed as supplied input.
    _CACHE[key]=(time.time()+(1800 if result["status"]!="unverified" else 60),result)
    return result


def verify_medicines(names, language="English"):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda name: verify_medicine(name,language), names[:4]))
