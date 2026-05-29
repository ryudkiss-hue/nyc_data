/**
 * Pre-build step: copy the canonical SPA into the Electron renderer bundle so
 * the packaged app has a single, self-contained frontend file. Keeps one
 * source of truth (app/static/mission_control_v2.html) — no manual sync.
 */

const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "..", "app", "static", "mission_control_v2.html");
const DEST_DIR = path.join(__dirname, "..", "renderer");
const DEST = path.join(DEST_DIR, "index.html");

function main() {
  if (!fs.existsSync(SRC)) {
    console.error(`[copy-spa] Source SPA not found: ${SRC}`);
    process.exit(1);
  }
  fs.mkdirSync(DEST_DIR, { recursive: true });
  fs.copyFileSync(SRC, DEST);
  const kb = (fs.statSync(DEST).size / 1024).toFixed(1);
  console.log(`[copy-spa] Copied SPA → renderer/index.html (${kb} KB)`);
}

main();
