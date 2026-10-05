/* Progressive enhancement for the signer pages. Everything works without it. */
(function () {
  "use strict";
  var summary = document.querySelector("[data-autofocus]");
  if (summary) {
    summary.focus();
  }
  if (typeof HTMLDialogElement !== "function") {
    return;
  }
  document.querySelectorAll("[data-report-open]").forEach(function (link) {
    var dialog = document.getElementById(link.getAttribute("data-report-open"));
    if (!dialog || typeof dialog.showModal !== "function") {
      return;
    }
    link.addEventListener("click", function (event) {
      event.preventDefault();
      dialog.showModal();
    });
    dialog.addEventListener("close", function () {
      link.focus();
    });
  });
})();
