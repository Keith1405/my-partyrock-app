// SmartMed Cycle — frontend runtime config.
//
// This file is intentionally created so the app can load without crashing when
// no deployed API is available yet. The app is designed to stay fully usable in
// offline mode and display honest "not connected yet" messages.

export const config = {
  // Replace with your deployed API base URL later, for example:
  // "https://abc123.execute-api.ap-southeast-1.amazonaws.com"
  // Leave blank to keep the app offline.
  apiBaseUrl: '',

  // Enable live backend mode only when apiBaseUrl is a real deployed URL.
  liveMode: false,
};

export default config;
