// SmartMed Cycle — frontend runtime config TEMPLATE (Stage 1 placeholder).
//
// This is an EXAMPLE. Copy it to `config.js` only when a real backend exists
// (Stage 3+). Right now the app runs fully offline with NO backend connected: patient
// actions show an honest "not connected yet" message and this file is not read.
//
// HOW IT WORKS LATER:
//   * The GitHub Actions deploy workflow (.github/workflows/deploy.yml) reads
//     the SAM stack output `ApiBaseUrl` after a real deploy and writes a
//     NON-SECRET `config.js` next to this file containing that URL.
//   * `config.js` is git-ignored (see .gitignore) so a developer's local or a
//     CI-generated value is never committed.
//
// SECURITY:
//   * This file holds a PUBLIC API base URL only. It must NEVER contain AWS
//     credentials, Bedrock model ids, account ids, or any secret. Those live on
//     the Lambda side (execution role + stack parameters), never in the browser.
//   * A missing `config.js` means the backend is not connected — the app must stay usable
//     (showing "not connected yet" beside each action) and must not throw.

export const config = {
  // Put the deployed API base URL here (SAM output `ApiBaseUrl`), e.g.
  // "https://abc123.execute-api.ap-southeast-1.amazonaws.com". No trailing slash
  // needed. Leave empty to keep the app offline ("not connected yet").
  apiBaseUrl: '',

  // Set true (AND set apiBaseUrl) to make Section 1 "Build Medicine Card" call the
  // real backend. When false or when apiBaseUrl is empty, the app stays offline and
  // every action reports "not connected yet" — no network call is made.
  liveMode: false,
};

export default config;

// LOCAL TESTING AGAINST A DEPLOYED API:
//   1. Deploy infra/template.yaml with your sandbox region, Bedrock model id, and
//      AllowedOrigin set to your local origin (e.g. http://localhost:8000).
//   2. Copy this file to `frontend/config.js` (git-ignored) and set:
//        apiBaseUrl: '<the ApiBaseUrl output>', liveMode: true
//   3. Serve the frontend (serve.ps1) and use Section 1 with typed input.
// config.js must contain ONLY this public URL — never AWS credentials or model ids.
