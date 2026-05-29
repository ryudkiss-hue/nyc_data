/**
 * Pre-build step: copy the canonical SPA into the Electron renderer bundle so
 * the packaged app has a single, self-contained frontend file. Keeps one
 * source of truth (app/static/mission_control_v2.html) — no manual sync.
 *
 * When running inside Electron (ELECTRON_RUN_AS_NODE or packaged build) we
 * also rewrite CDN URLs to relative vendor/ paths so the app works offline.
 */

const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "..", "app", "static", "mission_control_v2.html");
const DEST_DIR = path.join(__dirname, "..", "renderer");
const DEST = path.join(DEST_DIR, "index.html");

// CDN → local vendor mapping.  Order matters: more specific URLs first.
const CDN_REWRITES = [
  // Tailwind (the CDN play/ endpoint returns a standalone JS bundle)
  ["https://cdn.tailwindcss.com", "../vendor/js/tailwind.js"],

  // Font Awesome
  [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    "../vendor/css/fa-all.min.css",
  ],

  // Leaflet CSS
  ["https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "../vendor/css/leaflet.css"],

  // MarkerCluster CSS
  [
    "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css",
    "../vendor/css/MarkerCluster.Default.css",
  ],
  [
    "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css",
    "../vendor/css/MarkerCluster.css",
  ],

  // Leaflet JS
  ["https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", "../vendor/js/leaflet.js"],

  // MarkerCluster JS
  [
    "https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js",
    "../vendor/js/leaflet.markercluster.js",
  ],

  // Mermaid
  ["https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js", "../vendor/js/mermaid.min.js"],

  // svg-pan-zoom
  [
    "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js",
    "../vendor/js/svg-pan-zoom.min.js",
  ],

  // html2canvas
  [
    "https://html2canvas.hertzen.com/dist/html2canvas.min.js",
    "../vendor/js/html2canvas.min.js",
  ],
];

function rewriteCdnUrls(html) {
  let out = html;
  for (const [cdn, local] of CDN_REWRITES) {
    // Replace every occurrence (href="...", src="...", url('...'))
    out = out.split(cdn).join(local);
  }
  return out;
}

function main() {
  if (!fs.existsSync(SRC)) {
    console.error(`[copy-spa] Source SPA not found: ${SRC}`);
    process.exit(1);
  }
  fs.mkdirSync(DEST_DIR, { recursive: true });

  const html = fs.readFileSync(SRC, "utf8");
  const patched = rewriteCdnUrls(html);
  fs.writeFileSync(DEST, patched, "utf8");

  const cdnCount = CDN_REWRITES.length;
  const kb = (Buffer.byteLength(patched, "utf8") / 1024).toFixed(1);
  console.log(
    `[copy-spa] Copied SPA → renderer/index.html (${kb} KB, ${cdnCount} CDN URLs → vendor/)`
  );
}

main();
