# Security Practices

## General Rules

- Keep all secrets (tokens, DSNs, API keys) in environment variables or `.env` files.
- Never commit `.env` files (they are gitignored).
- Use least-privilege DB accounts.
- Use `socrata doctor --check-db` to verify configuration without exposing credentials.

---

## API Key Policy

### Socrata App Token

The Socrata app token is **read-only** and used only to increase Socrata rate limits.
It is stored in `localStorage` (browser) for the Mission Control SPA.

- **Risk**: Low — the token grants no write access and is locked to your account's
  registered domains. Rotate at `data.cityofnewyork.us/profile` if compromised.

### AI API Keys (Gemini / OpenAI)

AI keys grant **billing access** and must never be exposed to the browser.

**Architecture enforcement** (not convention):

1. The Mission Control v2 SPA has **no input fields** for AI keys — they cannot be
   pasted into the browser UI.
2. The SPA routes all AI chat via `POST /api/ai/chat` (the Flask API or standalone
   proxy at `app/llm_proxy.py`).
3. The proxy reads keys from environment variables only:

   ```bash
   export GEMINI_API_KEY="AIza..."   # Google AI Studio
   export OPENAI_API_KEY="sk-..."    # OpenAI platform
   ```

4. `GET /api/ai/status` returns `{"gemini": true/false, "openai": true/false}` —
   **never** the key value.

**If the proxy is offline**, the AI tab shows a yellow warning and the send button
is blocked — no fallback that would prompt users to enter keys in the browser.

---

## Credential Rotation

| Credential | Where configured | Rotate at |
|-----------|-----------------|-----------|
| `SOCRATA_APP_TOKEN` | env var / `.env` | data.cityofnewyork.us/profile → App Tokens |
| `GEMINI_API_KEY` | env var / `.env` | aistudio.google.com → API keys |
| `OPENAI_API_KEY` | env var / `.env` | platform.openai.com → API keys |
| `DATABASE_URL` | env var / `.env` | Your DB provider |

---

## Other Practices

- The Socrata Discovery API calls use `api.us.socrata.com` (CORS-safe) rather than
  per-domain endpoints to avoid CORS errors in the browser.
- All user-supplied strings rendered into HTML pass through `sanitize()` (HTML entity
  encoding) before insertion — no raw `innerHTML` with user data.
- Dataset metadata from the Socrata API is rendered via `sanitize()` or stored in a
  server-side `_resultMap` registry — JSON is never embedded in HTML `onchange` attributes.
