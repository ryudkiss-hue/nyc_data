// home.js: quick-start box. Routes an SR number to the Make Safe brief, a dataset ID or search term to Explore.
import { $, setStatus } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
  $('#go-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const t = $('#go-q').value.trim();
    if (!t) { setStatus($('#go-status'), 'Type a dataset ID, a search term or an SR number.', true); $('#go-q').focus(); return; }
    const sr = t.match(/\b311-\d{8}\b/);
    if (sr) location.href = `make-safe/?sr=${sr[0]}`;
    else if (/^[a-z0-9]{4}-[a-z0-9]{4}$/i.test(t)) location.href = `explore.html?ds=${t.toLowerCase()}`;
    else location.href = `explore.html?search=${encodeURIComponent(t)}`;
  });
});
