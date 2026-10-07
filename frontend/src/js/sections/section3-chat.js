// sections/section3-chat.js — Ask About My Medicines.
// Emergency notice is static in index.html. Chat works with Sections 1-2 empty.
// A short static welcome is shown; answers are generated ONLY after the user submits a
// non-empty question. No sample/canned answers, no auto quiz, no auto pharmacist summary.
// While the backend is unconnected, the chat service resolves a typed 'serviceUnavailable'
// error and we show the chat-unavailable message, preserving the user's typed question.
// Emergency routing (all three languages) is handled by the real chat service in Stage 3.

import { getLanguage, createOutput, bumpRevision } from '../state.js';
import { t } from '../i18n.js';
import { chatRespond } from '../services/index.js';

export function initSection3() {
  const thread = document.getElementById('s3-thread');
  const form = document.getElementById('s3-form');
  const input = document.getElementById('s3-input');

  const chatOut = createOutput('chat');
  let loadingEl = null;

  function appendMessage(text, kind) {
    const el = document.createElement('div');
    el.className = 'chat-msg ' + kind;
    el.textContent = text;
    thread.append(el);
    thread.scrollTop = thread.scrollHeight;
    return el;
  }

  function resetThread() {
    thread.innerHTML = '';
    // Static welcome only — NOT a generated answer, no sample content.
    appendMessage(t('chat.welcome', getLanguage()), 'bot');
  }

  // Generate an answer ONLY from a non-empty user-submitted question. No auto quiz,
  // no auto pharmacist summary, no canned replies. While the backend is unconnected the
  // service resolves a typed 'serviceUnavailable' error and we show the chat-unavailable
  // message, keeping the user's typed question available (not cleared on failure).
  async function send(rawMessage) {
    const text = (rawMessage || '').trim();
    if (!text) {
      // Whitespace-only or empty: do not call the service; show a brief instruction.
      appendMessage(t('need.s3.empty', getLanguage()), 'bot');
      return;
    }

    appendMessage(text, 'user');
    bumpRevision('chat');
    const captured = getChatRevisionSnapshot();

    chatOut.set('loading');
    loadingEl = appendMessage(t('status.loading', getLanguage()), 'bot loading');

    let result;
    try {
      result = await chatRespond({ message: text, lang: getLanguage() });
    } catch (err) {
      removeLoading();
      chatOut.set('error', { error: { message: String(err) } });
      appendMessage('⚠️ ' + t('svc.chat', getLanguage()), 'bot');
      return;
    }

    removeLoading();

    // If the conversation was cleared while the request was in flight, ignore the result
    // so a stale/old response can never reappear in a reset thread.
    if (chatCleared(captured)) return;

    if (!result.ok) {
      chatOut.set('error', { requestId: result.requestId, error: result.error });
      const key = result.error && result.error.feature ? 'svc.' + result.error.feature : 'svc.chat';
      appendMessage('⚠️ ' + t(key, getLanguage()), 'bot');
      return;
    }

    chatOut.set('success', { requestId: result.requestId, data: result.data });
    const kind = result.data.intent === 'emergency' ? 'bot emergency' : 'bot';
    appendMessage(result.data.text, kind);
  }

  function removeLoading() {
    if (loadingEl && loadingEl.parentNode) loadingEl.parentNode.removeChild(loadingEl);
    loadingEl = null;
  }

  // Track clears so a late response from before a clear is discarded.
  let clearToken = 0;
  function getChatRevisionSnapshot() { return clearToken; }
  function chatCleared(captured) { return clearToken !== captured; }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const message = input.value;
    input.value = '';
    send(message);
  });

  // Example chips INSERT their question into the input and focus it — the user must press
  // Send. They do not auto-generate (no automatic quiz or pharmacist summary).
  document.querySelectorAll('[data-chat-example]').forEach((btn) => {
    btn.addEventListener('click', () => {
      input.value = btn.textContent;
      input.focus();
    });
  });

  document.querySelector('[data-chat-clear]').addEventListener('click', () => {
    bumpRevision('chat');
    clearToken += 1; // discard any in-flight response from before this clear
    removeLoading();
    chatOut.set('idle', { data: null, error: null });
    resetThread();
  });

  resetThread();

  return {
    // The chat renders inline rather than through a single output body, but expose a
    // minimal hook so the dev harness can still exercise its state machine + messages.
    outputs: {
      's3-chat': {
        output: chatOut,
        body: thread,
        render: () => {},
        devAppend: appendMessage
      }
    }
  };
}
