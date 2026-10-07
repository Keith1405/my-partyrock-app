// main.js — app shell. Imports state/i18n/services; renders chrome; applies language
// switching; smooth in-page nav; initialises each section; wires the ?dev=1 harness.

import { t, LANGUAGES } from './i18n.js';
import { getLanguage, setLanguage, subscribe } from './state.js';
import * as services from './services/index.js';
import { loadConfig } from './config-loader.js';
import { renderStatus } from './sections/shared.js';
import { initSection1 } from './sections/section1-medicine.js';
import { initSection2 } from './sections/section2-precautions.js';
import { initSection3 } from './sections/section3-chat.js';
import { initSection4 } from './sections/section4-returns.js';
import { STATUSES } from './state.js';

// ---- i18n chrome application ----------------------------------------------

function applyI18n() {
  const lang = getLanguage();
  document.documentElement.lang = lang;

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.getAttribute('data-i18n'), lang);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder'), lang));
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
    el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria-label'), lang));
  });
}

function initLanguageSwitch() {
  const select = document.getElementById('lang-switch');
  select.innerHTML = '';
  for (const l of LANGUAGES) {
    const opt = document.createElement('option');
    opt.value = l.value;
    opt.textContent = l.label;
    select.append(opt);
  }
  select.value = getLanguage();
  select.addEventListener('change', () => setLanguage(select.value));

  subscribe('language', () => {
    select.value = getLanguage();
    applyI18n();
  });
}

// ---- Smooth in-page navigation --------------------------------------------

function initNav() {
  document.querySelectorAll('.site-nav a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Move focus for keyboard/AT users without adding it to the tab order permanently.
      target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    });
  });
}

// ---- Dev fixture harness (?dev=1) -----------------------------------------

function initDevHarness(sectionApis) {
  const params = new URLSearchParams(window.location.search);
  if (params.get('dev') !== '1') return; // hidden entirely when the flag is absent

  const mount = document.getElementById('dev-harness');
  mount.hidden = false;

  const title = document.createElement('h2');
  title.textContent = t('dev.title', getLanguage());
  mount.append(title);

  // Flatten every registered output.
  const outputs = {};
  for (const api of sectionApis) {
    if (api && api.outputs) Object.assign(outputs, api.outputs);
  }

  // Force-state controls per output.
  Object.entries(outputs).forEach(([key, entry]) => {
    const group = document.createElement('div');
    group.className = 'dev-group';
    const label = document.createElement('strong');
    label.textContent = key + ' — ' + t('dev.forceState', getLanguage());
    group.append(label);

    STATUSES.forEach((status) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = status;
      btn.addEventListener('click', () => {
        if (status === 'success') {
          // Drive the output through the REAL service via its run button. While the backend
          // is unconnected this surfaces the honest "not connected yet" message — the dev
          // harness never injects sample success content into the patient-facing app.
          runRealSuccess(key, entry);
          return;
        }
        entry.output.set(status, { data: status === 'success' ? entry.output.data : null });
        if (entry.render) entry.render();
        else renderStatus(entry.output, entry.body);
        if (entry.devAppend && (status === 'error' || status === 'loading')) {
          entry.devAppend('[dev] forced ' + status, 'bot');
        }
      });
      group.append(btn);
    });
    mount.append(group);
  });

  // Single-module simulated failure: arm one service to reject on its next call.
  const failGroup = document.createElement('div');
  failGroup.className = 'dev-group';
  const failLabel = document.createElement('strong');
  failLabel.textContent = t('dev.failOn', getLanguage());
  failGroup.append(failLabel);

  const serviceNames = [
    'extractFromPhoto',
    'buildMedicineCard',
    'buildPrecautionsSummary',
    'chatRespond',
    'prepareReturnPlan'
  ];
  const sel = document.createElement('select');
  for (const name of serviceNames) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.append(opt);
  }
  const armBtn = document.createElement('button');
  armBtn.type = 'button';
  armBtn.textContent = t('dev.failNext', getLanguage());
  armBtn.addEventListener('click', () => {
    services.armFailure(sel.value);
    armBtn.textContent = '✓ armed: ' + sel.value;
    setTimeout(() => { armBtn.textContent = t('dev.failNext', getLanguage()); }, 1500);
  });
  failGroup.append(sel, armBtn);
  mount.append(failGroup);
}

async function runRealSuccess(key, entry) {
  // Trigger the matching run button so the output goes through the real state machine
  // (currently the unconnected-service path). No fixtures are injected.
  const runBtn = document.querySelector('[data-run="' + key + '"]');
  if (runBtn) { runBtn.click(); return; }
  // Chat has no single run button; note that it is driven by a submitted question.
  if (entry.devAppend) entry.devAppend('[dev] chat is driven by a submitted question', 'bot');
}

// ---- Boot ------------------------------------------------------------------

async function boot() {
  // Resolve runtime config first (optional config.js → apiBaseUrl/liveMode). Never throws;
  // if absent the app stays offline and services report "not connected yet".
  await loadConfig();

  applyI18n();
  initLanguageSwitch();
  initNav();

  const sectionApis = [];
  // Each section initialises independently; a failure in one must not stop the others.
  for (const init of [initSection1, initSection2, initSection3, initSection4]) {
    try {
      sectionApis.push(init());
    } catch (err) {
      console.error('[main] section init failed (contained):', err);
    }
  }

  initDevHarness(sectionApis);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
