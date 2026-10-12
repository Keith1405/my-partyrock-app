"""
SmartMed Cycle — My Return Plan (streaming Flask Lambda).

Provides a short, localized preparation checklist and links to the official
MyMediSAFE locator. Does not identify photos or invent collection-point records.
Streams deterministic text; no model call is needed.
"""
import json
import os
import re

import patient_safety
from flask import Flask, Response, request, stream_with_context

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Malaysia postcode -> "City, State" lookup (bundled, offline, public domain).
# Source: AsyrafHussin/malaysia-postcodes (from Pos Malaysia data). Lets us
# resolve ANY Malaysian postcode exactly instead of letting the model guess
# (e.g. 80200 -> Johor Bahru, Johor, not a hallucinated town).
# ---------------------------------------------------------------------------
_POSTCODE_PATH = os.path.join(os.path.dirname(__file__), "postcodes_my.json")
try:
    with open(_POSTCODE_PATH, "r", encoding="utf-8") as _f:
        POSTCODES = (json.load(_f) or {}).get("postcodes", {}) or {}
except Exception:  # noqa: BLE001
    POSTCODES = {}

_POSTCODE_RE = re.compile(r"\b(\d{5})\b")

def resolve_location(location):
    """Resolve a 5-digit Malaysian postcode found in the free-text location to
    an exact 'City, State'. Returns a dict:
      {found: bool, postcode: str|None, place: str|None, nearest: bool, note: str}
    - exact match  -> found=True, nearest=False
    - no postcode at all / not in Malaysia list -> found=False
    """
    out = {"found": False, "postcode": None, "place": None, "nearest": False, "note": ""}
    if not POSTCODES:
        out["note"] = "postcode table unavailable"
        return out
    m = _POSTCODE_RE.search(location or "")
    if not m:
        out["note"] = "no 5-digit postcode in the location text"
        return out
    pc = m.group(1)
    out["postcode"] = pc
    if pc in POSTCODES:
        out["found"] = True
        out["place"] = POSTCODES[pc]
        out["note"] = "exact postcode match"
        return out
    out["note"] = f"postcode {pc} not found in the Malaysia table"
    return out


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

# ---------------------------------------------------------------------------
# Lightweight abuse guards (per-instance; best-effort, not a substitute for WAF)
# ---------------------------------------------------------------------------
import time
from collections import deque

MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", 8 * 1024 * 1024))
RATE_MAX = int(os.environ.get("RATE_MAX", 30))
RATE_WINDOW = int(os.environ.get("RATE_WINDOW", 60))
_hits = deque()

def _rate_limited():
    now = time.time()
    while _hits and now - _hits[0] > RATE_WINDOW:
        _hits.popleft()
    if len(_hits) >= RATE_MAX:
        return True
    _hits.append(now)
    return False

def _guard():
    length = request.content_length or 0
    if length > MAX_BODY_BYTES:
        return 413, "Payload too large."
    if _rate_limited():
        return 429, "Too many requests — slow down and try again shortly."
    return None



RETURN_COPY = {
    "English": ["What to do now", "A collection point has not been confirmed yet.", "Open the official MyMediSAFE locator and search using your town or postcode.", "Call the listed centre to check its address, hours and whether it accepts your items before travelling.", "Keep medicines in their original packaging, cover personal details and seal liquids. Do not flush or put medicines in household rubbish.", "Ask your usual pharmacy or clinic to help find and telephone a collection centre if you cannot use the locator.", "Needles: keep separately in a suitable sharps container. Inhalers: do not puncture. Confirm acceptance first.", "Before returning medicine still prescribed to you, ask your pharmacist/prescriber. Do not stop treatment simply because you feel better.", "Your location", "Enter a town or valid five-digit Malaysian postcode. Keep any town already supplied when correcting a postcode.", "No medicine has been identified from the photo. Type the label if you can, or bring the labelled packaging to a pharmacist.", "Collection policies"],
    "Bahasa Melayu": ["Apa yang perlu dibuat sekarang", "Pusat pengumpulan belum disahkan.", "Buka pencari lokasi rasmi MyMediSAFE dan cari menggunakan bandar atau poskod anda.", "Telefon pusat yang disenaraikan untuk menyemak alamat, waktu operasi dan penerimaan ubat anda sebelum pergi.", "Simpan ubat dalam pembungkusan asal, tutup maklumat peribadi dan tutup botol cecair dengan kemas. Jangan buang ubat ke tandas atau tong sampah rumah.", "Jika tidak dapat menggunakan pencari lokasi, minta farmasi atau klinik biasa anda membantu mencari dan menelefon pusat pengumpulan.", "Jarum: asingkan dalam bekas benda tajam yang sesuai. Inhaler: jangan tebuk. Sahkan penerimaan dahulu.", "Sebelum memulangkan ubat yang masih dipreskripsikan, tanya ahli farmasi/doktor. Jangan hentikan rawatan hanya kerana sudah rasa sihat.", "Lokasi anda", "Masukkan bandar atau poskod Malaysia lima digit yang sah. Kekalkan nama bandar yang telah diberi semasa membetulkan poskod.", "Tiada ubat dikenal pasti daripada foto. Taip label jika boleh, atau bawa pembungkusan berlabel kepada ahli farmasi.", "Dasar penerimaan"],
    "中文": ["现在该怎么做", "尚未确认具体回收点。", "打开 MyMediSAFE 官方定位工具，按城市或邮政编码搜索。", "出发前致电所列中心，确认地址、营业时间及是否接受您的物品。", "保留药物原包装，遮盖个人资料并拧紧液体瓶盖。不要将药物冲入厕所或放入家庭垃圾。", "如果不会使用定位工具，请让常去的药房或诊所帮助查找并致电回收中心。", "针头：分开放入合适的锐器容器。吸入器：不要刺穿。先确认中心是否接受。", "退回仍在处方疗程中的药物前，请咨询药剂师或医生。不要只因感觉好转就自行停止治疗。", "您的位置", "请输入城市或有效的马来西亚五位邮政编码。更正邮编时请保留已提供的城市。", "没有根据照片识别药物。可以输入标签内容，或将带标签的包装交给药剂师查看。", "接收政策"],
}

def generate(body):
    language = body.get("preferred_language", "English")
    c = RETURN_COPY.get(language, RETURN_COPY["English"])
    item = body.get("return_item_details", "") or ""
    location = body.get("your_location", "") or ""
    warning = patient_safety.validation(item, language)
    if warning:
        yield "⚠️ " + warning
        return
    yield "⚠️ " + c[7] + "\n\n"
    yield "## ♻️ " + c[0] + "\n" + c[1] + "\n"
    loc = resolve_location(location)
    if loc["found"]:
        yield c[8] + ": " + loc["place"] + "\n"
    else:
        # A supplied town remains useful even if a postcode is wrong/missing.
        # A broad state/village still needs a district; do not invent geography.
        towns = {part.strip() for place in POSTCODES.values() for part in str(place).split(",")[:-1]}
        town = next((t for t in sorted(towns, key=lambda t: (-len(t), t)) if t and re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", location, re.I)), None)
        if town:
            yield c[8] + ": " + town + "\n"
            if _POSTCODE_RE.search(location): yield "⚠️ " + c[9] + "\n"
        else:
            yield "⚠️ " + c[9] + "\n"
    yield "1. " + c[2] + " [MyMediSAFE](https://www.mymedisafe.org.my/index.html)\n"
    yield "2. " + c[3] + "\n3. " + c[4] + "\n\n" + c[5] + "\n"
    yield c[6] + "\n"
    if body.get("file_data"):
        yield c[10] + "\n"
    yield "[" + c[11] + "](https://www.mymedisafe.org.my/faq.html)"

@app.route("/", methods=["POST", "OPTIONS"])
def handler():
    if request.method == "OPTIONS":
        return Response(status=200, headers=CORS_HEADERS)
    rejected = _guard()
    if rejected:
        status, message = rejected
        resp = Response(message, status=status, content_type="text/plain; charset=utf-8")
        for key, value in CORS_HEADERS.items():
            resp.headers[key] = value
        return resp
    body = request.get_json(silent=True) or {}
    resp = Response(
        stream_with_context(generate(body)),
        content_type="text/plain; charset=utf-8",
    )
    for key, value in CORS_HEADERS.items():
        resp.headers[key] = value
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
