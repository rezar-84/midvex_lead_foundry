(() => {
  const form = document.querySelector("[data-source-form]");
  if (!form) return;
  const type = form.querySelector("[data-source-type]");
  const protocol = form.querySelector("[data-protocol-settings]");
  const update = () => {
    const visible = type.value === "imap" || type.value === "pop3";
    protocol.hidden = !visible;
    protocol.querySelectorAll("input").forEach((input) => { input.disabled = !visible; });
  };
  type.addEventListener("change", update);
  update();
})();
