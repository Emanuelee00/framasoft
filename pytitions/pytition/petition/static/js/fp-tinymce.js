/* TinyMCE callbacks, referenced by name in TINYMCE_DEFAULT_CONFIG (S13: no eval, no inline script).
 * Loaded through TINYMCE_EXTRA_MEDIA, before django_tinymce/init_tinymce.js. */
(function () {
  "use strict";

  function csrfToken(editor) {
    var scope = (editor && editor.formElement) || document;
    var input = scope.querySelector("[name=csrfmiddlewaretoken]") ||
      document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  // Image upload (TinyMCE 5 signature): POST to images_upload_url with the CSRF token
  window.fpTinymceUploadImage = function (blobInfo, success, failure) {
    var editor = window.tinymce && window.tinymce.activeEditor;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", editor.getParam("images_upload_url"));
    xhr.setRequestHeader("X-CSRFToken", csrfToken(editor));
    xhr.onload = function () {
      if (xhr.status !== 200) {
        failure("HTTP Error: " + xhr.status);
        return;
      }
      var json;
      try {
        json = JSON.parse(xhr.responseText);
      } catch (e) {
        json = null;
      }
      if (!json || typeof json.location !== "string") {
        failure("Invalid JSON: " + xhr.responseText);
        return;
      }
      success(json.location);
    };
    var formData = new FormData();
    formData.append("file", blobInfo.blob(), blobInfo.filename());
    xhr.send(formData);
  };

  // Remember that the editor content changed (used by the "unsaved changes" warning)
  window.fpTinymceSetup = function (editor) {
    editor.on("change", function () {
      if (editor.formElement && window.jQuery) {
        window.jQuery(editor.formElement).data("mce_changed", true);
      }
    });
  };
})();
