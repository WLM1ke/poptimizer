htmx.config.responseHandling = [
  { code: "204", swap: false },
  { code: "[23]..", swap: true },
  { code: "[45]..", swap: true, error: false, target: ".alerts", swapOverride: "afterbegin" },
];

function setTheme(theme) {
  document.body.setAttribute("data-theme", theme);
}

function setTitle(title) {
  document.title = `POptimizer - ${title}`;
}
