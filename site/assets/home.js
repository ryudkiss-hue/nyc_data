// home.js: quick-start box. Routes an SR number to the Make Safe brief, a dataset ID or search term to Explore.
// URLs are built from fixed paths with URLSearchParams, so typed text can only ever be an encoded query value.
import { $, setStatus } from './ui.js';

function go(path, params) {
  const url = new URL(path, location.href);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  location.assign(url.href);
}

document.addEventListener('DOMContentLoaded', () => {
  $('#go-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const t = $('#go-q').value.trim();
    if (!t) { setStatus($('#go-status'), 'Type a dataset ID, a search term or an SR number.', true); $('#go-q').focus(); return; }
    const sr = t.match(/\b311-\d{8}\b/);
    if (sr) go('make-safe/', { sr: sr[0] });
    else if (/^[a-z0-9]{4}-[a-z0-9]{4}$/i.test(t)) go('explore.html', { ds: t.toLowerCase() });
    else go('explore.html', { search: t });
  });
});
