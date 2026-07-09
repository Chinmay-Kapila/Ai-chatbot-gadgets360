# Gadgets360 AI Assistant — Frontend

A floating, Gadgets360-inspired chat widget built with React 18, Vite, and
Tailwind CSS. It talks to the existing FastAPI backend's `POST /api/chat`
endpoint and renders every field the backend returns: `answer` (markdown),
`product_cards`, `article_cards`, `related_links`, and `metadata`.

## Tech Stack

- React 18 + Vite
- Tailwind CSS (dark mode via `class` strategy)
- Axios (API layer with retries, timeout, graceful error normalization)
- react-markdown + remark-gfm (markdown rendering)
- lucide-react (icons)

## Design

- **Palette**: signal red brand accent (`#E03A22`) inspired by Gadgets360's
  editorial identity, paired with a neutral charcoal/ink scale for dark and
  light surfaces, plus amber for ratings and green for the "online" status dot.
- **Type**: "Sora" for display/headings, "Inter" for body text, "JetBrains
  Mono" for prices, specs, and metadata — a tech-editorial feel.
- **Signature element**: the launcher button's pulsing signal ring,
  echoing a live broadcast/connectivity motif fitting a tech-news assistant.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

The app runs at `http://localhost:5173` by default. Ensure the backend is
running (see the backend's own README) and reachable at the URL configured
in `.env` (`VITE_API_BASE_URL`, default `http://localhost:8000/api`).

## Environment Variables

| Variable                | Description                                   | Default                        |
| ------------------------ | ---------------------------------------------- | ------------------------------- |
| `VITE_API_BASE_URL`      | Base URL of the backend API                    | `http://localhost:8000/api`     |
| `VITE_API_TIMEOUT`       | Request timeout in ms                          | `20000`                         |
| `VITE_API_MAX_RETRIES`   | Retries on network/timeout/5xx errors          | `2`                              |

## Project Structure

```
frontend/
  index.html
  package.json
  vite.config.js
  tailwind.config.js
  postcss.config.js
  .env.example
  .eslintrc.cjs
  .gitignore
  README.md
  src/
    main.jsx
    App.jsx
    index.css
    assets/
      logo.svg
    services/
      api.js          # axios instance, retries, timeout, error normalization
    hooks/
      useChat.js       # message state, session_id, send/retry logic
      useTheme.js       # dark/light mode (in-memory, follows system preference)
    components/
      ChatWidget.jsx     # floating launcher + panel toggle
      ChatWindow.jsx      # header, message list, suggestions, input, footer
      ChatMessage.jsx      # renders one message: markdown, cards, links, metadata
      InputBox.jsx
      CodeBlock.jsx
      Loading.jsx
      TypingIndicator.jsx
      ProductCard.jsx
      ArticleCard.jsx
      RelatedLinks.jsx
      SuggestedPrompts.jsx
      ThemeToggle.jsx
      Header.jsx
      Footer.jsx
      ErrorBanner.jsx
```

## Backend Contract

The widget sends:

```json
POST /api/chat
{ "session_id": "sess_... or null", "message": "user text" }
```

And renders every field of the response:

- `answer` — rendered as markdown (code blocks, links, lists, tables)
- `product_cards` — image, title, price, key specs, rating, link out
- `article_cards` — thumbnail, title, summary, link out
- `related_links` — clickable chips opening in a new tab
- `metadata` — shown as a small footnote (intent, entity, source APIs,
  whether Gemini reasoning was used, cache status)

Rejected (out-of-scope) responses and request errors are rendered inline
with distinct, non-alarming styling, and network/timeout failures surface
a retryable error banner.

## Session Handling

No login, no persistent storage. The `session_id` returned by the backend
is kept in a React ref for the lifetime of the page and sent on every
subsequent request; it resets on page reload.

## Build

```bash
npm run build
npm run preview
```
