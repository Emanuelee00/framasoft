/*
 * Mastodon share (PUB-03): asks for the visitor's server in a native <dialog>, then opens
 * https://<server>/share. The list item stays hidden without JavaScript; no inline script (CSP).
 */
(function () {
  "use strict";
  var dialog = document.getElementById("MastodonModal");
  if (!dialog || typeof dialog.showModal !== "function") { return; }
  var form = dialog.querySelector("[data-mastodon-form]");
  var input = document.getElementById("msb-address");
  var error = document.getElementById("msb-address-error");
  var text = "";

  function setError(on) {
    error.hidden = !on;
    if (on) {
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", "msb-address-help msb-address-error");
    } else {
      input.removeAttribute("aria-invalid");
      input.setAttribute("aria-describedby", "msb-address-help");
    }
  }

  Array.prototype.forEach.call(document.querySelectorAll(".mastodon-share-button"), function (link) {
    var item = link.closest("li");
    if (item) { item.hidden = false; }
    link.addEventListener("click", function (event) {
      event.preventDefault();
      text = link.getAttribute("data-target") || "";
      setError(false);
      dialog.showModal();
      input.focus();
      dialog.addEventListener("close", function () { link.focus(); }, { once: true });
    });
  });

  form.addEventListener("submit", function (event) {
    var address = input.value.trim();
    if (!/^https?:\/\//i.test(address)) { address = "https://" + address; }
    var url = null;
    try { url = new URL(address); } catch (e) { url = null; }
    if (!url || url.hostname.indexOf(".") === -1) {
      event.preventDefault();
      setError(true);
      input.focus();
      return;
    }
    // method="dialog" closes the dialog after this handler
    window.open(url.origin + "/share?text=" + text, "_blank", "noopener");
  });
})();
