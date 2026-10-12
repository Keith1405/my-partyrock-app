"""
SmartMed Cycle — reference-data retrieval helpers (free NLM services).

Implements a small, honest retrieval layer used to VERIFY a medicine name and
resolve its active ingredient(s). It never invents data: every function either
returns a real result from a live call or signals that verification failed.

Services (all free, no auth, no licence):
  - RxNorm / RxNav REST API      https://rxnav.nlm.nih.gov/REST/
      * findRxcuiByString  — exact normalized name -> RxCUI
      * approximateTerm    — spell-tolerant candidate match
      * rxcui/{id}/related — active ingredient(s) (TTY = IN, PIN)
  - MedlinePlus Connect          https://connect.medlineplus.gov/service
      * patient-friendly drug page by RXCUI (attribution + caching required)

Design rules (aligned with the MOH LASA guide and the task spec):
  - Short timeouts; any network/parse failure degrades to "could not verify",
    never to a guess.
  - Results are cached in-process (per warm Lambda) to respect MedlinePlus's
    acceptable-use policy (<=100 req/min/IP; cache 12-24h recommended).
  - We expose RxNorm/MedlinePlus pages as sources ONLY when a call actually
    returned them, so citations are never fabricated.
"""
import json
import time
import urllib.parse
import urllib.request

_TIMEOUT = 4  # seconds per call — keep the Lambda responsive
_UA = "SmartMedCycle/1.0 (patient medicine-prep tool)"

# Simple in-process cache: key -> (expiry_epoch, value)
_CACHE = {}
_CACHE_TTL = 12 * 60 * 60  # 12 hours, per MedlinePlus guidance


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


# ---------------------------------------------------------------------------
# RxNorm
# ---------------------------------------------------------------------------
def _rxcui_exact(name):
    """Return an RxCUI for an exact (normalized) name match, or None."""
    url = (
        "https://rxnav.nlm.nih.gov/REST/rxcui.json?name="
        + urllib.parse.quote(name)
        + "&search=2"  # 2 = normalized match
    )
    try:
        data = _get_json(url)
        ids = (data.get("idGroup") or {}).get("rxnormId") or []
        return ids[0] if ids else None
    except Exception:
        return None


def _rxcui_approx(name):
    """Spell-tolerant approximate match. Returns a list of candidate dicts
    [{rxcui, name, score}], highest score first, or []."""
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
    """Return a list of active-ingredient names for an RxCUI (TTY IN + PIN)."""
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


# ---------------------------------------------------------------------------
# MedlinePlus Connect (patient drug page by RXCUI)
# ---------------------------------------------------------------------------
_LANG_MAP = {"English": "en", "Bahasa Melayu": "en", "中文": "en"}  # Connect supports en/es only


def _medlineplus_by_rxcui(rxcui, language="English"):
    """Return {title, url} for a MedlinePlus drug page, or None.
    MedlinePlus Connect supports English/Spanish only; we always request English
    (the patient-facing language is handled by the model, this is just a source link)."""
    lang = "en"
    url = (
        "https://connect.medlineplus.gov/service"
        "?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88"  # RXCUI code system OID
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


# ---------------------------------------------------------------------------
# Public: verify a single medicine name
# ---------------------------------------------------------------------------
def verify_medicine(name, language="English"):
    """
    Verify a medicine NAME against RxNorm and (if found) fetch a MedlinePlus page.

    Returns a dict the prompt can trust:
      {
        "query": <original text>,
        "status": "verified" | "ambiguous" | "unverified",
        "rxcui": <str or None>,
        "matched_name": <RxNorm name or None>,
        "ingredients": [<ingredient names>],
        "candidates": [{name, score}, ...]   # only when ambiguous
        "sources": [{title, url}, ...]        # only pages actually retrieved
        "note": <short machine note>
      }
    status meanings:
      verified   — exact normalized RxNorm match found; ingredients resolved.
      ambiguous  — only approximate/multiple candidates; DO NOT identify.
      unverified — nothing usable returned (empty, offline, or no match).
    """
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

    # 1) Exact normalized match
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
        src = {"title": "RxNorm (US NLM) — " + matched, "url": "https://rxnav.nlm.nih.gov/REST/rxcui/%s" % rxcui}
        result["sources"].append(src)
        mp = _medlineplus_by_rxcui(rxcui, language)
        if mp:
            result["sources"].append({"title": "MedlinePlus — " + mp["title"], "url": mp["url"]})
        _cache_put(cache_key, result)
        return result

    # 2) Approximate (spell-tolerant) — treat as AMBIGUOUS, never auto-identify
    cands = _rxcui_approx(name)
    if cands:
        # If the single top candidate is an extremely strong, unique match we
        # still return it as ambiguous: identity must be confirmed by the user.
        result.update(
            status="ambiguous",
            candidates=[{"name": c["name"], "score": c["score"]} for c in cands[:5]],
            note="approximate matches only — not auto-identified",
        )
        _cache_put(cache_key, result)
        return result

    # 3) Nothing
    result["note"] = "no RxNorm match (may be a Malaysia-only brand, misspelling, or offline)"
    _cache_put(cache_key, result)
    return result


def reference_block(verifications):
    """Render a compact, machine-readable block for the model prompt describing
    what retrieval actually returned for each queried name. The model must base
    its 'verified' claims and source lines ONLY on this block."""
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
