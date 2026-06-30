/**
 * WCAG 2.1 AA runtime patches
 *
 * 1. Color-token overrides — Mantine v7 MantineProvider injects a <style> tag at
 *    runtime with CSS custom properties (e.g. --mantine-color-blue-6 = #228be6,
 *    3.55:1 on white, fails AA).  Inline styles on document.documentElement set
 *    via element.style.setProperty() beat any injected <style> tag and cannot be
 *    overridden by it.  We use this mechanism to pin every color token to its
 *    WCAG-AA-safe equivalent.
 *
 * 2. ARIA labels — unlabeled progressbars (Mantine Progress) and file inputs
 *    (dcc.Upload) are patched on load and re-patched via MutationObserver so
 *    dynamically-rendered components are also covered.
 *
 * Contrast ratios (AA requires ≥4.5:1 for normal text on white / near-white):
 *   blue-6:   #228be6 → 3.55:1 FAIL  → #1864ab → 5.65:1 PASS
 *   green-6:  #40c057 → 2.36:1 FAIL  → #1e7b35 → 5.02:1 PASS
 *   red-6:    #fa5252 → 3.28:1 FAIL  → #c92a2a → 6.10:1 PASS
 *   orange-6: #fd7e14 → 2.57:1 FAIL  → #b85500 → 4.84:1 PASS (text on white)
 *   gray-6:   #868e96 → 3.32:1 FAIL  → #545B62 → 6.90:1 PASS
 *   cyan-6:   #15aabf → 2.78:1 FAIL  → #0b7285 → 5.15:1 PASS
 */
(function () {
  'use strict';

  var COLOR_TOKENS = {
    '--mantine-color-blue-6':        '#1864ab',
    '--mantine-color-blue-filled':   '#1864ab',
    '--mantine-color-green-6':       '#1e7b35',
    '--mantine-color-green-filled':  '#1e7b35',
    '--mantine-color-red-6':         '#c92a2a',
    '--mantine-color-red-filled':    '#c92a2a',
    '--mantine-color-orange-6':      '#b85500',
    '--mantine-color-orange-filled': '#b85500',
    '--mantine-color-gray-6':        '#545B62',
    '--mantine-color-gray-filled':   '#545B62',
    '--mantine-color-cyan-6':        '#0b7285',
    '--mantine-color-cyan-filled':   '#0b7285',
    '--mantine-color-dimmed':        '#545B62',
  };

  function applyColorTokens() {
    var root = document.documentElement;
    for (var token in COLOR_TOKENS) {
      root.style.setProperty(token, COLOR_TOKENS[token]);
    }
  }

  function patchAria() {
    document.querySelectorAll('[role="progressbar"]:not([aria-label])').forEach(function (el) {
      el.setAttribute('aria-label', 'Processing progress');
    });
    document.querySelectorAll('input[type="file"]:not([aria-label])').forEach(function (el) {
      el.setAttribute('aria-label', 'Upload file');
    });
  }

  function init() {
    applyColorTokens();
    patchAria();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* Re-run on every DOM mutation so Mantine re-renders cannot undo the overrides */
  var observer = new MutationObserver(function () {
    applyColorTokens();
    patchAria();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
