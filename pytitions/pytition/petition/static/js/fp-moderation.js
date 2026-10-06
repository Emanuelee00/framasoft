/*
 * Moderation queue (FE-09, CRE-06). Vanilla, loaded with defer, no inline script.
 *
 *   input[data-fp-filter=<table id>]           hides the rows whose text does not contain the query
 *   input[data-fp-select-visible=<name>]       ticks every visible input[name=<name>]
 *   button.fp-sort[data-sort-table][data-sort-col]   sorts the rows by that numeric column, highest first,
 *                                              and moves aria-sort to its header
 */
(function () {
  "use strict";

  function each(selector, fn, root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(selector), fn);
  }

  function rows(table) {
    return Array.prototype.slice.call(table.tBodies[0].rows).filter(function (row) {
      return row.querySelector("input[type=checkbox]");   // skip the "nothing here" row
    });
  }

  each("input[data-fp-filter]", function (input) {
    var table = document.getElementById(input.getAttribute("data-fp-filter"));
    if (!table) { return; }
    input.addEventListener("input", function () {
      var query = input.value.trim().toLowerCase();
      rows(table).forEach(function (row) {
        row.hidden = query !== "" && row.textContent.toLowerCase().indexOf(query) === -1;
      });
    });
  });

  each("input[data-fp-select-visible]", function (box) {
    var name = box.getAttribute("data-fp-select-visible");
    box.addEventListener("change", function () {
      each("input[name='" + name + "']", function (input) {
        if (!input.closest("tr").hidden) { input.checked = box.checked; }
      });
    });
  });

  each("button.fp-sort", function (button) {
    button.addEventListener("click", function () {
      var table = document.getElementById(button.getAttribute("data-sort-table"));
      var column = Number(button.getAttribute("data-sort-col"));
      var body = table.tBodies[0];
      rows(table).sort(function (a, b) {
        return (Number(b.cells[column].textContent.trim()) || 0) - (Number(a.cells[column].textContent.trim()) || 0);
      }).forEach(function (row) { body.appendChild(row); });
      each("th[aria-sort]", function (th) { th.removeAttribute("aria-sort"); }, table);
      button.closest("th").setAttribute("aria-sort", "descending");
    });
  });
})();
