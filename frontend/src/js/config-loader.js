// config-loader.js — resolves runtime config once, for the whole app.
//
// `config.js` is NOT committed (git-ignored). It is written next to index.html either by
// the CI deploy workflow (from the SAM `ApiBaseUrl` output) or by hand for local testing.
// It must contain ONLY a public API base URL — never secrets, model ids, or credentials.
//
// If `config.js` is absent, the app stays fully usable in OFFLINE mode: services resolve a
// typed "not connected yet" error and no network call is made. This loader never throws.

const OFFLINE_DEFAULT = Object.freeze({ apiBaseUrl: '', liveMode: false });

let cached = null;

// Resolve config exactly once. Returns a frozen { apiBaseUrl, liveMode } object.
// `config.js` lives at frontend/config.js, i.e. two levels up from src/js/.
export async function loadConfig() {
  if (cached) return cached;
  try {
    // Relative to this module: ../../config.js  → frontend/config.js
    const mod = await import('../../config.js');
    const cfg = (mod && (mod.config || mod.default)) || {};
    const apiBaseUrl = typeof cfg.apiBaseUrl === 'string' ? cfg.apiBaseUrl.trim() : '';
    // liveMode is only honoured when an apiBaseUrl is actually present.
    const liveMode = Boolean(cfg.liveMode) && apiBaseUrl.length > 0;
    cached = Object.freeze({ apiBaseUrl: apiBaseUrl.replace(/\/+$/, ''), liveMode });
  } catch (_) {
    // No config.js (offline) — stay unconnected, never throw.
    cached = OFFLINE_DEFAULT;
  }
  return cached;
}

// Synchronous accessor for code paths that run after loadConfig() has resolved.
export function getConfig() {
  return cached || OFFLINE_DEFAULT;
}
