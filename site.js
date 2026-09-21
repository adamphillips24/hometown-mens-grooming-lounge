/* Progressive enhancements only: every service and booking link works without JS. */
(() => {
  'use strict';
  document.documentElement.classList.add('js-ready');
  const dock = document.querySelector('.dock');
  const directBooking = [...document.querySelectorAll('[data-booking-zone]')];
  const visibleZones = new Set();
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const setDock = () => {
    if (!dock) return;
    const focusedInDock = dock.contains(document.activeElement);
    const show = !visibleZones.size && window.scrollY > 180;
    // Keep the control a keyboard user is interacting with in place.
    if (focusedInDock && !show) return;
    dock.dataset.visible = String(show);
    dock.inert = !show;
    dock.setAttribute('aria-hidden', String(!show));
  };
  if (dock && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) visibleZones.add(entry.target);
        else visibleZones.delete(entry.target);
      }
      setDock();
    }, {threshold:0, rootMargin:'0px 0px -100px 0px'});
    directBooking.forEach(zone => observer.observe(zone));
    dock.addEventListener('focusout', () => requestAnimationFrame(setDock));
    // A focused main-page link must never be hidden behind the booking bar.
    document.addEventListener('focusin', event => {
      if (dock.contains(event.target) || dock.dataset.visible !== 'true') return;
      const r = event.target.getBoundingClientRect();
      const top = dock.getBoundingClientRect().top;
      if (r.bottom > top && r.top < window.innerHeight) {
        event.target.scrollIntoView({block:'center', behavior:reduced.matches?'instant':'smooth'});
      }
    });
  }
  // Highlight the section without intercepting standard anchor navigation.
  if ('IntersectionObserver' in window) {
    const sectionObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        document.querySelectorAll('.nav a').forEach(link => {
          if (link.hash === '#' + entry.target.id) link.setAttribute('aria-current','location');
          else link.removeAttribute('aria-current');
        });
      }
    }, {rootMargin:'-10% 0px -60% 0px'});
    document.querySelectorAll('main section[id]').forEach(section => sectionObserver.observe(section));
  }
  // Local event hook for a future analytics adapter. No trackers, cookies, or network calls.
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-action]');
    if (!link) return;
    document.dispatchEvent(new CustomEvent('hometown:action', {detail:{
      action:link.dataset.action, location:link.dataset.location || document.body.dataset.location,
      barber:link.dataset.barber || null, placement:link.dataset.placement || null
    }}));
  });
})();
