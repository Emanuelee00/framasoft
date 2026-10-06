/*
 * Framapétitions micro-interactions on scroll (MI-01). Vanilla, loaded with defer; once per
 * element, nothing with reduced motion or without IntersectionObserver.
 *   .fp-icon-badge -> .is-inview; [data-fp-countup] counts up; progress.fp-progress-bar fills.
 */
(function () {
  "use strict";

  if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { return; }

  var DURATION = 700;

  function tween(draw) {
    var start = null;
    function frame(now) {
      if (start === null) { start = now; }
      var t = Math.min((now - start) / DURATION, 1);
      draw(1 - Math.pow(1 - t, 3), t === 1);
      if (t < 1) { requestAnimationFrame(frame); }
    }
    requestAnimationFrame(frame);
  }

  function countUp(el) {
    var text = el.textContent;
    var target = parseInt(text.replace(/\D/g, ""), 10);
    if (!(target > 1)) { return; }
    // Same thousands separator as the page; screen readers get the final value only
    var sep = (text.match(/\d(\D+)\d/) || [])[1] || "";
    var label = document.createElement("span");
    label.className = "fp-sr-only";
    label.textContent = text;
    el.parentNode.insertBefore(label, el.nextSibling);
    el.setAttribute("aria-hidden", "true");
    // Fixed width while counting: digits of the display font differ in width, the text after must not move
    el.style.width = el.getBoundingClientRect().width + "px";
    tween(function (k, done) {
      el.textContent = done ? text : String(Math.round(target * k)).replace(/\B(?=(\d{3})+(?!\d))/g, sep);
      if (done) { el.style.width = ""; }
    });
  }

  function fill(bar) {
    var value = bar.value;
    if (!(value > 0)) { return; }
    bar.value = 0;
    tween(function (k) { bar.value = value * k; });
  }

  var stagger = 0;
  function start(el) {
    if (el.classList.contains("fp-icon-badge")) {
      el.style.animationDelay = stagger + "ms";
      stagger += 80;
      el.classList.add("is-inview");
    } else if (el.tagName === "PROGRESS") {
      fill(el);
    } else {
      countUp(el);
    }
  }

  var observer = new IntersectionObserver(function (entries) {
    stagger = 0;
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) { return; }
      observer.unobserve(entry.target);
      start(entry.target);
    });
  }, { rootMargin: "0px 0px -10% 0px" });

  // What is already on screen starts now, before the first paint shows the final values
  Array.prototype.forEach.call(
    document.querySelectorAll(".fp-icon-badge, [data-fp-countup], progress.fp-progress-bar"),
    function (el) {
      var box = el.getBoundingClientRect();
      if (box.height && box.top < window.innerHeight && box.bottom > 0) { start(el); } else { observer.observe(el); }
    }
  );
})();
