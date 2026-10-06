/* Progressive enhancement for the signer pages. Everything works without it. */
(function () {
  "use strict";
  var summary = document.querySelector("[data-autofocus]");
  if (summary) {
    summary.focus();
  }
  // Share (FE-06): copy the link and the native share sheet, only when the browser supports them.
  var copyButton = document.querySelector("[data-share-copy]");
  if (copyButton && navigator.clipboard) {
    var status = document.querySelector(".fp-share-status");
    copyButton.parentNode.hidden = false;
    copyButton.addEventListener("click", function () {
      navigator.clipboard.writeText(copyButton.getAttribute("data-share-copy")).then(function () {
        if (status) { status.textContent = copyButton.getAttribute("data-share-copied"); }
      });
    });
    var nativeButton = document.querySelector("[data-share-native]");
    if (nativeButton && navigator.share) {
      nativeButton.hidden = false;
      nativeButton.addEventListener("click", function () {
        navigator.share({
          title: nativeButton.getAttribute("data-share-text"),
          url: nativeButton.getAttribute("data-share-native")
        }).catch(function () {});
      });
    }
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
