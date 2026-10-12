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

def verify_medicine(name, language="English"):
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
    lines = ["RETRIEVED REFERENCE DATA (RxNorm + MedlinePlus, live this request):"]
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
            cand = "; ".join(f"{c['name']} (score {c['score']})" for c in v["candidates"])
            lines.append(f"  approximate_candidates: {cand}")
        if v["sources"]:
            for s in v["sources"]:
                lines.append(f"  source: {s['title']} — {s['url']}")
    return "\n".join(lines)
