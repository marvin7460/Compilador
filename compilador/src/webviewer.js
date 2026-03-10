export function openExecutionView() {
  const viewer = globalThis?.webviewer;

  if (viewer && typeof viewer.openExecutionTab === "function") {
    try {
      const handle = viewer.openExecutionTab("Ejecución");
      return { mode: "webviewer", handle };
    } catch {
      return { mode: "embedded", handle: null };
    }
  }

  if (typeof window !== "undefined" && typeof window.open === "function") {
    const popup = window.open("", "compilador-ejecucion", "width=720,height=480");
    if (popup) {
      popup.document.title = "Salida de ejecución";
      popup.document.body.innerHTML = "<pre id='execution-log' style='font-family:monospace'></pre>";
      return { mode: "window", handle: popup };
    }
  }

  return { mode: "embedded", handle: null };
}

export function sendExecutionOutput(target, message) {
  if (!target) return false;

  if (target.mode === "webviewer" && target.handle?.postMessage) {
    try {
      target.handle.postMessage({ type: "execution-log", payload: message });
      return true;
    } catch {
      return false;
    }
  }

  if (target.mode === "window" && target.handle && !target.handle.closed) {
    const node = target.handle.document.getElementById("execution-log");
    if (node) {
      node.textContent = `${node.textContent}${message}\n`;
      return true;
    }
  }

  return false;
}
