htmx.config.defaultSwapStyle = "outerHTML";

function setTheme(event) {
  const themeName = event?.detail?.theme;
  const allowedThemes = ["light", "dark", "system"];
  if (!allowedThemes.includes(themeName)) {
    return;
  }

  document.body.setAttribute("data-theme", themeName);
}
