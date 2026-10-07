// sections/upload.js — reusable upload handler with preview, replace, remove,
// unsupported-extension rejection, and object-URL revoke.
//
// Memory only: the chosen file lives in memory for the session and is never persisted.
// NO network: object URLs are created locally for preview and revoked on remove/clear.

import { t } from '../i18n.js';
import { getLanguage } from '../state.js';

const IMAGE_EXT = ['jpg', 'jpeg', 'png', 'webp'];

export function createUpload({ inputId, previewId, errorId, accept, onChange }) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  const errorEl = document.getElementById(errorId);

  let currentFile = null;
  let objectUrl = null;

  function revoke() {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }
  function clearError() {
    errorEl.textContent = '';
    errorEl.hidden = true;
  }

  function extensionOf(name) {
    const dot = name.lastIndexOf('.');
    return dot >= 0 ? name.slice(dot + 1).toLowerCase() : '';
  }

  function renderPreview() {
    revoke();
    preview.innerHTML = '';
    if (!currentFile) {
      preview.hidden = true;
      return;
    }
    const lang = getLanguage();
    const ext = extensionOf(currentFile.name);

    if (IMAGE_EXT.includes(ext)) {
      objectUrl = URL.createObjectURL(currentFile);
      const img = document.createElement('img');
      img.src = objectUrl;
      img.alt = 'Preview of ' + currentFile.name;
      preview.append(img);
    } else {
      // PDF (or other accepted non-image): filename chip, no image preview.
      const chip = document.createElement('span');
      chip.className = 'file-chip';
      chip.textContent = '📄 ' + currentFile.name + ' — ' + t('upload.pdfChip', lang);
      preview.append(chip);
    }

    const actions = document.createElement('div');
    actions.className = 'preview-actions';

    const replaceBtn = document.createElement('button');
    replaceBtn.type = 'button';
    replaceBtn.className = 'btn';
    replaceBtn.textContent = t('btn.replace', lang);
    replaceBtn.addEventListener('click', () => input.click());

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn ghost';
    removeBtn.textContent = t('btn.remove', lang);
    removeBtn.addEventListener('click', () => remove());

    actions.append(replaceBtn, removeBtn);
    preview.append(actions);
    preview.hidden = false;
  }

  function remove() {
    revoke();
    currentFile = null;
    input.value = '';
    preview.innerHTML = '';
    preview.hidden = true;
    clearError();
    if (typeof onChange === 'function') onChange();
  }

  input.addEventListener('change', () => {
    clearError();
    const file = input.files && input.files[0];
    if (!file) {
      // Dialog cancelled; keep whatever we had.
      return;
    }
    const ext = extensionOf(file.name);
    if (!accept.includes(ext)) {
      // Reject in-section only; do not touch other sections.
      input.value = '';
      showError(t('upload.rejected', getLanguage()));
      return;
    }
    currentFile = file;
    renderPreview();
    if (typeof onChange === 'function') onChange();
  });

  return {
    getFile: () => currentFile,
    clear: remove,
    refreshLabels: () => { if (currentFile) renderPreview(); }
  };
}
