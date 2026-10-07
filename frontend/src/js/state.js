// state.js — tiny pub/sub store + per-output state machine factory.
//
// Shared slices:
//   language  : 'en' | 'ms' | 'zh'   (PERSISTED to localStorage; the only persisted value)
//   ageGroup  : repaired non-overlapping boundaries (MEMORY ONLY)
//
// Four independent health-data slices (medicine, precautions, chat, return), each with a
// stable id and a monotonically increasing `revision`. These are MEMORY ONLY — no patient
// text or images ever touch localStorage/sessionStorage.

const LANG_KEY = 'smartmed.language';
const VALID_LANGS = ['en', 'ms', 'zh'];
const VALID_AGE = [
  'notProvided',
  'child0to12',
  'teen13to17',
  'adult18to59',
  'older60plus'
];

function loadLanguage() {
  try {
    const stored = localStorage.getItem(LANG_KEY);
    if (stored && VALID_LANGS.includes(stored)) return stored;
  } catch (_) {
    // localStorage may be unavailable (private mode / file://); fall back silently.
  }
  return 'en';
}

function persistLanguage(lang) {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch (_) {
    // Ignore persistence failures; language simply stays in memory for the session.
  }
}

// ---- Shared store ----------------------------------------------------------

const shared = {
  language: loadLanguage(),
  ageGroup: 'notProvided'
};

const subscribers = {
  language: new Set(),
  ageGroup: new Set()
};

export function getLanguage() {
  return shared.language;
}

export function setLanguage(lang) {
  if (!VALID_LANGS.includes(lang) || lang === shared.language) return;
  shared.language = lang;
  persistLanguage(lang);
  notify('language', lang);
}

export function getAgeGroup() {
  return shared.ageGroup;
}

export function setAgeGroup(age) {
  if (!VALID_AGE.includes(age) || age === shared.ageGroup) return;
  shared.ageGroup = age;
  notify('ageGroup', age);
}

export function subscribe(sliceKey, fn) {
  if (!subscribers[sliceKey]) subscribers[sliceKey] = new Set();
  subscribers[sliceKey].add(fn);
  return () => subscribers[sliceKey].delete(fn);
}

function notify(sliceKey, value) {
  const set = subscribers[sliceKey];
  if (!set) return;
  for (const fn of set) {
    try {
      fn(value);
    } catch (err) {
      // A subscriber error must not break the store or other subscribers.
      console.error('[state] subscriber error for', sliceKey, err);
    }
  }
}

// ---- Independent health-data slices (memory only) --------------------------

function makeSlice(id) {
  return { id, revision: 0 };
}

export const slices = {
  medicine: makeSlice('medicine'),
  precautions: makeSlice('precautions'),
  chat: makeSlice('chat'),
  return: makeSlice('return')
};

// The current usable Medicine Card (Section 1 → Section 2 dependency), memory only.
// Section 2 may only generate precautions when this holds a usable card. It is set by
// Section 1 on a successful card build and cleared when Section 1 inputs are cleared or
// change. Modules never import each other; they share through here.
let currentMedicineCard = null;

export function setMedicineCard(card) {
  currentMedicineCard = card || null;
}

export function getMedicineCard() {
  return currentMedicineCard;
}

export function hasUsableMedicineCard() {
  return currentMedicineCard != null;
}

// Bumping a slice revision marks any in-flight request for that slice as stale,
// so a late response can never overwrite newer input.
export function bumpRevision(sliceKey) {
  const slice = slices[sliceKey];
  if (!slice) return 0;
  slice.revision += 1;
  return slice.revision;
}

export function getRevision(sliceKey) {
  const slice = slices[sliceKey];
  return slice ? slice.revision : 0;
}

// ---- Per-output state machine ---------------------------------------------

export const STATUSES = Object.freeze([
  'idle',
  'loading',
  'success',
  'empty',
  'error',
  'retry',
  'stale'
]);

let requestCounter = 0;
export function nextRequestId() {
  requestCounter += 1;
  return 'req-' + requestCounter;
}

// createOutput(sliceKey) → a small observable state machine for one output panel.
export function createOutput(sliceKey) {
  const listeners = new Set();
  const output = {
    sliceKey,
    status: 'idle',
    requestId: null,
    inputRevision: getRevision(sliceKey),
    data: null,
    error: null,

    onChange(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },

    set(status, patch = {}) {
      if (!STATUSES.includes(status)) {
        throw new Error('[state] invalid output status: ' + status);
      }
      output.status = status;
      if ('requestId' in patch) output.requestId = patch.requestId;
      if ('inputRevision' in patch) output.inputRevision = patch.inputRevision;
      if ('data' in patch) output.data = patch.data;
      if ('error' in patch) output.error = patch.error;
      emit();
    },

    // True when the slice has advanced past the revision this request captured.
    isStale(capturedRevision) {
      return getRevision(sliceKey) !== capturedRevision;
    }
  };

  function emit() {
    for (const fn of listeners) {
      try {
        fn(output);
      } catch (err) {
        console.error('[state] output listener error', err);
      }
    }
  }

  return output;
}
