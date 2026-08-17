import { createRoot } from 'react-dom/client'
import ChatWidget from './components/ChatWidget'
// The `?inline` suffix tells Vite to return the compiled Tailwind CSS
// as a plain string instead of auto-injecting a <link>/<style> into
// document.head — we inject it ourselves, INSIDE the shadow root below,
// so it stays fully scoped to the widget.
import stylesheet from './index.css?inline'

const CONTAINER_ID = 'g360-chatbot-widget-root'

/**
 * Reads config off the currently-executing <script> tag's data-*
 * attributes (the standard, zero-extra-markup way third-party embed
 * widgets are configured), falling back to a `window.G360ChatbotConfig`
 * global object for teams that prefer setting it that way instead.
 *
 * Usage on the host page:
 *   <script src="https://cdn.example.com/chatbot.js"
 *           data-api-base-url="https://api.gadgets360.com"></script>
 */
function readConfig() {
  const script =
    document.currentScript || document.querySelector('script[src*="chatbot.js"]')
  const dataset = script ? script.dataset : {}
  const globalConfig = window.G360ChatbotConfig || {}

  return {
    apiBaseUrl: dataset.apiBaseUrl || globalConfig.apiBaseUrl || '',
  }
}

/** Loads the Google Fonts used by the design (Sora/Inter/JetBrains Mono) once, globally. */
function ensureFonts() {
  if (document.getElementById('g360-chatbot-fonts')) return
  const pre1 = document.createElement('link')
  pre1.rel = 'preconnect'
  pre1.href = 'https://fonts.googleapis.com'
  const pre2 = document.createElement('link')
  pre2.rel = 'preconnect'
  pre2.href = 'https://fonts.gstatic.com'
  pre2.crossOrigin = ''
  const fontLink = document.createElement('link')
  fontLink.id = 'g360-chatbot-fonts'
  fontLink.rel = 'stylesheet'
  fontLink.href =
    'https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap'
  document.head.append(pre1, pre2, fontLink)
  // Note: a <link> loaded in the main document registers @font-face
  // globally even though its CSS rules don't cross into the shadow
  // root, so `font-family: Sora, ...` still resolves correctly inside
  // the widget's shadow-scoped styles below.
}

function mount() {
  if (document.getElementById(CONTAINER_ID)) return // guard against double-injection if the script tag is present twice

  const config = readConfig()
  // Read by src/apiConfig.js's getApiBaseUrl() — set BEFORE React
  // renders so the very first request already uses it.
  window.__G360_CHATBOT_API_BASE_URL__ = config.apiBaseUrl

  ensureFonts()

  const host = document.createElement('div')
  host.id = CONTAINER_ID
  document.body.appendChild(host)

  // Shadow DOM = complete style isolation in BOTH directions: the
  // widget's Tailwind utility classes (.flex, .border, .text-sm, ...)
  // never leak onto/collide with the host site's own CSS, and the host
  // site's CSS never overrides the widget's look. This is the standard
  // approach used by embeddable third-party widgets for exactly this
  // reason.
  const shadow = host.attachShadow({ mode: 'open' })

  const styleEl = document.createElement('style')
  styleEl.textContent = stylesheet
  shadow.appendChild(styleEl)

  const mountPoint = document.createElement('div')
  shadow.appendChild(mountPoint)

  // Tailwind's `dark:` variants need a literal ancestor with
  // class="dark" INSIDE the same style-encapsulation boundary — the
  // shadow root does not automatically inherit host-page classes. This
  // mirrors <html class="dark"> (the common pattern most theme toggles
  // use) onto the shadow mount point. VERIFY against the real
  // useTheme.js: if it toggles document.documentElement's class, this
  // keeps dark mode working unchanged with zero component edits; if it
  // uses a different mechanism, flag it and this observer is a
  // harmless no-op.
  const syncDarkClass = () => {
    mountPoint.classList.toggle('dark', document.documentElement.classList.contains('dark'))
  }
  syncDarkClass()
  new MutationObserver(syncDarkClass).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })

  createRoot(mountPoint).render(<ChatWidget />)
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount)
} else {
  mount()
}
