function handleCmd(event) {
  const cmd = event?.detail?.cmd;
  const args = event?.detail?.args;

  switch (cmd) {
    case "set_theme":
      setTheme(args?.theme);
      break;
    case "set_title":
      setTitle();
      break;
    default:
      console.error("Unknown command:", cmd);
  }
}

function setTheme(themeName) {
  const allowedThemes = ["light", "dark", "system"];
  if (!allowedThemes.includes(themeName)) {
    return;
  }

  document.body.setAttribute("data-theme", themeName);
}

function setTitle() {
  const h1Element = document.querySelector("h1");

  if (h1Element) {
    const h1Text = h1Element.textContent.trim();
    document.title = `POptimizer - ${h1Text}`;
  }
}
