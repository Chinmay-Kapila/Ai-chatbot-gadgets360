/**
 * Central place the widget resolves its FastAPI backend base URL from,
 * at RUNTIME rather than baked in at build time. This means the exact
 * same chatbot.js file can be pointed at production / staging / a
 * different environment purely via the embed <script> tag's
 * data-api-base-url attribute, with no rebuild required.
 *
 * IMPORTANT: wire this into the real project. Find wherever the
 * existing code currently builds its request URL (almost certainly
 * inside src/hooks/useChat.js — something like a hardcoded
 * "http://localhost:8000" or an `import.meta.env.VITE_API_BASE_URL`
 * constant) and replace it with `getApiBaseUrl()` from this file.
 */
export function getApiBaseUrl() {
  return (
    window.__G360_CHATBOT_API_BASE_URL__ ||
    (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
    'http://localhost:8000'
  )
}
