import { useMemo, useRef, useState } from "react";
import "./App.css";
import { openExecutionView, sendOutputToExecutionView } from "./webviewer";

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
  const [terminal, setTerminal] = useState("Terminal lista.\n");
  const [executionPanel, setExecutionPanel] = useState("Sin ejecución.\n");
  const [errorPanel, setErrorPanel] = useState("Sin errores.\n");
  const [astPanel, setAstPanel] = useState("AST no generado.");
  const [outputTab, setOutputTab] = useState("compile");
  const fileInputRef = useRef(null);
  const tabIdCounterRef = useRef(INITIAL_TABS.length + 1);

  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) ?? tabs[0],
    [tabs, activeTabId]
  );

  const setActiveContent = (content) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, content } : t)));
  };

  const appendTerminal = (message) => {
    setTerminal((prev) => `${prev}${message}\n`);
  };

  const appendExecution = (message) => {
    setExecutionPanel((prev) => `${prev}${message}\n`);
    sendOutputToExecutionView(message);
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
    appendTerminal(`[Archivo] ${opened.length} archivo(s) abierto(s).`);
    e.target.value = "";
  };

  const onSaveClick = () => {
    if (!activeTab) return;
    const filename = ensureTsFilename(activeTab.name);
    downloadText(filename, activeTab.content, "application/typescript;charset=utf-8");
    appendTerminal(`[Archivo] Guardado/descargado: ${filename}`);
  };

  const onDownloadClick = () => {
    onSaveClick();
  };

  const onCloseTab = (id) => {
    setTabs((prev) => {
      if (prev.length === 1) {
        appendTerminal("[Archivo] No se puede cerrar la última pestaña.");
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
    appendTerminal(`[Archivo] Nueva pestaña: ${newTab.name}`);
  };

  const runStage = async (stage) => {
    if (!activeTab) return;
    appendTerminal(`[Compilador] Ejecutando etapa: ${stage.label}`);

    try {
      const response = await fetch(`${BACKEND_URL}${stage.path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: activeTab.content }),
      });
      const data = await response.json();

      if (data.tokens) setTokensPanel(formatTokens(data.tokens));
      if (typeof data.nasm === "string") setNasmPanel(data.nasm || "Sin NASM generado.");
      if (data.ast) setAstPanel(JSON.stringify(data.ast, null, 2));

      const diagnostics = data.diagnostics ?? [];
      setErrorPanel(formatDiagnostics(diagnostics));

      if (!response.ok) {
        appendTerminal(`[Compilador] Etapa ${stage.label}: finalizada con errores.`);
        appendExecution(`[Ejecución] Detenida en etapa ${stage.label}.`);
      } else {
        appendTerminal(`[Compilador] Etapa ${stage.label}: OK.`);
        if (stage.id === "compile") {
          appendExecution("[Ejecución] Compilación completada. Revise NASM para ejecución externa.");
        }
      }
    } catch (error) {
      const msg = `[Compilador] Error de conexión backend: ${error.message}`;
      setErrorPanel(msg);
      appendTerminal(msg);
      appendExecution("[Ejecución] Falló la comunicación con backend.");
    }
  };

  const onCloseFile = () => {
    if (!activeTab) return;
    onCloseTab(activeTab.id);
  };

  const onOpenWebviewer = () => {
    const status = openExecutionView();
    if (status.supported) {
      appendExecution("[Webviewer] Vista de ejecución abierta.");
    } else if (status.error) {
      appendTerminal(`[Webviewer] ${status.error}`);
    }
  };

  const compileConsole = `${tokensPanel}\n\nAST:\n${astPanel}\n\nNASM:\n${nasmPanel}`;

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
              {STAGES.map((stage) => (
                <button key={stage.id} onClick={() => runStage(stage)}>
                  {stage.label}
                </button>
              ))}
              <button onClick={onOpenWebviewer}>Abrir webviewer</button>
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

        <section className="panel panelWide">
          <div className="tabs outputTabs">
            <button className={`tab ${outputTab === "compile" ? "active" : ""}`} onClick={() => setOutputTab("compile")}>
              Consola compilación
            </button>
            <button className={`tab ${outputTab === "run" ? "active" : ""}`} onClick={() => setOutputTab("run")}>
              Salida ejecución
            </button>
            <button className={`tab ${outputTab === "errors" ? "active" : ""}`} onClick={() => setOutputTab("errors")}>
              Errores/advertencias
            </button>
            <button className={`tab ${outputTab === "logs" ? "active" : ""}`} onClick={() => setOutputTab("logs")}>
              Logs
            </button>
          </div>
          <pre className="output">
            {outputTab === "compile" && compileConsole}
            {outputTab === "run" && executionPanel}
            {outputTab === "errors" && errorPanel}
            {outputTab === "logs" && terminal}
          </pre>
        </section>
      </main>
    </div>
  );
}
