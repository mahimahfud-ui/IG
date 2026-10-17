/* Small, dependency-free enhancements shared by the static MahiCloud pages. */
(() => {
  "use strict";
  const setYear = () => {
    const year = String(new Date().getFullYear());
    ["year", "yr"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = year;
    });
  };
  const optimizeImages = () => {
    document.querySelectorAll("img").forEach(img => {
      if (!img.hasAttribute("decoding")) img.decoding = "async";
      if (img.hasAttribute("loading")) return;
      if (img.closest("header, nav, .hero, .profile, .boot, .intro") || img.fetchPriority === "high") return;
      img.loading = "lazy";
    });
  };
  const initMobileMenu = () => {
    if (document.getElementById("mcMainNav") || document.getElementById("mcMobileDock")) return;
    if (document.querySelector(".menu-btn, #menuBtn, [data-existing-mobile-menu]")) return;
    const nav = document.querySelector("header nav.nav, header .nav, header nav");
    if (!nav || nav.id === "nav" || nav.querySelector("#search, .search")) return;
    const links = nav.querySelector(".nav-links, .navlinks");
    if (!links || links.querySelectorAll("a[href]").length < 2) return;
    if (nav.querySelector(".site-menu-toggle")) return;
    nav.classList.add("site-mobile-nav-host");
    links.classList.add("site-mobile-nav-links");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "site-menu-toggle";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", "site-mobile-links");
    button.innerHTML = '<span class="site-menu-icon" aria-hidden="true"></span><span>Menu</span>';
    links.id = links.id || "site-mobile-links";
    nav.insertBefore(button, links);
    const close = () => {
      nav.classList.remove("site-mobile-nav-open");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", "Open menu");
    };
    button.addEventListener("click", () => {
      const open = !nav.classList.contains("site-mobile-nav-open");
      nav.classList.toggle("site-mobile-nav-open", open);
      button.setAttribute("aria-expanded", String(open));
      button.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    links.addEventListener("click", event => {
      if (event.target.closest("a")) close();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") { close(); button.focus(); }
    });
    document.addEventListener("click", event => {
      if (!nav.contains(event.target)) close();
    });
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => { setYear(); optimizeImages(); initMobileMenu(); });
  } else {
    setYear();
    optimizeImages();
    initMobileMenu();
  }
})();