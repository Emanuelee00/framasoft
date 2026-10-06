/*
 * Framapétitions UI behaviours (DS-03). Vanilla, no dependency, loaded with defer.
 * Every behaviour is an enhancement: the markup works without it.
 *
 *   [data-fp-menu-toggle]     header menu button (aria-expanded + .is-open on its aria-controls)
 *   details.fp-menu           closes on Escape (focus back to its summary) and on outside click
 *   [data-fp-dialog-open=id]  opens <dialog id> with showModal(); focus returns to the opener
 *   [data-fp-dialog-close]    closes the enclosing <dialog>
 *   [data-fp-tabs]            turns a list of #anchors + panels into ARIA tabs (arrow keys, Home, End)
 */
(function () {
  "use strict";

  function each(selector, fn, root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(selector), fn);
  }

  // Header menu on small screens
  each("[data-fp-menu-toggle]", function (button) {
    var menu = document.getElementById(button.getAttribute("aria-controls"));
    if (!menu) { return; }
    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      menu.classList.toggle("is-open", open);
    });
  });

  // Disclosure menus
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") { return; }
    each("details.fp-menu[open]", function (menu) {
      menu.open = false;
      menu.querySelector("summary").focus();
    });
  });
  document.addEventListener("click", function (event) {
    each("details.fp-menu[open]", function (menu) {
      if (!menu.contains(event.target)) { menu.open = false; }
    });
  });

  // Dialogs
  if (typeof HTMLDialogElement === "function") {
    each("[data-fp-dialog-open]", function (opener) {
      var dialog = document.getElementById(opener.getAttribute("data-fp-dialog-open"));
      if (!dialog || typeof dialog.showModal !== "function") { return; }
      opener.addEventListener("click", function (event) {
        event.preventDefault();
        dialog.showModal();
        dialog.addEventListener("close", function () { opener.focus(); }, { once: true });
      });
    });
    each("[data-fp-dialog-close]", function (button) {
      button.addEventListener("click", function () {
        var dialog = button.closest("dialog");
        if (dialog) { dialog.close(); }
      });
    });
  }

  // Tabs
  each("[data-fp-tabs]", function (root, index) {
    var list = root.querySelector(".fp-tabs");
    var tabs = Array.prototype.slice.call(list.querySelectorAll(".fp-tab[href^='#']"));
    var panels = tabs.map(function (tab) { return document.getElementById(tab.getAttribute("href").slice(1)); });
    if (!tabs.length || panels.indexOf(null) !== -1) { return; }

    list.setAttribute("role", "tablist");
    tabs.forEach(function (tab, i) {
      tab.parentNode.setAttribute("role", "presentation");
      tab.setAttribute("role", "tab");
      tab.id = tab.id || "fp-tab-" + index + "-" + i;
      tab.setAttribute("aria-controls", panels[i].id);
      panels[i].setAttribute("role", "tabpanel");
      panels[i].setAttribute("aria-labelledby", tab.id);
      panels[i].setAttribute("tabindex", "0");
    });

    function select(i, focus) {
      tabs.forEach(function (tab, j) {
        tab.setAttribute("aria-selected", String(i === j));
        tab.setAttribute("tabindex", i === j ? "0" : "-1");
        panels[j].hidden = i !== j;
      });
      if (focus) { tabs[i].focus(); }
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function (event) {
        event.preventDefault();
        select(i, false);
        if (history.replaceState) { history.replaceState(null, "", tab.getAttribute("href")); }
      });
      tab.addEventListener("keydown", function (event) {
        var last = tabs.length - 1;
        var next = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[event.key];
        if (next === undefined) { return; }
        event.preventDefault();
        select(next, true);
      });
    });

    var initial = tabs.findIndex(function (tab) { return tab.getAttribute("href") === location.hash; });
    select(initial === -1 ? 0 : initial, false);
  });
})();
