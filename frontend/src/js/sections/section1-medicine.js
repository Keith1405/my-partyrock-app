// sections/section1-medicine.js — Understand My Medicine.

import { t, LANGUAGES, AGE_OPTIONS } from '../i18n.js';
import {
  getLanguage, setLanguage, subscribe,
  getAgeGroup, setAgeGroup, bumpRevision,
  createOutput, setMedicineCard
} from '../state.js';
import { extractFromPhoto, buildMedicineCard } from '../services/index.js';
import { runOutput, renderStatus, renderGuidance } from './shared.js';
import { createUpload } from './upload.js';

function hasText(v) {
  return Boolean(v && v.trim());
}

const ACCEPT = ['jpg', 'jpeg', 'png', 'webp', 'pdf'];

export function initSection1() {
  const details = document.getElementById('s1-details');
  const langSelect = document.getElementById('s1-language');
  const ageSelect = document.getElementById('s1-age');

  // --- Preferred Language (bound to the SHARED language slice) ---
  function fillLanguageOptions() {
    const current = getLanguage();
    langSelect.innerHTML = '';
    for (const l of LANGUAGES) {
      const opt = document.createElement('option');
      opt.value = l.value;
      opt.textContent = l.label;
      langSelect.append(opt);
    }
    langSelect.value = current;
  }
  fillLanguageOptions();
  langSelect.addEventListener('change', () => setLanguage(langSelect.value));
  // Keep in sync if language changes elsewhere (header switch).
  subscribe('language', () => { langSelect.value = getLanguage(); });

  // --- Patient Age (repaired non-overlapping boundaries) ---
  function fillAgeOptions() {
    const lang = getLanguage();
    const current = getAgeGroup();
    ageSelect.innerHTML = '';
    for (const key of AGE_OPTIONS) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = t('age.' + key, lang);
      ageSelect.append(opt);
    }
    ageSelect.value = current;
  }
  fillAgeOptions();
  ageSelect.addEventListener('change', () => {
    setAgeGroup(ageSelect.value);
    invalidateMedicine();
  });
  subscribe('language', fillAgeOptions);

  // Typing medicine details bumps the slice revision (supersedes in-flight requests)
  // and invalidates any previously built Medicine Card that Section 2 depends on.
  details.addEventListener('input', () => {
    invalidateMedicine();
  });

  // --- Upload (preview / replace / remove / reject / revoke) ---
  const upload = createUpload({
    inputId: 's1-upload',
    previewId: 's1-upload-preview',
    errorId: 's1-upload-error',
    accept: ACCEPT,
    onChange: () => invalidateMedicine()
  });

  // --- Outputs ---
  const extractOut = createOutput('medicine');
  const cardOut = createOutput('medicine');
  const extractBody = document.querySelector('#s1-extract .output-body');
  const cardBody = document.querySelector('#s1-card .output-body');

  function invalidateMedicine() {
    bumpRevision('medicine');
    setMedicineCard(null);
    for (const out of [extractOut, cardOut]) {
      out.set('idle', { data: null, error: null });
    }
    renderExtract();
    renderCard();
  }

  function inputSnapshot() {
    return {
      details: details.value,
      upload: upload.getFile(),
      lang: getLanguage(),
      ageGroup: getAgeGroup()
    };
  }

  function renderExtract() {
    renderStatus(extractOut, extractBody, (data) => renderExtractCard(data));
  }
  function renderCard() {
    renderStatus(cardOut, cardBody, (data) => renderMedicineCard(data));
  }

  async function runExtract() {
    // "Extract from Photo" REQUIRES an actual uploaded file. A filename/preview alone
    // is not extracted information; with no file we show an instruction, not a result.
    if (!upload.getFile()) {
      bumpRevision('medicine');
      renderGuidance(extractOut, extractBody, 'need.s1.extract');
      return;
    }
    const snap = inputSnapshot();
    await runOutput(extractOut, extractBody, () => extractFromPhoto(snap));
    if (extractOut.status === 'success') renderExtract();
  }
  async function runCard() {
    // "Build Medicine Card" REQUIRES typed details OR a usable extraction. Missing or
    // unreadable details stay unknown — never fabricate a card from an empty input.
    const typed = hasText(details.value);
    const usableExtraction = extractOut.status === 'success' && extractOut.data;
    if (!typed && !usableExtraction) {
      bumpRevision('medicine');
      renderGuidance(cardOut, cardBody, 'need.s1.card');
      return;
    }
    const snap = inputSnapshot();
    snap.extract = usableExtraction ? extractOut.data : null;
    await runOutput(cardOut, cardBody, () => buildMedicineCard(snap), {
      emptyWhen: (data) => !data
    });
    if (cardOut.status === 'success') {
      setMedicineCard(cardOut.data);
      renderCard();
    } else {
      // Not connected / empty / error / stale → no usable card for Section 2.
      setMedicineCard(null);
    }
  }

  document.querySelector('[data-run="s1-extract"]').addEventListener('click', runExtract);
  document.querySelector('[data-run="s1-card"]').addEventListener('click', runCard);

  document.querySelector('[data-clear="s1-extract"]').addEventListener('click', () => {
    bumpRevision('medicine');
    extractOut.set('idle', { data: null, error: null });
    renderExtract();
  });
  document.querySelector('[data-clear="s1-card"]').addEventListener('click', () => {
    bumpRevision('medicine');
    setMedicineCard(null);
    cardOut.set('idle', { data: null, error: null });
    renderCard();
  });

  // Initial idle render.
  renderExtract();
  renderCard();

  // Expose outputs for the dev harness.
  return {
    outputs: {
      's1-extract': { output: extractOut, body: extractBody, render: renderExtract },
      's1-card': { output: cardOut, body: cardBody, render: renderCard }
    }
  };
}

// --- Renderers --------------------------------------------------------------

function renderExtractCard(data) {
  const root = document.createElement('div');
  root.className = 'result';

  const banner = document.createElement('p');
  banner.className = 'banner';
  banner.textContent = data.banner;
  root.append(banner);

  const title = document.createElement('p');
  title.textContent = data.title;
  root.append(title);

  for (const f of data.fields) {
    const p = document.createElement('p');
    p.className = 'fact';
    const strong = document.createElement('strong');
    strong.textContent = f.label + ':';
    p.append(strong, document.createTextNode(' ' + f.value));
    root.append(p);
  }

  const footer = document.createElement('p');
  footer.className = 'disclaimer';
  footer.textContent = data.footer;
  root.append(footer);
  return root;
}

function renderMedicineCard(data) {
  if (data.kind === 'typedDraft') return renderTypedDraft(data);
  const root = document.createElement('div');
  root.className = 'result';

  const h = document.createElement('h4');
  h.textContent = '💊 Medicine Card';
  root.append(h);

  const draft = document.createElement('p');
  draft.className = 'help small';
  draft.textContent = data.draftNote;
  root.append(draft);

  root.append(fact('🏷️ Name', data.identity.name));
  root.append(fact('💪 Strength', data.identity.strength));
  root.append(fact('💉 Form', data.identity.form));
  root.append(fact('🕐 Take', data.label.take));
  root.append(fact('🔁 How often', data.label.howOften));
  root.append(fact('🍽️ How to take', data.label.howToTake));
  root.append(fact('⏳ For how long', data.label.forHowLong));

  root.append(para('💬 Plain words: ' + data.plainWords));
  root.append(para('ℹ️ ' + data.whatItIsFor));

  const nh = document.createElement('h4');
  nh.textContent = '⚠️ Needs checking';
  root.append(nh);
  root.append(list(data.needsChecking));

  root.append(para('📦 Extra: ' + data.extra));

  const sh = document.createElement('h4');
  sh.textContent = '📚 Reference links';
  root.append(sh);
  const sNote = document.createElement('p');
  sNote.className = 'help small';
  sNote.textContent = data.sourcesNote;
  root.append(sNote);
  const ul = document.createElement('ul');
  for (const s of data.sources) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = s.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = s.title;
    li.append(a);
    ul.append(li);
  }
  root.append(ul);

  const footer = document.createElement('p');
  footer.className = 'disclaimer';
  footer.textContent = data.footer;
  root.append(footer);
  return root;
}

function fact(label, value) {
  const p = document.createElement('p');
  p.className = 'fact';
  const strong = document.createElement('strong');
  strong.textContent = label + ':';
  p.append(strong, document.createTextNode(' ' + value));
  return p;
}
function para(text) {
  const p = document.createElement('p');
  p.textContent = text;
  return p;
}
function list(items) {
  const ul = document.createElement('ul');
  for (const it of items) {
    const li = document.createElement('li');
    li.textContent = it;
    ul.append(li);
  }
  return ul;
}

// Render only text nodes: patient entries must never become HTML.
function renderTypedDraft(data) {
  const root = document.createElement('div');
  root.className = 'result';
  const title = document.createElement('h4');
  title.textContent = data.copy.title;
  root.append(title, para(data.copy.note));
  for (const field of data.fields) {
    root.append(fact(field.label, field.missing ? data.copy.missing : field.value));
  }
  if (data.missing.length) {
    const heading = document.createElement('h4');
    heading.textContent = data.copy.missingTitle;
    root.append(heading, list(data.missing));
  } else {
    root.append(para(data.copy.complete));
  }
  if (data.warnings.length) {
    const heading = document.createElement('h4');
    heading.textContent = data.copy.check;
    root.append(heading, list(data.warnings));
  }
  const heading = document.createElement('h4');
  heading.textContent = data.copy.original;
  const original = para(data.rawInput);
  original.style.whiteSpace = 'pre-wrap';
  root.append(heading, original);
  return root;
}
