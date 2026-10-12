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
import directory
import urllib.parse
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

# Deterministic response template: no generative model is needed for a return plan.
# All medicine details below are patient-entered, not a verified product identity.
FRAME = {
    "English": {
        "return":"Your return", "medicine":"Medicine", "amount":"Amount", "reason":"Reason", "missing":"Not provided",
        "expired":"Expired — **do not take them**", "damaged":"Damaged — **do not use them**", "unwanted":"No longer needed", "completed":"Course completed",
        "prepare":"Prepare and keep safely", "point":"Listed collection point", "address":"Address", "directions":"Directions", "call":"**Call before going** to confirm opening hours and acceptance.",
        "pack":"Keep medicines in their **original pack** and follow its storage instructions.",
        "privacy":"**Cross out personal details**; keep the medicine name visible. Remove the Farmatag hologram on packs being returned.",
        "store":"Store separately from medicines you use, **away from children and pets**.",
        "waste":"**Do not put medicines in rubbish, the toilet or sink**.",
        "liquid":"Keep medicines in their **original pack**; close liquid bottles tightly and follow the storage instructions.",
        "sharps":"Keep needles in a **suitable sharps container**, away from medicines; **call to check acceptance**. Do not puncture inhalers.",
        "check":"**Check the label:** the entered paracetamol amount is unusual. Confirm whether it is the strength or a total amount; do not guess. If this is an amount already taken, **seek urgent medical help**, even if you feel well.",
        "prescribed":"**Check with your pharmacist** before returning medicine still prescribed to you.",
        "location":"Enter a valid **town or postcode**. Check that any town and postcode agree.",
        "approx":"Selected using approximate town/postcode coordinates; your exact nearest centre may differ.",
        "sources":"Sources", "checked":"Directory checked", "phone":"Phone",
    },
    "Bahasa Melayu": {
        "return":"Ubat untuk dipulangkan", "medicine":"Ubat", "amount":"Kuantiti", "reason":"Sebab", "missing":"Belum diberi",
        "expired":"Tamat tempoh — **jangan ambil ubat ini**", "damaged":"Rosak — **jangan gunakan ubat ini**", "unwanted":"Tidak diperlukan lagi", "completed":"Rawatan selesai",
        "prepare":"Sediakan dan simpan dengan selamat", "point":"Pusat pengumpulan yang disenaraikan", "address":"Alamat", "directions":"Arah perjalanan", "call":"**Telefon sebelum pergi** untuk mengesahkan waktu operasi dan penerimaan.",
        "pack":"Simpan ubat dalam **pek asal** dan ikut arahan penyimpanannya.",
        "privacy":"**Padam maklumat peribadi**; pastikan nama ubat masih kelihatan. Musnahkan hologram Farmatag pada pek yang dipulangkan.",
        "store":"Asingkan daripada ubat yang masih digunakan, **jauh daripada kanak-kanak dan haiwan peliharaan**.",
        "waste":"**Jangan buang ubat ke tong sampah, tandas atau sinki**.",
        "liquid":"Simpan ubat dalam **pek asal**; tutup botol cecair dengan rapat dan ikut arahan penyimpanan.",
        "sharps":"Simpan jarum dalam **bekas benda tajam yang sesuai**, berasingan daripada ubat; **telefon untuk menyemak penerimaan**. Jangan tebuk inhaler.",
        "check":"**Semak label:** jumlah paracetamol yang dimasukkan luar biasa. Sahkan sama ada kekuatan atau jumlah keseluruhan; jangan teka. Jika jumlah ini sudah diambil, **dapatkan bantuan perubatan segera**, walaupun rasa sihat.",
        "prescribed":"**Semak dengan ahli farmasi** sebelum memulangkan ubat yang masih dipreskripsikan.",
        "location":"Masukkan **bandar atau poskod** yang sah. Pastikan bandar dan poskod sepadan.",
        "approx":"Dipilih berdasarkan koordinat bandar/poskod anggaran; pusat paling dekat dengan lokasi tepat anda mungkin berbeza.",
        "sources":"Sumber", "checked":"Direktori disemak", "phone":"Telefon",
    },
    "中文": {
        "return":"您的退回药物", "medicine":"药物", "amount":"数量", "reason":"原因", "missing":"未提供",
        "expired":"已过期 — **请勿服用**", "damaged":"已损坏 — **请勿使用**", "unwanted":"不再需要", "completed":"疗程结束",
        "prepare":"准备并安全存放", "point":"列出的回收点", "address":"地址", "directions":"路线", "call":"**出发前致电**确认营业时间及是否接受您的物品。",
        "pack":"保留药物**原包装**，并遵循包装上的储存说明。",
        "privacy":"**划去个人资料**，保留可见的药物名称。销毁准备退回包装上的 Farmatag 防伪标签。",
        "store":"与仍在使用的药物分开存放，**远离儿童和宠物**。",
        "waste":"**不要将药物放入垃圾、厕所或水槽**。",
        "liquid":"保留药物**原包装**；拧紧液体瓶盖，并遵循储存说明。",
        "sharps":"针头应放入**合适的锐器容器**，与药物分开；**致电确认是否接受**。不要刺穿吸入器。",
        "check":"**核对标签：**您输入的 paracetamol 数量异常。请确认是规格还是总量，不要猜测。如果已经服用了这个量，**立即寻求医疗帮助**，即使没有不适。",
        "prescribed":"退回仍在处方疗程中的药物前，**先咨询药剂师**。",
        "location":"请输入有效的**城市或邮编**，并确认两者一致。",
        "approx":"按城市或邮编的估算坐标选择；您实际最近的中心可能不同。",
        "sources":"来源", "checked":"目录核对日期", "phone":"电话",
    },
}


def _plain(text):
    """Source/input text cannot inject Markdown links, headings or HTML."""
    return re.sub(r"[\[\]<>*`_#|]", "", str(text)).replace("\n", " ").strip()


def _return_details(text):
    """Conservative parsing of raw return-item text; never infer dose or identity.
    Missing/ambiguous fields stay missing. Quantity means stock, not a dose.
    """
    text=str(text or "")[:4000]
    first=re.split(r"[\n;]|\.\s",text,1)[0].strip()
    first=re.sub(r"^(?:medicine|medicine name|ubat|nama ubat|药物|药名)\s*:\s*", "",first,flags=re.I)
    # Explicit quantity fields can include liquids or other non-tablet forms.
    explicit=re.search(r"(?:amount|quantity|remaining|kuantiti|baki|数量)\s*:\s*([^\n;]+)",text,re.I)
    quantity=re.search(r"\b\d+\s*(?:tablets?|tabs?|capsules?|caps?|suppositor(?:y|ies)|patch(?:es)?|sachets?|biji|kapsul|tablet)\b|\d+\s*[片粒]",text,re.I)
    amount=explicit.group(1).strip()[:80] if explicit else quantity.group(0) if quantity else ""
    if quantity and quantity.start()<len(first): first=first[:quantity.start()]
    first=re.split(r",|\b(?:expired|damaged|no longer needed|unwanted|course completed|tamat tempoh|rosak|tidak diperlukan|rawatan selesai|amount|quantity|remaining)\b|过期|损坏|不再需要|疗程结束|数量",first,1,flags=re.I)[0].strip(' .—-:')
    # Bare instructions, unknown text and numeric fragments are not product names.
    if not first or len(first)>120 or re.match(r"^(?:\d|take\b|ambil\b|unknown\b|not sure\b|none\b|expired\b|damaged\b)",first,re.I): first=""
    patterns={
        "expired":r"\bexpired\b|tamat tempoh|已?过期",
        "damaged":r"\bdamaged\b|\brosak\b|损坏",
        "unwanted":r"no longer needed|\bunwanted\b|tidak diperlukan|不再需要",
        "completed":r"course completed|rawatan selesai|疗程结束",
    }
    # Negated expiry/damage is not a reason for return.
    reasons=[]
    for key,pattern in patterns.items():
        matches=list(re.finditer(pattern,text,re.I))
        if any(not re.search(r"(?:not|isn't|no|tidak|belum|未|没有)\s*$",text[max(0,m.start()-12):m.start()],re.I) for m in matches): reasons.append(key)
    return {"medicine":_plain(first),"amount":_plain(amount),"reason":reasons[0] if len(reasons)==1 else None}


def _unusual_paracetamol(text):
    # A label/amount check, not a full clinical dose assessment. No amount is fixed.
    if not re.search(r"\b(?:paracetamol|acetaminophen)\b",text,re.I): return False
    return any(float(m.group(1))*(1000 if m.group(2).lower()=="g" else 1)>1000
               for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(mg|g)\b",text,re.I))


def generate(body):
    language=body.get("preferred_language", "English")
    c=RETURN_COPY.get(language,RETURN_COPY["English"])
    f=FRAME.get(language,FRAME["English"])
    item=str(body.get("return_item_details", "") or "")
    location=str(body.get("your_location", "") or "")
    warning=patient_safety.validation(item,language)
    if warning:
        yield "⚠️ "+warning
        return
    detail=_return_details(item)
    # Critical input concerns appear before the normal three-section frame.
    if _unusual_paracetamol(item):
        yield "⚠️ "+f["check"]+" [NHS](https://www.nhs.uk/medicines/paracetamol-for-adults/)\n\n"
    yield "## 💊 "+f["return"]+"\n"
    yield "- **"+f["medicine"]+":** "+(detail["medicine"] or f["missing"])+".\n"
    yield "- **"+f["amount"]+":** "+(detail["amount"] or f["missing"])+".\n"
    yield "- **"+f["reason"]+":** "+(f[detail["reason"]] if detail["reason"] else f["missing"])+".\n"
    if body.get("file_data"): yield "- ⚠️ "+c[10]+"\n"
    if detail["reason"] not in ("expired","damaged"):
        yield "- ⚠️ "+f["prescribed"]+"\n"
    yield "\n## 📦 "+f["prepare"]+"\n"
    first=f["liquid"] if re.search(r"liquid|suspension|syrup|cecair|sirap|液体|糖浆",item,re.I) else f["pack"]
    yield "- "+first+"\n- "+f["privacy"]+"\n- "+f["store"]+"\n"
    special=bool(re.search(r"needle|sharps|jarum|inhaler|针|吸入",item,re.I))
    yield "- "+(f["sharps"]+" "+f["waste"] if special else f["waste"])+"\n"
    yield "\n## 📍 "+f["point"]+"\n"
    local=directory.listed_in_area(location)
    origin,points=(None,local[:1]) if local else directory.nearest(location,limit=1)
    if points:
        point=points[0]
        pin=str(point["latitude"])+","+str(point["longitude"])
        yield "- **"+_plain(point["name"])+"**\n"
        yield "- **"+f["address"]+":** "+_plain(point["description"])+".\n"
        link="[🗺️ "+f["directions"]+"](https://www.google.com/maps/dir/?api=1&destination="+urllib.parse.quote(pin)+")"
        yield "- "+("**📞 "+_plain(point["phone"])+"** · " if point["phone"] else "")+link+"\n"
        yield "- "+f["call"]+"\n"
        if origin: yield f["approx"]+"\n"
    else:
        yield "- ⚠️ "+f["location"]+" [MyMediSAFE](https://www.mymedisafe.org.my/index.html)\n"
    # A compact footer keeps the main answer short while retaining provenance.
    yield "\n"+f["sources"]+": [MyMediSAFE](https://www.mymedisafe.org.my/faq.html) · [MOH](https://infosihat.moh.gov.my/images/media_sihat/emagazine/EdisiSept2025/files/basic-html/page31.html)"
    yield " · ["+f["checked"]+": "+directory.DIRECTORY["checked_on"]+"](https://www.mymedisafe.org.my/index.html) · [GeoNames](https://www.geonames.org/) (CC BY 4.0)"

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
