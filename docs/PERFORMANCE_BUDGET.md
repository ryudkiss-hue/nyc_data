# Performance Budget — Manhattan Mission Control SPA

Targets follow Google Web Vitals "good" thresholds and are enforced
qualitatively via the lightweight runtime timing in Enhancement Module C
(`window.mmcPerfReport()` in the browser console).

| Metric | Target ("good") | Notes |
|--------|-----------------|-------|
| LCP (Largest Contentful Paint) | ≤ 2.5 s | First meaningful panel painted |
| INP (Interaction to Next Paint) | ≤ 200 ms | Long-task observer flags >200 ms tasks |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | Skeletons reserve space to avoid shift |
| TTFB | ≤ 800 ms | Static SPA — dominated by CDN/file load |
| Main-thread sort | offloaded ≥ 2000 rows | `mmcSortAsync` → inline Web Worker |
| Table render | windowed | `mmcVirtualTable` renders only visible rows |
| Network | cached | `mmcCachedFetch` LRU (sessionStorage, TTL 10 min) |

## Mechanisms

- **Caching** — `mmcCachedFetch(url, ttl)` serves repeat dataset fetches from a
  sessionStorage LRU (cap 24 entries, quota-safe eviction). Inspect with
  `mmcCacheStats()`, clear with `mmcCacheClear()`.
- **Virtualized tables** — `mmcVirtualTable(container, columns, rows)` renders
  only the visible row window + a small buffer; memory and paint cost are
  independent of row count.
- **Web Worker** — `mmcSortAsync(rows, key, dir)` sorts large arrays off the
  main thread; falls back to a main-thread sort under 2000 rows or when workers
  are unavailable.
- **Lazy init** — `mmcLazy(tabName, initFn)` defers heavy panel setup (map,
  Mermaid) until the tab is first shown.
- **Resilient fetch** — `mmcFetch` retries with exponential backoff and honors
  `Retry-After` on HTTP 429 (rate-limit aware).

## Measuring

Open DevTools console in the SPA (or Electron app) and run:

```js
mmcPerfReport();   // { ttfb, domContentLoaded, load, lcp, marks: [...] }
mmcCacheStats();   // { entries, approx_kb }
```

`mmcPerf(label, detail)` records custom marks; the long-task observer
auto-records any task exceeding 200 ms as an INP risk signal.
