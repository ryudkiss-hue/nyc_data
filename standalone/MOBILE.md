# Run Manhattan Mission Control on a mobile device

The standalone app is a mobile-friendly PWA served from this directory.

## Start the local server

```bash
cd /workspace/standalone
python3 -m http.server 8765 --bind 0.0.0.0
```

The app is available at:

```text
http://localhost:8765/mission-control.html
```

## Open it on your phone

1. In Cursor/Cloud, open or forward port `8765`.
2. Copy the forwarded `https://...` URL.
3. Open that URL in Safari or Chrome on your mobile device.
4. Optional install:
   - iPhone/iPad: tap Share, then **Add to Home Screen**.
   - Android/Chrome: tap the browser menu, then **Install app**.

The app shell can be cached by the service worker after the first load. Live Socrata searches, map tiles, and optional Gemini assistant calls still require network access.
