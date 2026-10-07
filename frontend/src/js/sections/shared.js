// sections/shared.js — small helpers shared by section modules.
// Not a section itself; keeps per-output state-machine wiring consistent and DRY.

import { t } from '../i18n.js';
import { getLanguage, getRevision } from '../state.js';

const STATUS_ICON = {
  idle: 'ℹ️',
  loading: '⏳',
  success: '✅',
  empty: '📭',
  error: '⚠️',
  retry: '🔁',
  stale: '🔄'
};

// Build a status chip where colour is ALWAYS paired with an icon + text label.
export function statusChip(status) {
  const lang = getLanguage();
  const el = document.createElement('span');
  el.className = 'status status-' + status;
  el.setAttribute('role', 'status');
  const icon = document.createElement('span');
  icon.className = 'status-icon';
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = STATUS_ICON[status] || '•';
  const label = document.createElement('span');
  label.className = 'status-label';
  label.textContent = t('status.' + status, lang);
  el.append(icon, label);
  return el;
}

export function escapeText(value) {
  return String(value == null ? '' : value);
}

// Dispatch a service call through an output's state machine with stale-supersede logic.
// servicePromiseFactory() must return the service Promise. renderData(data) renders success.
export async function runOutput(output, bodyEl, servicePromiseFactory, { emptyWhen } = {}) {
  const capturedRevision = getRevision(output.sliceKey);
  const retrying = output.status === 'error';
  output.set(retrying ? 'retry' : 'loading', { inputRevision: capturedRevision });
  renderStatus(output, bodyEl);

  let result;
  try {
    result = await servicePromiseFactory();
  } catch (err) {
    // Service functions resolve rather than reject, but guard anyway for containment.
    if (output.isStale(capturedRevision)) {
      output.set('stale');
    } else {
      output.set('error', { error: { message: String(err && err.message || err) } });
    }
    renderStatus(output, bodyEl);
    return;
  }

  // A newer input arrived while we were working — never overwrite it.
  if (output.isStale(capturedRevision)) {
    output.set('stale', { requestId: result.requestId });
    renderStatus(output, bodyEl);
    return;
  }

  if (!result.ok) {
    output.set('error', { requestId: result.requestId, error: result.error });
    renderStatus(output, bodyEl);
    return;
  }

  // Note: a not-connected backend resolves { ok:false, error.code:'serviceUnavailable' },
  // so it flows through the error branch above and is rendered by renderStatus() with the
  // feature-specific "not connected yet" message. Inputs are never cleared on this path.

  const isEmpty = result.empty || (typeof emptyWhen === 'function' && emptyWhen(result.data));
  if (isEmpty) {
    output.set('empty', { requestId: result.requestId, data: null });
  } else {
    output.set('success', { requestId: result.requestId, data: result.data });
  }
  renderStatus(output, bodyEl);
}

// Render the status chip + hint for non-success states. Success content is rendered by callers.
export function renderStatus(output, bodyEl, renderSuccess) {
  const lang = getLanguage();
  bodyEl.innerHTML = '';
  bodyEl.append(statusChip(output.status));

  if (output.status === 'success' && typeof renderSuccess === 'function') {
    bodyEl.append(renderSuccess(output.data));
    return;
  }

  const hintKey = {
    idle: 'status.idle.hint',
    empty: 'status.empty.hint',
    error: 'status.error.hint',
    stale: 'status.stale.hint'
  }[output.status];

  if (output.status === 'error' && output.error) {
    const err = output.error;
    if (err.code === 'serviceUnavailable') {
      // Honest "not connected yet" message keyed on the affected feature; inputs are kept.
      const msg = document.createElement('p');
      msg.className = 'status-hint';
      msg.textContent = t('svc.' + (err.feature || 'ai'), lang);
      bodyEl.append(msg);
      const kept = document.createElement('p');
      kept.className = 'status-hint';
      kept.textContent = t('svc.keepInputs', lang);
      bodyEl.append(kept);
    } else if (err.message) {
      const detail = document.createElement('p');
      detail.className = 'status-hint';
      detail.textContent = err.message;
      bodyEl.append(detail);
    }
  }
  if (hintKey) {
    const hint = document.createElement('p');
    hint.className = 'status-hint';
    hint.textContent = t(hintKey, lang);
    bodyEl.append(hint);
  }
}

// Render a short instruction/guidance message into an output body WITHOUT calling a
// service. Used when required input is missing: the output stays in a non-success,
// non-error "needs input" state and no backend request is made.
export function renderGuidance(output, bodyEl, i18nKey) {
  const lang = getLanguage();
  output.set('empty', { data: null, error: null });
  bodyEl.innerHTML = '';
  bodyEl.append(statusChip('empty'));
  const hint = document.createElement('p');
  hint.className = 'status-hint';
  hint.textContent = t(i18nKey, lang);
  bodyEl.append(hint);
}
