// sections/section4-returns.js — Return Unused Medicines.
// Fully independent of Section 1: uses the expired Paracetamol fixture; amlodipine never
// appears here. Separate photo upload with its own preview/validation/revoke.

import { bumpRevision, createOutput, getLanguage } from '../state.js';
import { prepareReturnPlan } from '../services/index.js';
import { runOutput, renderStatus, renderGuidance } from './shared.js';
import { createUpload } from './upload.js';

function hasText(v) {
  return Boolean(v && v.trim());
}

const ACCEPT = ['jpg', 'jpeg', 'png', 'webp', 'pdf'];

export function initSection4() {
  const location = document.getElementById('s4-location');
  const item = document.getElementById('s4-item');

  location.addEventListener('input', () => bumpRevision('return'));
  item.addEventListener('input', () => bumpRevision('return'));

  const upload = createUpload({
    inputId: 's4-upload',
    previewId: 's4-upload-preview',
    errorId: 's4-upload-error',
    accept: ACCEPT,
    onChange: () => bumpRevision('return')
  });

  const planOut = createOutput('return');
  const body = document.querySelector('#s4-plan .output-body');

  function render() {
    renderStatus(planOut, body, (data) => renderPlan(data));
  }

  async function run() {
    // Generate ONLY from actual return text, a usable photo, OR a location-only search.
    // With none of these, show an instruction and call nothing. Returns are independent of
    // Section 1 (medicine entry) — nothing here is copied from the medicine card.
    const hasItemText = hasText(item.value);
    const hasPhoto = Boolean(upload.getFile());
    const hasLocation = hasText(location.value);
    if (!hasItemText && !hasPhoto && !hasLocation) {
      bumpRevision('return');
      renderGuidance(planOut, body, 'need.s4.input');
      return;
    }
    const snap = {
      location: location.value,     // a location alone is a valid collection-point search
      itemDetails: item.value,
      upload: upload.getFile(),
      lang: getLanguage()
    };
    await runOutput(planOut, body, () => prepareReturnPlan(snap));
    if (planOut.status === 'success') render();
  }

  document.querySelector('[data-run="s4-plan"]').addEventListener('click', run);
  document.querySelector('[data-clear="s4-plan"]').addEventListener('click', () => {
    bumpRevision('return');
    planOut.set('idle', { data: null, error: null });
    render();
  });

  render();

  return {
    outputs: {
      's4-plan': { output: planOut, body, render }
    }
  };
}

function renderPlan(data) {
  const root = document.createElement('div');
  root.className = 'result';

  const h = document.createElement('h4');
  h.textContent = data.title;
  root.append(h);

  root.append(fact('💊 Item', data.item.name));
  root.append(fact('🔢 Quantity', data.item.quantity));
  root.append(fact('❓ Reason', data.item.reason));
  root.append(fact('📦 Packaging', data.item.packaging));

  const sh = document.createElement('h4');
  sh.textContent = 'Steps';
  root.append(sh);
  const ul = document.createElement('ul');
  for (const s of data.steps) {
    const li = document.createElement('li');
    li.textContent = s;
    ul.append(li);
  }
  root.append(ul);

  const fh = document.createElement('h4');
  fh.textContent = data.facilitiesHeading;
  root.append(fh);
  for (const f of data.facilities) {
    const card = document.createElement('div');
    card.className = 'facility-card';
    const tag = document.createElement('span');
    tag.className = 'fictional-tag';
    tag.textContent = 'FICTIONAL DEMO SAMPLE';
    card.append(tag);
    const name = document.createElement('p');
    const strong = document.createElement('strong');
    strong.textContent = f.name;
    name.append(strong, document.createTextNode(' — ' + f.area));
    card.append(name);
    const note = document.createElement('p');
    note.className = 'help small';
    note.textContent = f.note;
    card.append(note);
    root.append(card);
  }

  const dir = document.createElement('p');
  const strong = document.createElement('strong');
  strong.textContent = '🔗 ' + data.directory.label + ': ';
  const a = document.createElement('a');
  a.href = data.directory.url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.textContent = data.directory.name;
  dir.append(strong, a);
  root.append(dir);

  const disc = document.createElement('p');
  disc.className = 'disclaimer';
  disc.textContent = data.disclaimer;
  root.append(disc);
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
