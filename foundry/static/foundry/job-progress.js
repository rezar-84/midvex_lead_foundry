(function () {
  "use strict";
  var root = document.querySelector("[data-job-status-url]");
  if (!root || root.dataset.jobTerminal === "true") return;
  var url = root.dataset.jobStatusUrl;
  var fields = {};
  document.querySelectorAll("[data-job-field]").forEach(function (el) {
    fields[el.dataset.jobField] = el;
  });
  var bar = document.querySelector("progress[data-job-progress]");

  function apply(data) {
    if (bar) {
      bar.value = data.processed;
      bar.max = data.total || 1;
    }
    if (fields.status) fields.status.textContent = data.status_display;
    if (fields.processed) fields.processed.textContent = data.processed + " / " + data.total;
    if (fields.errors) fields.errors.textContent = data.error_count;
    if (fields.requests) {
      fields.requests.textContent =
        data.requests_used + (data.request_budget ? " / " + data.request_budget : "");
    }
  }

  function tick() {
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("status " + response.status);
        return response.json();
      })
      .then(function (data) {
        apply(data);
        if (data.terminal) {
          window.location.reload();
        } else {
          window.setTimeout(tick, 2500);
        }
      })
      .catch(function () {
        window.setTimeout(tick, 10000);
      });
  }

  window.setTimeout(tick, 2500);
})();
