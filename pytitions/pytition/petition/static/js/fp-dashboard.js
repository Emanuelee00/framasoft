/*
 * Creator area behaviours (CRE-*). Vanilla, loaded with defer, no inline script.
 *
 *   form[data-fp-async]        POST through fetch (CSRF token from the form), then reload or go to
 *                              data-fp-redirect; on error shows data-fp-error (or the generic message
 *                              of #fp-dash-messages[data-fp-error]) as an alert.
 *   form[data-fp-invite]       search accounts (data-fp-search-url) and invite one (data-fp-add-url)
 *   form[data-fp-transfer]     search users and organizations (data-fp-search-url), then confirm
 *                              in <dialog id="transfer-confirm"> and submit form#transfer-form
 *   [data-fp-select-all]       checkbox selecting every input[name=<value>] of its form
 *   [data-fp-sympa-url]        fills its element with the newsletter block when its dialog opens
 */
(function () {
  "use strict";

  function each(selector, fn, root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(selector), fn);
  }

  function csrf(form) {
    var input = form.querySelector("[name=csrfmiddlewaretoken]") || document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function post(url, form) {
    return fetch(url, {
      method: "POST",
      body: form ? new FormData(form) : null,
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(form || document), "X-Requested-With": "XMLHttpRequest" }
    });
  }

  function showError(text) {
    var box = document.getElementById("fp-dash-messages");
    if (!box) { return; }
    var alert = document.createElement("div");
    alert.className = "fp-alert fp-alert-danger";
    alert.setAttribute("role", "alert");
    var p = document.createElement("p");
    p.textContent = text || box.getAttribute("data-fp-error") || "Error";
    alert.appendChild(p);
    box.textContent = "";
    box.appendChild(alert);
    box.scrollIntoView({ block: "nearest" });
  }

  function debounce(fn, delay) {
    var timer;
    return function () {
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(null, args); }, delay);
    };
  }

  // Asynchronous actions (publish, bin, delete, templates, members)
  each("form[data-fp-async]", function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var button = form.querySelector("[type=submit]");
      if (button) { button.disabled = true; }
      post(form.action, form).then(function (response) {
        if (!response.ok) { throw new Error(String(response.status)); }
        var target = form.getAttribute("data-fp-redirect");
        if (target) { window.location.assign(target); } else { window.location.reload(); }
      }).catch(function () {
        if (button) { button.disabled = false; }
        var dialog = form.closest("dialog");
        if (dialog && dialog.open) { dialog.close(); }
        var menu = form.closest("details");
        if (menu) { menu.open = false; }
        showError(form.getAttribute("data-fp-error"));
      });
    });
  });

  // Result list made of buttons
  function renderResults(list, items, onPick) {
    list.textContent = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "fp-dash-list-item";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "fp-btn fp-btn-tertiary fp-result-btn";
      button.textContent = item.label;
      button.addEventListener("click", function () { onPick(item); });
      li.appendChild(button);
      list.appendChild(li);
    });
  }

  // Invite a member into an organization
  each("form[data-fp-invite]", function (form) {
    var input = form.querySelector("input[type=search]");
    var list = form.querySelector("ul");
    var status = form.querySelector("[role=status]");
    form.addEventListener("submit", function (event) { event.preventDefault(); });
    input.addEventListener("input", debounce(function () {
      var q = input.value.trim();
      if (q.length < 2) { list.textContent = ""; status.textContent = ""; return; }
      status.textContent = form.getAttribute("data-fp-searching");
      fetch(form.getAttribute("data-fp-search-url") + "?q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          var label = form.getAttribute("data-fp-invite-label");
          status.textContent = data.values.length ? "" : form.getAttribute("data-fp-none");
          renderResults(list, data.values.map(function (name) { return { name: name, label: label + " " + name }; }), function (item) {
            post(form.getAttribute("data-fp-add-url") + "?user=" + encodeURIComponent(item.name), form)
              .then(function (response) { return response.json(); })
              .then(function (result) {
                list.textContent = "";
                input.value = "";
                status.textContent = result.message;
              })
              .catch(function () { showError(); });
          });
        })
        .catch(function () { status.textContent = ""; });
    }, 250));
  });

  // Transfer a petition
  each("form[data-fp-transfer]", function (form) {
    var input = form.querySelector("input[type=search]");
    var list = form.querySelector("ul");
    var status = form.querySelector("[role=status]");
    var dialog = document.getElementById("transfer-confirm");
    var target = document.getElementById("transfer-target");
    var request = document.getElementById("transfer-form");
    form.addEventListener("submit", function (event) { event.preventDefault(); });
    input.addEventListener("input", debounce(function () {
      var q = input.value.trim();
      if (q.length < 2) { list.textContent = ""; status.textContent = ""; return; }
      fetch(form.getAttribute("data-fp-search-url") + "?q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          var orgLabel = form.getAttribute("data-fp-org-label");
          var items = data.orgs.map(function (org) {
            return { type: "org", name: org.slugname, label: org.name + " (" + orgLabel + ")" };
          }).concat(data.users.map(function (user) {
            var full = (user.firstname + " " + user.lastname).trim();
            return { type: "user", name: user.username, label: full ? full + " (" + user.username + ")" : user.username };
          }));
          status.textContent = items.length ? "" : form.getAttribute("data-fp-none");
          renderResults(list, items, function (item) {
            request.querySelector("[name=new_owner_type]").value = item.type;
            request.querySelector("[name=new_owner_name]").value = item.name;
            target.textContent = item.label;
            if (dialog && typeof dialog.showModal === "function") {
              var opener = document.activeElement;
              dialog.showModal();
              dialog.addEventListener("close", function () { if (opener) { opener.focus(); } }, { once: true });
            } else {
              request.submit();
            }
          });
        })
        .catch(function () { status.textContent = ""; });
    }, 250));
  });

  // Select every row of a table
  each("[data-fp-select-all]", function (box) {
    var name = box.getAttribute("data-fp-select-all");
    box.addEventListener("change", function () {
      each("input[name='" + name + "']", function (input) { input.checked = box.checked; }, box.form || document);
    });
  });

  // Newsletter block, loaded when its dialog is opened
  each("[data-fp-sympa-url]", function (target) {
    var dialog = target.closest("dialog");
    var opener = dialog && document.querySelector("[data-fp-dialog-open='" + dialog.id + "']");
    if (!opener) { return; }
    opener.addEventListener("click", function () {
      fetch(target.getAttribute("data-fp-sympa-url"), { credentials: "same-origin" })
        .then(function (response) { return response.text(); })
        .then(function (html) {
          // Server-sanitised lines "email first last<br>": keep them as text
          var doc = new DOMParser().parseFromString(html.replace(/<br\s*\/?>/gi, ""), "text/html");
          target.textContent = doc.body.textContent.trim();
        });
    });
  });
})();
