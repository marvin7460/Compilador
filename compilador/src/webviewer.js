function resolveWebviewer() {
  if (typeof window === "undefined") return null;
  return window.pywebview || window.webviewer || null;
}

export function openExecutionView() {
  const webviewer = resolveWebviewer();
  if (webviewer?.api?.openExecutionView) {
    try {
      webviewer.api.openExecutionView();
      return { supported: true };
    } catch (error) {
      return { supported: false, error: error?.message || "No se pudo abrir webviewer." };
    }
  }
  return { supported: false, error: "Webviewer no disponible. Usando terminal embebida." };
}

export function sendOutputToExecutionView(payload) {
  const webviewer = resolveWebviewer();
  if (webviewer?.api?.appendExecutionLog) {
    try {
      webviewer.api.appendExecutionLog(payload);
      return { supported: true };
    } catch (error) {
      return { supported: false, error: error?.message || "No se pudo enviar salida a webviewer." };
    }
  }
  return { supported: false };
}
