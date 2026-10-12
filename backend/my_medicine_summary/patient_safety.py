"""Conservative input checks, not a prescription or clinical validation."""
import re

COPY = {
    "dose": ("The dose amount has no unit. Copy the amount AND unit exactly from your label; do not guess.", "Jumlah dos tiada unit. Salin jumlah DAN unit tepat seperti pada label; jangan teka.", "剂量数值没有单位。请按标签填写数值和单位，不要猜测。"),
    "negative": ("The quantity or dose cannot be negative. Correct the value or leave it blank if unsure.", "Kuantiti atau dos tidak boleh negatif. Betulkan nilai atau biarkan kosong jika tidak pasti.", "数量或剂量不能为负数。请更正，不确定时请留空。"),
    "error": ("The service could not finish. Please try again. No complete result was saved.", "Perkhidmatan tidak dapat diselesaikan. Sila cuba lagi. Tiada keputusan lengkap disimpan.", "服务未能完成。请重试。未保存完整结果。"),
    "bleeding": ("Warfarin with aspirin or ibuprofen needs a pharmacist/prescriber check because bleeding risk can increase. Check each listed medicine before adding or changing it. Do not stop prescribed medicines on your own.", "Warfarin bersama aspirin atau ibuprofen perlu disemak oleh ahli farmasi/doktor kerana risiko pendarahan boleh meningkat. Semak setiap ubat sebelum menambah atau mengubahnya. Jangan hentikan ubat preskripsi sendiri.", "Warfarin 与 aspirin 或 ibuprofen 合用可能增加出血风险，请让药剂师或医生逐一核对。添加或更改药物前先咨询，不要自行停用处方药。"),
    "allergy": ("You reported a penicillin allergy and entered amoxicillin. Contact your pharmacist/prescriber before taking it. If breathing difficulty or face/throat swelling is happening now, call 999.", "Anda melaporkan alahan penicillin dan memasukkan amoxicillin. Hubungi ahli farmasi/doktor sebelum mengambilnya. Jika sukar bernafas atau muka/tekak bengkak sekarang, hubungi 999.", "您报告了 penicillin 过敏并输入了 amoxicillin。服用前请联系药剂师或医生。如果现在呼吸困难或面部、喉咙肿胀，请拨打 999。"),
}
def translated(key, language):
    return COPY[key][{"English": 0, "Bahasa Melayu": 1, "中文": 2}.get(language, 0)]

def validation(text, language):
    if re.search(r"(?<![\w\d])[-−]\s*\d+(?:[.,]\d+)?", text or ""):
        return translated("negative", language)
    # A number immediately followed by frequency has no explicit dose unit.
    # Strength ratios (250 mg/5 mL) are not used to infer the taking amount.
    for match in re.finditer(r"(?:\b(?:take|ambil|makan)\b|服用|每次)\s*(\d+(?:[.,]\d+)?)\s*([^\n.;]*)", text or "", re.I):
        unit = match.group(2)
        if not re.match(r"(?:ml|mg|mcg|g|tablets?|tabs?|capsules?|caps?|puffs?|drops?|units?|iu|biji|tablet|kapsul|titis|片|粒|毫升|毫克|单位)(?:\b|(?=[\u4e00-\u9fff]))", unit, re.I):
            return translated("dose", language)
    return ""

def candidate_names(*texts):
    """Extract label name lines, including brand-only and MAL registration input.
    These are search queries, not identified medicines. Never trust rendered cards.
    """
    names=[]
    stop=re.compile(r"^(?:take|ambil|makan|dose|dos|quantity|jumlah|allerg|none|not sure|unknown|draf|draft|heart|form|strength|instruction|route|frequency|morning|evening|tablet|capsule|liquid|suspension|suppository|no known)\b", re.I)
    for text in texts:
        for line in re.split(r"[\n;]+", text or ""):
            line=line.strip()
            mal=re.search(r"\bMAL[0-9]{8}[A-Za-z]+\b",line,re.I)
            if mal: candidate=mal.group(0)
            else:
                line=re.sub(r"^(?:medicine(?: name)?|brand(?: name)?|nama ubat)\s*:\s*", "",line,flags=re.I)
                line=re.sub(r"^[^A-Za-z]+(?=[A-Za-z])", "", line)
                candidate=re.split(r"(?:\.\s|\s[-—]\s|\b(?:take|ambil|makan|once|twice|daily|sehari)\b)",line,1,flags=re.I)[0].strip(' .,:')
                if not candidate or stop.search(candidate) or len(candidate)>100: continue
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 +'’()/.,%-]*",candidate): continue
            if candidate.casefold() not in {n.casefold() for n in names}: names.append(candidate)
    return names[:4]

def clinical_alerts(raw, other, allergies, language):
    text = (raw + "\n" + other).lower()
    alerts = []
    if re.search(r"\bwarfarin\b", text) and re.search(r"\b(?:aspirin|ibuprofen)\b", text):
        alerts.append(translated("bleeding", language) + "\n[NHS](https://www.nhs.uk/medicines/warfarin/)")
    # Do not suppress an uncertain or historical reaction. The alert states what
    # was reported and asks for a professional check; it does not diagnose.
    if re.search(r"\bamoxicillin\b", text) and re.search(r"\bpenicillin\b", allergies or "", re.I) and not re.fullmatch(r"\s*(?:no|none|no known allergies|tiada|无)\s*", allergies or "", re.I):
        alerts.append(translated("allergy", language) + "\n[NHS](https://www.nhs.uk/medicines/amoxicillin/who-can-and-cannot-take-amoxicillin/)")
    return alerts
