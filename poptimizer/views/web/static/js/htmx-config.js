htmx.config.defaultSwapStyle = "outerHTML";

function setTheme(event) {
  if (!event?.detail?.successful) {
    return;
  }

  const requestPath = event.detail.pathInfo?.requestPath;
  if (!requestPath) {
    return;
  }

  const themeName = requestPath.split("/").pop();

  const allowedThemes = ["light", "dark", "system"];
  if (!allowedThemes.includes(themeName)) {
    return;
  }

  document.documentElement.setAttribute("data-theme", themeName);
}
