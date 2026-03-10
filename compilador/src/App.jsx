import { useMemo, useRef, useState } from "react";
import "./App.css";
import { openExecutionView, sendExecutionOutput } from "./webviewer";

const BACKEND_URL = "http://127.0.0.1:8000";
const STAGES = [
  { id: "lexico", label: "Léxico", path: "/api/lexico" },
  { id: "sintactico", label: "Sintáctico", path: "/api/sintactico" },
  { id: "semantico", label: "Semántico", path: "/api/semantico" },
  { id: "compile", label: "Compilar", path: "/api/compile" },
];
const INITIAL_TABS = [{ id: 1, name: "programa.ts", content: "" }];

function downloadText(filename, text, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ensureTsFilename(filename) {
  if (!filename) return "programa.ts";
  return filename.toLowerCase().endsWith(".ts") ? filename : `${filename}.ts`;
}

function formatDiagnostics(diagnostics) {
  if (!diagnostics?.length) return "Sin errores.";
  return diagnostics
    .map((d) => `[${d.stage}] ${d.type} L${d.line}:C${d.column} - ${d.message}`)
    .join("\n");
}

function formatTokens(tokens) {
  if (!tokens?.length) return "Sin tokens.";
  return tokens.map((t) => `${t.type}(${t.lexeme}) @ ${t.line}:${t.column}`).join("\n");
}

export default function App() {
  const [tabs, setTabs] = useState(INITIAL_TABS);
  const [activeTabId, setActiveTabId] = useState(1);
  const [tokensPanel, setTokensPanel] = useState("Sin análisis léxico.");
  const [nasmPanel, setNasmPanel] = useState("Sin compilación.");
  const [compileTerminal, setCompileTerminal] = useState("Terminal de compilación lista.\n");
  const [executionTerminal, setExecutionTerminal] = useState("Sin ejecución.\n");
  const [errorTerminal, setErrorTerminal] = useState("Sin errores.\n");
  const [activeTerminalTab, setActiveTerminalTab] = useState("compile");
  const fileInputRef = useRef(null);
  const executionViewRef = useRef(null);
  const tabIdCounterRef = useRef(INITIAL_TABS.length + 1);

  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) ?? tabs[0],
    [tabs, activeTabId]
  );

  const setActiveContent = (content) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, content } : t)));
  };

  const appendCompileTerminal = (message) => {
    setCompileTerminal((prev) => `${prev}${message}\n`);
  };

  const appendExecutionTerminal = (message) => {
    setExecutionTerminal((prev) => `${prev}${message}\n`);
    sendExecutionOutput(executionViewRef.current, message);
  };

  const onOpenClick = () => fileInputRef.current?.click();

  const onFileChosen = async (e) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;

    const opened = await Promise.all(
      files.map(async (f) => ({
        id: tabIdCounterRef.current++,
        name: ensureTsFilename(f.name),
        content: await f.text(),
      }))
    );
    setTabs((prev) => [...prev, ...opened]);
    setActiveTabId(opened[opened.length - 1].id);
    appendCompileTerminal(`[Archivo] ${opened.length} archivo(s) abierto(s).`);
    e.target.value = "";
  };

  const onSaveClick = () => {
    if (!activeTab) return;
    const filename = ensureTsFilename(activeTab.name);
    downloadText(filename, activeTab.content, "application/typescript;charset=utf-8");
    appendCompileTerminal(`[Archivo] Guardado/descargado: ${filename}`);
  };

  const onDownloadClick = () => {
    onSaveClick();
  };

  const onCloseTab = (id) => {
    setTabs((prev) => {
      if (prev.length === 1) {
        appendCompileTerminal("[Archivo] No se puede cerrar la última pestaña.");
        return prev;
      }
      const filtered = prev.filter((t) => t.id !== id);
      if (id === activeTabId) setActiveTabId(filtered[0].id);
      return filtered;
    });
  };

  const onNewTab = () => {
    const newTab = {
      id: tabIdCounterRef.current++,
      name: `nuevo_${tabs.length + 1}.ts`,
      content: "",
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(newTab.id);
    appendCompileTerminal(`[Archivo] Nueva pestaña: ${newTab.name}`);
  };

  const runStage = async (stage) => {
    if (!activeTab) return;
    appendCompileTerminal(`[Compilador] Ejecutando etapa: ${stage.label}`);
    setActiveTerminalTab("compile");

    try {
      const response = await fetch(`${BACKEND_URL}${stage.path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: activeTab.content }),
      });
      const data = await response.json();

      if (data.tokens) setTokensPanel(formatTokens(data.tokens));
      if (typeof data.nasm === "string") setNasmPanel(data.nasm || "Sin NASM generado.");

      const diagnostics = data.diagnostics ?? [];
      setErrorTerminal(formatDiagnostics(diagnostics));

      if (!response.ok) {
        appendCompileTerminal(`[Compilador] Etapa ${stage.label}: finalizada con errores.`);
        appendExecutionTerminal(`[Ejecución] No disponible por errores en ${stage.label}.`);
        setActiveTerminalTab("errors");
      } else {
        appendCompileTerminal(`[Compilador] Etapa ${stage.label}: OK.`);
        if (stage.id === "compile") {
          appendExecutionTerminal("[Ejecución] Compilación completada sin errores.");
          setActiveTerminalTab("execution");
        }
      }
    } catch (error) {
      const msg = `[Compilador] Error de conexión backend: ${error.message}`;
      setErrorTerminal(msg);
      appendCompileTerminal(msg);
      setActiveTerminalTab("errors");
    }
  };

  const onOpenExecutionView = () => {
    executionViewRef.current = openExecutionView();
    appendCompileTerminal("[UI] Vista de ejecución abierta (webviewer/ventana o fallback embebido).");
  };

  const onCloseFile = () => {
    if (!activeTab) return;
    onCloseTab(activeTab.id);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="title">
          <div className="h1">Compilador</div>
          <div className="h2">Frontend React + backend Python</div>
        </div>

        <nav className="menu">
          <div className="menuGroup">
            <div className="menuTitle">Archivo</div>
            <div className="menuItems">
              <button onClick={onOpenClick}>Abrir</button>
              <button onClick={onSaveClick}>Guardar</button>
              <button onClick={onDownloadClick}>Descargar</button>
              <button onClick={onCloseFile}>Cerrar</button>
              <button onClick={onNewTab}>Nueva pestaña</button>
            </div>
          </div>
          <div className="menuGroup">
            <div className="menuTitle">Análisis</div>
            <div className="menuItems">
              <button onClick={onOpenExecutionView}>Abrir ejecución</button>
              {STAGES.map((stage) => (
                <button key={stage.id} onClick={() => runStage(stage)}>
                  {stage.label}
                </button>
              ))}
            </div>
          </div>
        </nav>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".ts,.txt"
          onChange={onFileChosen}
          style={{ display: "none" }}
        />
      </header>

      <main className="main">
        <section className="editorPane">
          <div className="tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`tab ${tab.id === activeTabId ? "active" : ""}`}
                onClick={() => setActiveTabId(tab.id)}
              >
                {tab.name}
                <span
                  className="tabClose"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.id);
                  }}
                >
                  ×
                </span>
              </button>
            ))}
          </div>
          <textarea
            className="editor"
            value={activeTab?.content ?? ""}
            onChange={(e) => setActiveContent(e.target.value)}
            placeholder="Escribe tu código aquí..."
            spellCheck={false}
          />
        </section>

        <section className="panel">
          <div className="paneTitle">Tokenización</div>
          <pre className="output">{tokensPanel}</pre>
        </section>

        <section className="panel">
          <div className="paneTitle">NASM</div>
          <pre className="output">{nasmPanel}</pre>
        </section>

        <section className="panel panelWide">
          <div className="tabs terminalTabs">
            <button
              className={`tab ${activeTerminalTab === "compile" ? "active" : ""}`}
              onClick={() => setActiveTerminalTab("compile")}
            >
              Compilación
            </button>
            <button
              className={`tab ${activeTerminalTab === "execution" ? "active" : ""}`}
              onClick={() => setActiveTerminalTab("execution")}
            >
              Ejecución
            </button>
            <button
              className={`tab ${activeTerminalTab === "errors" ? "active" : ""}`}
              onClick={() => setActiveTerminalTab("errors")}
            >
              Errores / Warnings
            </button>
          </div>
          <pre className="output">
            {activeTerminalTab === "compile"
              ? compileTerminal
              : activeTerminalTab === "execution"
                ? executionTerminal
                : errorTerminal}
          </pre>
        </section>
      </main>
    </div>
  );
}
