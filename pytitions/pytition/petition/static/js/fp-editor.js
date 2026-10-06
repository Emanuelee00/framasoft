/*
 * Petition editor behaviours: creation wizard and petition settings (CRE-04, CRE-05).
 * Vanilla, loaded with defer, no inline script.
 *
 *   get_csrf_token(), set_mce_changed(ed)   globals called by the TinyMCE configuration (settings)
 *   output[data-fp-slug-source=<input id>]  preview of the web address built from the title
 *   [data-fp-extend=<input id>]             extends a date field by data-fp-extend-months, never beyond
 *                                           the input max or data-fp-extend-limit-months from today
 *   form[data-fp-track=<name>]              marks [data-fp-unsaved=<name>] while the form has unsaved changes
 *                                           and asks before leaving the page
 *   [data-fp-reveal=<id>]                   checkbox showing or hiding the element <id>
 *   input[type=file][data-fp-image-preview=<img id>]   previews the chosen image
 *   tabs (fp-ui.js)                         the panel with form errors is shown first; links to an
 *                                           element of a hidden panel open that panel
 */
(function () {
  "use strict";

  function each(selector, fn) {
    Array.prototype.forEach.call(document.querySelectorAll(selector), fn);
  }

  // TinyMCE hooks (images_upload_handler and setup in TINYMCE_DEFAULT_CONFIG)
  window.get_csrf_token = function () {
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  };
  window.set_mce_changed = function (editor) {
    var form = editor && editor.formElement;
    if (form) { form.dispatchEvent(new Event("input", { bubbles: true })); }
  };

  // Web address preview, close to Django's slugify
  function slugify(text) {
    return text.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/[^\w\s-]/g, "").trim().replace(/[-\s]+/g, "-");
  }
  each("output[data-fp-slug-source]", function (output) {
    var input = document.getElementById(output.getAttribute("data-fp-slug-source"));
    var base = output.getAttribute("data-fp-slug-example").replace(/[^/]*\/?$/, "");
    if (!input) { return; }
    function update() { output.textContent = base + (slugify(input.value) || "…"); }
    input.addEventListener("input", update);
    update();
  });

  // Extend a deletion date
  function parseDate(value) {
    var iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
    if (iso) { return new Date(+iso[1], iso[2] - 1, +iso[3]); }
    var fr = /^(\d{1,2})[/.](\d{1,2})[/.](\d{4})/.exec(value);
    if (fr) { return new Date(+fr[3], fr[2] - 1, +fr[1]); }
    return null;
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function isoDate(date) { return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()); }
  function addMonths(date, months) {
    var result = new Date(date.getFullYear(), date.getMonth() + months, date.getDate());
    if (result.getDate() !== date.getDate()) { result.setDate(0); }   // 31 -> last day of the month
    return result;
  }

  each("[data-fp-extend]", function (button) {
    var input = document.getElementById(button.getAttribute("data-fp-extend"));
    var status = button.closest(".fp-expiry") && button.closest(".fp-expiry").querySelector(".fp-expiry-status");
    if (!input) { return; }
    button.hidden = false;
    button.addEventListener("click", function () {
      var today = new Date();
      today = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      var current = parseDate(input.value);
      var from = current && current > today ? current : today;
      var limit = parseDate(input.getAttribute("max") || "") ||
        addMonths(today, parseInt(button.getAttribute("data-fp-extend-limit-months"), 10));
      var next = addMonths(from, parseInt(button.getAttribute("data-fp-extend-months"), 10));
      if (next > limit) { next = limit; }
      if (current && next <= current) {
        if (status) { status.textContent = button.getAttribute("data-fp-extend-max"); }
        return;
      }
      var time = /T.*$/.exec(input.value);   // keep the time of a datetime-local input
      input.value = isoDate(next) + (time ? time[0] : "");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      if (status) {
        status.textContent = button.getAttribute("data-fp-extend-done").replace("{date}", next.toLocaleDateString(document.documentElement.lang || undefined));
      }
    });
  });

  // Unsaved changes
  var dirty = {};
  each("form[data-fp-track]", function (form) {
    var name = form.getAttribute("data-fp-track");
    function mark(value) {
      dirty[name] = value;
      each("[data-fp-unsaved='" + name + "']", function (flag) { flag.hidden = !value; });
    }
    form.addEventListener("input", function () { mark(true); });
    form.addEventListener("change", function () { mark(true); });
    form.addEventListener("submit", function () { dirty = {}; });
  });
  window.addEventListener("beforeunload", function (event) {
    if (Object.keys(dirty).some(function (key) { return dirty[key]; })) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  // Show the fields that depend on a checkbox
  each("[data-fp-reveal]", function (box) {
    var target = document.getElementById(box.getAttribute("data-fp-reveal"));
    if (!target) { return; }
    function update() { target.hidden = !box.checked; }
    box.addEventListener("change", update);
    update();
  });

  // Image preview
  each("input[type=file][data-fp-image-preview]", function (input) {
    var img = document.getElementById(input.getAttribute("data-fp-image-preview"));
    if (!img) { return; }
    input.addEventListener("change", function () {
      if (!input.files || !input.files[0]) { return; }
      var reader = new FileReader();
      reader.onload = function (event) {
        img.src = event.target.result;
        img.closest("[hidden]") && (img.closest("[hidden]").hidden = false);
      };
      reader.readAsDataURL(input.files[0]);
    });
  });
  // Tabs: show the panel that has errors, follow links into hidden panels
  function showPanelOf(element) {
    var panel = element && element.closest(".fp-tab-panel");
    if (!panel || !panel.hidden) { return; }
    var tab = document.querySelector(".fp-tab[href='#" + panel.id + "']");
    if (tab) { tab.click(); }
  }
  showPanelOf(document.querySelector(".fp-tab-panel .fp-error-summary"));
  document.addEventListener("click", function (event) {
    var link = event.target.closest("a[href^='#']:not(.fp-tab)");
    if (!link || link.getAttribute("href").length < 2) { return; }
    var target = document.getElementById(link.getAttribute("href").slice(1));
    if (!target || !target.closest(".fp-tab-panel")) { return; }
    event.preventDefault();
    showPanelOf(target);
    target.scrollIntoView({ block: "center" });
    var field = target.matches("input, select, textarea") ? target : target.querySelector("input, select, textarea");
    if (field) { field.focus({ preventScroll: true }); }
  });
})();
