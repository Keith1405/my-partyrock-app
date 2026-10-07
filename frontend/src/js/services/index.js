// Typed Medicine Cards organise the user's own text locally, without AI.
// Other services remain unavailable until their real backends are connected.
// There are no sample responses or inferred prescription details.
import { nextRequestId } from '../state.js';
import { getConfig } from '../config-loader.js';

const DELAY_MS = 300;          // small delay only for the offline "unavailable" path (UX)
const REQUEST_TIMEOUT_MS = 30000;

// Which backend route + not-connected message bucket each service maps to.
const SERVICE_META = {
  extractFromPhoto: { feature: 'extraction', path: '/extract-from-photo' },
  buildMedicineCard: { feature: 'extraction', path: '/build-medicine-card' },
  buildPrecautionsSummary: { feature: 'ai', path: '/build-precautions-summary' },
  chatRespond: { feature: 'chat', path: '/chat-respond' },
  prepareReturnPlan: { feature: 'search', path: '/prepare-return-plan' }
};

// Dev-harness hook: when a service name is armed, its NEXT call fails once (no fixtures).
const failOnce = new Set();
export function armFailure(serviceName) { failOnce.add(serviceName); }
export function isArmed(serviceName) { return failOnce.has(serviceName); }

function delay(ms = DELAY_MS) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function typedError(code, feature, message, requestId) {
  return {
    ok: false,
    error: { code, feature, message },
    requestId,
    sourceProvenance: 'none'
  };
}

// The honest outcome when a service's backend is not connected.
async function unavailable(serviceName) {
  const requestId = nextRequestId();
  await delay();
  const meta = SERVICE_META[serviceName] || { feature: 'ai' };
  failOnce.delete(serviceName);
  return typedError('serviceUnavailable', meta.feature,
    'This feature is not connected yet.', requestId);
}

// POST JSON to the configured API with a bounded timeout. Returns the parsed body or
// throws a tagged Error ({ kind }) the caller maps to a typed error.
async function postJson(url, payload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
      mode: 'cors'
    });
  } catch (err) {
    clearTimeout(timer);
    const e = new Error(err && err.name === 'AbortError' ? 'timeout' : 'network');
    e.kind = err && err.name === 'AbortError' ? 'timeout' : 'network';
    throw e;
  }
  clearTimeout(timer);

  let body = null;
  try {
    body = await res.json();
  } catch (_) {
    const e = new Error('badJson'); e.kind = 'badJson'; throw e;
  }
  if (!res.ok) {
    // Backend returned a structured error envelope; surface its code/message.
    const e = new Error('httpError');
    e.kind = 'httpError';
    e.status = res.status;
    e.body = body;
    throw e;
  }
  return body;
}

// ---------------------------------------------------------------------------
// Medicine Card response validation (client side).
// The backend is the authority, but we re-validate defensively so a malformed
// response is treated as an error, never rendered. Shape MUST match the renderer
// in sections/section1-medicine.js. Missing fields default to "Not provided".
// ---------------------------------------------------------------------------

const NOT_PROVIDED = 'Not provided';

function str(v, fallback = NOT_PROVIDED) {
  if (typeof v !== 'string') return fallback;
  const s = v.trim();
  return s.length ? s : fallback;
}

function strList(v) {
  if (!Array.isArray(v)) return [];
  return v.map((x) => (typeof x === 'string' ? x.trim() : '')).filter(Boolean);
}

// Returns a normalised card object, or null if the payload is not a usable card.
function normaliseMedicineCard(data) {
  if (!data || typeof data !== 'object') return null;
  const identity = data.identity && typeof data.identity === 'object' ? data.identity : {};
  const label = data.label && typeof data.label === 'object' ? data.label : {};

  // Name is the one field that must be present for a card to mean anything.
  const name = str(identity.name, '');
  if (!name) return null;

  const sources = Array.isArray(data.sources)
    ? data.sources
        .filter((s) => s && typeof s === 'object' && typeof s.url === 'string')
        .map((s) => ({ title: str(s.title, s.url), url: s.url }))
    : [];

  return {
    draftNote: str(data.draftNote, 'Draft only — compare with your original label.'),
    identity: {
      name,
      strength: str(identity.strength),
      form: str(identity.form)
    },
    label: {
      take: str(label.take),
      howOften: str(label.howOften),
      howToTake: str(label.howToTake),
      forHowLong: str(label.forHowLong)
    },
    plainWords: str(data.plainWords),
    whatItIsFor: str(data.whatItIsFor),
    needsChecking: strList(data.needsChecking),
    extra: str(data.extra),
    sourcesNote: str(data.sourcesNote,
      'Reference links are shown for general information; nothing was retrieved live for your specific medicine.'),
    sources,
    footer: str(data.footer, '➡️ For precautions go to Section 2. For questions go to Section 3.')
  };
}

// --- Section 1: Medicine Card (LIVE) ---------------------------------------

// buildMedicineCard({ details, upload, extract, lang, ageGroup })
// Typed-entry path (this stage): sends the typed `details` + language/age to the backend.
// Requires a configured live backend; otherwise returns the honest unavailable error.
export async function buildMedicineCard(input = {}) {
  const requestId = nextRequestId();
  const data = makeTypedMedicineCard(input.details, input.lang);
  if (!data) return { ok: true, empty: true, data: null, requestId, sourceProvenance: 'none' };
  const cfg = getConfig();
  if (cfg.liveMode && cfg.apiBaseUrl) {
    const result = await requestAIMedicineCard(input);
    if (result.ok) return result;
    const messages = {
      en: 'AI explanation is unavailable. This draft contains only details from your entry.',
      ms: 'Penerangan AI tidak tersedia. Draf ini hanya mengandungi butiran daripada input anda.',
      zh: 'AI 说明暂时不可用。此草稿仅包含您输入的详情。'
    };
    data.warnings.push(messages[input.lang] || messages.en);
  }
  return { ok: true, data, requestId, sourceProvenance: 'userTyped' };
}

async function requestAIMedicineCard(input = {}) {
  const requestId = nextRequestId();
  const meta = SERVICE_META.buildMedicineCard;
  const cfg = getConfig();

  // Dev-harness forced failure (no network, no fixtures).
  if (failOnce.has('buildMedicineCard')) {
    failOnce.delete('buildMedicineCard');
    await delay();
    return typedError('serviceUnavailable', meta.feature,
      'Simulated failure (dev harness).', requestId);
  }

  // No backend configured → honest "not connected yet".
  if (!cfg.liveMode || !cfg.apiBaseUrl) {
    await delay();
    return typedError('serviceUnavailable', meta.feature,
      'Medicine extraction is not connected yet.', requestId);
  }

  // Caller (Section 1) already validated that there is typed text or a usable extraction.
  const payload = {
    requestId,
    details: typeof input.details === 'string' ? input.details : '',
    lang: input.lang || 'en',
    ageGroup: input.ageGroup || 'notProvided'
    // NOTE: typed entry only this stage. Photo/extract wiring is a separate stage.
  };

  let body;
  try {
    body = await postJson(cfg.apiBaseUrl + meta.path, payload);
  } catch (err) {
    const map = {
      timeout: ['timeout', 'The request timed out. Please try again.'],
      network: ['network', 'Could not reach the service. Check your connection and try again.'],
      badJson: ['internal', 'The service returned an unreadable response. Please try again.'],
      httpError: null
    };
    if (err.kind === 'httpError') {
      const be = err.body && err.body.error;
      const code = (be && be.code) || 'internal';
      const message = (be && be.message) || ('The service reported an error (HTTP ' + err.status + ').');
      return typedError(code, meta.feature, message, requestId);
    }
    const [code, message] = map[err.kind] || ['internal', 'Something went wrong. Please try again.'];
    return typedError(code, meta.feature, message, requestId);
  }

  // Backend envelope: { ok, data|error, requestId, sourceProvenance }.
  if (!body || body.ok !== true) {
    const be = body && body.error;
    return typedError((be && be.code) || 'internal', meta.feature,
      (be && be.message) || 'The service could not build a Medicine Card.', requestId);
  }

  const card = normaliseMedicineCard(body.data);
  if (!card) {
    return typedError('internal', meta.feature,
      'The Medicine Card response was incomplete. Please try again.', requestId);
  }

  return {
    ok: true,
    data: card,
    requestId: body.requestId || requestId,
    sourceProvenance: body.sourceProvenance || 'liveModel'
  };
}

// --- Services not wired in this stage (still honest) -----------------------

export function extractFromPhoto(_input = {}) { return unavailable('extractFromPhoto'); }
export function buildPrecautionsSummary(_input = {}) { return unavailable('buildPrecautionsSummary'); }
export function chatRespond(_input = {}) { return unavailable('chatRespond'); }
export function prepareReturnPlan(_input = {}) { return unavailable('prepareReturnPlan'); }

// A local draft of user-supplied text. No AI, medicine lookup or dose recommendation.
// Recognise a small set of explicit English label patterns; retain everything else
// verbatim for review. Missing/unrecognised information is never inferred.
const COPY = {
  en: {
    title: 'Medicine Card — draft', missing: 'Not provided / not recognised',
    note: 'Details copied from your entry. Compare this draft with your medicine label; it is not a recommended prescription.',
    original: 'Your original entry', missingTitle: 'Missing details', check: 'Please check',
    labels: ['Medicine name', 'Strength as entered', 'Form', 'Amount each time', 'Frequency', 'Duration', 'Other label instructions'],
    unit: 'The unit “ng” needs checking against the original label. It has not been changed to “mg”.',
    complex: 'This entry may contain multiple medicines or conflicting details. The original text is kept below; enter one medicine at a time to organise its fields.',
    unknown: 'Some wording could not be organised. It remains in your original entry below. Add or correct details above and rebuild the card.',
    complete: 'All displayed fields were found in your entry. This does not confirm that the instructions are correct or safe.'
  },
  ms: {
    title: 'Kad Ubat — draf', missing: 'Tidak diberikan / tidak dikenal pasti',
    note: 'Butiran disalin daripada input anda. Bandingkan draf dengan label ubat; ini bukan cadangan preskripsi.',
    original: 'Input asal anda', missingTitle: 'Butiran yang belum lengkap', check: 'Sila semak',
    labels: ['Nama ubat', 'Kekuatan seperti ditaip', 'Bentuk', 'Jumlah setiap kali', 'Kekerapan', 'Tempoh', 'Arahan label lain'],
    unit: 'Semak unit “ng” pada label asal. Unit ini tidak ditukar kepada “mg”.',
    complex: 'Input mungkin mengandungi beberapa ubat atau butiran bercanggah. Teks asal dikekalkan di bawah; masukkan satu ubat pada satu masa.',
    unknown: 'Sebahagian teks tidak dapat disusun. Teks asal dikekalkan di bawah. Tambah atau betulkan butiran dan bina semula kad.',
    complete: 'Semua medan ditemui dalam input anda. Ini tidak mengesahkan bahawa arahan itu betul atau selamat.'
  },
  zh: {
    title: '药物卡 — 草稿', missing: '未提供 / 未识别',
    note: '详情来自您输入的内容。请与原药物标签核对；这不是建议处方。',
    original: '您的原始输入', missingTitle: '缺少的详情', check: '请核对',
    labels: ['药物名称', '输入的规格', '剂型', '每次用量', '频率', '疗程', '其他标签指示'],
    unit: '请核对原标签上的“ng”单位。系统没有将其改为“mg”。',
    complex: '输入可能包含多种药物或相互矛盾的详情。原文保留在下方；请每次输入一种药物。',
    unknown: '部分内容未能整理，已保留在下方原文中。请补充或更正后重新生成药物卡。',
    complete: '所有显示的字段均来自您的输入。这不代表指示正确或安全。'
  }
};

const PATTERNS = {
  strength: /\b\d+(?:\.\d+)?\s*(?:mg|mcg|ng|µg|μg|g|ml|iu|%)(?:\s*\/\s*(?:\d+(?:\.\d+)?\s*)?(?:ml|tablet|capsule))?(?![a-z])/gi,
  frequency: /\b(?:once|twice|three times|four times|\d+\s*times)\s+(?:a\s+day|per\s+day|daily|weekly)|\bevery\s+\d+\s*hours?\b|\bonce\s+(?:a\s+week|weekly)\b|\bdaily\b/gi,
  duration: /\b(?:for\s+)?\d+\s*(?:days?|weeks?|months?)\b/gi,
  amount: /\b(?:(?:take|use)\s+)?(?:one|two|three|four|half|\d+(?:\.\d+)?|\d+\/\d+)\s*(?:tablets?|capsules?|puffs?|drops?|sachets?)\b/gi,
  form: /\b(?:tablets?|capsules?|cream|ointment|inhaler|syrup|solution|drops?|sachets?)\b/gi,
  instructions: /\b(?:with\s+(?:food|meals?|water)|after\s+(?:food|meals?)|before\s+(?:food|meals?)|on an empty stomach|at bedtime|as needed)\b/gi
};

function matches(text, pattern) {
  return [...text.matchAll(new RegExp(pattern.source, pattern.flags))];
}

export function makeTypedMedicineCard(details, lang = 'en') {
  const raw = typeof details === 'string' ? details.trim() : '';
  if (!raw) return null;
  const c = COPY[lang] || COPY.en;
  const found = Object.fromEntries(Object.entries(PATTERNS).map(([k, p]) => [k, matches(raw, p)]));
  const first = (key) => found[key][0]?.[0] || null;
  // Never combine several schedules or strengths into a guessed prescription.
  const complex = ['strength', 'frequency', 'duration', 'amount'].some(k => found[k].length > 1)
    || /\n|;|\b(?:and|plus)\b/i.test(raw);
  const values = { name: null, strength: null, form: null, amount: null, frequency: null, duration: null, instructions: null };
  let nameEnd = 0;
  if (!complex) {
    for (const key of Object.keys(PATTERNS)) values[key] = first(key);
    const starts = Object.values(found).flat().map(m => m.index);
    nameEnd = starts.length ? Math.min(...starts) : raw.length;
    const candidate = raw.slice(0, nameEnd).replace(/[\s—–,:-]+$/u, '').trim();
    // Free-text name is explicitly unverified. Do not treat question/instruction prose as a drug name.
    if (candidate && /^[\p{L}][\p{L}\p{N}\s'’().-]*$/u.test(candidate)
      && candidate.split(/\s+/).length <= 6 && !/\b(?:take|use|what|how|please|medicine name)\b/i.test(candidate)) {
      values.name = candidate;
    }
  }
  const keys = ['name', 'strength', 'form', 'amount', 'frequency', 'duration', 'instructions'];
  const fields = keys.map((key, i) => ({ key, label: c.labels[i], value: values[key], missing: !values[key] }));
  const missing = fields.filter(f => f.missing).map(f => f.label);
  const warnings = [];
  if (complex) warnings.push(c.complex);
  if (/\d\s*ng\b/i.test(raw)) warnings.push(c.unit);
  // Any unparsed remainder stays visible in the original input, never silently discarded.
  let remaining = raw;
  for (const p of Object.values(PATTERNS)) remaining = remaining.replace(new RegExp(p.source, p.flags), ' ');
  if (values.name) remaining = remaining.replace(values.name, '');
  if (!complex && remaining.replace(/[\s—–,.:()-]/g, '')) warnings.push(c.unknown);
  return {
    kind: 'typedDraft', sourceProvenance: 'userTyped', clinicalReview: 'notAssessed',
    rawInput: raw, fields, missing, warnings, copy: c,
    identity: { name: values.name, strength: values.strength, form: values.form },
    label: { take: values.amount, howOften: values.frequency, forHowLong: values.duration, howToTake: values.instructions }
  };
}
