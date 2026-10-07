// sections/section2-precautions.js — Check My Precautions.
// Two adjacent optional fields + one summary. Blank = "not provided / not assessed".
// Works independently; an error here never disables other sections.

import { bumpRevision, createOutput } from '../state.js';
import { getLanguage, getAgeGroup, getMedicineCard, hasUsableMedicineCard } from '../state.js';
import { buildPrecautionsSummary } from '../services/index.js';
import { runOutput, renderStatus, renderGuidance } from './shared.js';

export function initSection2() {
  const other = document.getElementById('s2-other');
  const allergies = document.getElementById('s2-allergies');

  other.addEventListener('input', () => bumpRevision('precautions'));
  allergies.addEventListener('input', () => bumpRevision('precautions'));

  const summaryOut = createOutput('precautions');
  const body = document.querySelector('#s2-summary .output-body');

  function render() {
    renderStatus(summaryOut, body, (data) => renderSummary(data));
  }

  async function run() {
    // Precautions generate ONLY from a usable current Medicine Card (built in Section 1).
    // Blank allergies/supplements are allowed (they mean "Not provided", not "None") — but
    // with no Medicine Card there is nothing to assess, so we show an instruction, not a result.
    if (!hasUsableMedicineCard()) {
      bumpRevision('precautions');
      renderGuidance(summaryOut, body, 'need.s2.card');
      return;
    }
    const snap = {
      medicineCard: getMedicineCard(),
      otherMeds: other.value,     // optional; blank = Not provided
      allergies: allergies.value, // optional; blank = Not provided
      lang: getLanguage(),
      ageGroup: getAgeGroup()
    };
    await runOutput(summaryOut, body, () => buildPrecautionsSummary(snap));
    if (summaryOut.status === 'success') render();
  }

  document.querySelector('[data-run="s2-summary"]').addEventListener('click', run);
  document.querySelector('[data-clear="s2-summary"]').addEventListener('click', () => {
    bumpRevision('precautions');
    summaryOut.set('idle', { data: null, error: null });
    render();
  });

  render();

  return {
    outputs: {
      's2-summary': { output: summaryOut, body, render }
    }
  };
}

function renderSummary(data) {
  const root = document.createElement('div');
  root.className = 'result';

  const h = document.createElement('h4');
  h.textContent = data.title;
  root.append(h);

  root.append(section('💊 Your Instructions', [data.instructions]));
  root.append(section('👀 Watch Out For', data.watchOut));
  root.append(section('🍽️ Food and Drink', [data.foodAndDrink]));
  root.append(section('🗣️ Concerns to Discuss', data.concerns));
  root.append(section('❓ Ask Your Pharmacist', data.askPharmacist));

  const disc = document.createElement('p');
  disc.className = 'disclaimer';
  disc.textContent = data.disclaimer;
  root.append(disc);
  return root;
}

function section(title, items) {
  const wrap = document.createElement('div');
  const h = document.createElement('h4');
  h.textContent = title;
  wrap.append(h);
  const ul = document.createElement('ul');
  for (const it of items) {
    const li = document.createElement('li');
    li.textContent = it;
    ul.append(li);
  }
  wrap.append(ul);
  return wrap;
}
