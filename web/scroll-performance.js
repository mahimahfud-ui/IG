/* MahiCloud scroll performance helper.
 * Temporarily removes expensive visual compositing while native scrolling is active,
 * then restores the complete visual treatment shortly after the gesture settles.
 */
(function () {
  "use strict";
  var root = document.documentElement;
  if (window.__mcScrollPerformanceInstalled) return;
  window.__mcScrollPerformanceInstalled = true;

  var settleTimer = 0;
  var style = document.createElement("style");
  style.id = "mc-scroll-performance";
  style.textContent = [
    "html.mc-scroll-active .chrome,",
    "html.mc-scroll-active .nav,",
    "html.mc-scroll-active header,",
    "html.mc-scroll-active .mc-mobile-dock,",
    "html.mc-scroll-active .skip,",
    "html.mc-scroll-active .social,",
    "html.mc-scroll-active .controls .seg,",
    "html.mc-scroll-active .mode-switch,",
    "html.mc-scroll-active .switch,",
    "html.mc-scroll-active .badge,",
    "html.mc-scroll-active .ad,",
    "html.mc-scroll-active .more,",
    "html.mc-scroll-active .status,",
    "html.mc-scroll-active .modal-bg,",
    "html.mc-scroll-active .viewer,",
    "html.mc-scroll-active #mf-add-overlay {",
    "  -webkit-backdrop-filter: none !important;",
    "  backdrop-filter: none !important;",
    "}",
    "html.mc-scroll-active .stage::before,",
    "html.mc-scroll-active .ambient::before,",
    "html.mc-scroll-active .glow-ball,",
    "html.mc-scroll-active .equalizer i,",
    "html.mc-scroll-active .movie-beam,",
    "html.mc-scroll-active .film-poster::after,",
    "html.mc-scroll-active .music-visualizer i,",
    "html.mc-scroll-active #backdrop::after { animation-play-state: paused !important; }",
    "html.mc-scroll-active .stage::before { mix-blend-mode: normal !important; opacity: .12 !important; }",
    "html.mc-scroll-active .grain { mix-blend-mode: normal !important; opacity: .025 !important; }",
    "html.mc-scroll-active .card,",
    "html.mc-scroll-active .app-card,",
    "html.mc-scroll-active .script-card,",
    "html.mc-scroll-active .nav-links a,",
    "html.mc-scroll-active .card .icon { transition: none !important; box-shadow: none !important; }",
    "html.mc-scroll-active .media img,",
    "html.mc-scroll-active .media video,",
    "html.mc-scroll-active .card .icon,",
    "html.mc-scroll-active .app-icon,",
    "html.mc-scroll-active .site-brand-logo { filter: none !important; }",
  ].join("\n");
  (document.head || root).appendChild(style);

  function finishScroll() {
    settleTimer = 0;
    root.classList.remove("mc-scroll-active");
    document.dispatchEvent(new Event("mahicloud:scroll-end"));
  }

  function onScroll() {
    if (!root.classList.contains("mc-scroll-active")) {
      root.classList.add("mc-scroll-active");
      document.dispatchEvent(new Event("mahicloud:scroll-start"));
    }
    if (settleTimer) clearTimeout(settleTimer);
    settleTimer = setTimeout(finishScroll, 150);
  }

  // Capture also sees scrolling inside embedded rails and nested panels.
  document.addEventListener("scroll", onScroll, { passive: true, capture: true });
  window.addEventListener("scroll", onScroll, { passive: true });

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden || !root.classList.contains("mc-scroll-active")) return;
    if (settleTimer) clearTimeout(settleTimer);
    finishScroll();
  });
})();