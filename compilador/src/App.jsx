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

function formatTokens(tokens) {
  if (!tokens?.length) return "Sin tokens.";
  return tokens.map((t) => `${t.type}(${t.lexeme}) @ ${t.line}:${t.column}`).join("\n");
}

function formatExecution(execution) {
  if (!execution?.length) return "Sin salida de ejecución.";
  return execution.join("\n");
}

function formatProcessLogs(processLogs, diagnostics) {
  const logs = [...(processLogs ?? [])];
  if (diagnostics?.length) {
    logs.push("Diagnósticos:");
    logs.push(...diagnostics.map((d) => `[${d.stage}] ${d.type} L${d.line}:C${d.column} - ${d.message}`));
  } else {
    logs.push("Sin diagnósticos.");
  }
  return logs.join("\n");
}

export default function App() {
  const [tabs, setTabs] = useState(INITIAL_TABS);
  const [activeTabId, setActiveTabId] = useState(1);
  const [tokensPanel, setTokensPanel] = useState("Sin análisis léxico.");
  const [nasmPanel, setNasmPanel] = useState("Sin ensamblador generado.");
  const [executionPanel, setExecutionPanel] = useState("Sin ejecución.\n");
  const [logsPanel, setLogsPanel] = useState("Logs de proceso listos.");
  const fileInputRef = useRef(null);
  const editorRef = useRef(null);
  const lineNumbersRef = useRef(null);
  const tabIdCounterRef = useRef(INITIAL_TABS.length + 1);

  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) ?? tabs[0],
    [tabs, activeTabId]
  );

  const setActiveContent = (content) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, content } : t)));
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
    setLogsPanel((prev) => `${prev}\n[Archivo] ${opened.length} archivo(s) abierto(s).`);
    e.target.value = "";
  };

  const onSaveClick = () => {
    if (!activeTab) return;
    const filename = ensureTsFilename(activeTab.name);
    downloadText(filename, activeTab.content, "application/typescript;charset=utf-8");
    setLogsPanel((prev) => `${prev}\n[Archivo] Guardado/descargado: ${filename}`);
  };

  const onDownloadClick = () => {
    onSaveClick();
  };

  const onCloseTab = (id) => {
    setTabs((prev) => {
        if (prev.length === 1) {
          setLogsPanel((current) => `${current}\n[Archivo] No se puede cerrar la última pestaña.`);
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
    setLogsPanel((prev) => `${prev}\n[Archivo] Nueva pestaña: ${newTab.name}`);
  };

  const runStage = async (stage) => {
    if (!activeTab) return;
    setTokensPanel("Procesando tokens...");
    setNasmPanel("Procesando ensamblador...");
    setExecutionPanel("Procesando ejecución...");
    setLogsPanel(`[Compilador] Ejecutando etapa: ${stage.label}`);

    try {
      const response = await fetch(`${BACKEND_URL}${stage.path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: activeTab.content }),
      });
      const data = await response.json();
      setTokensPanel(formatTokens(data.tokens));
      if (typeof data.nasm === "string") setNasmPanel(data.nasm || "Sin ensamblador generado.");
      setExecutionPanel(formatExecution(data.execution));
      const diagnostics = data.diagnostics ?? [];
      setLogsPanel(formatProcessLogs(data.processLogs, diagnostics));

      if (!response.ok) {
        setLogsPanel((prev) => `${prev}\n[Compilador] Etapa ${stage.label}: finalizada con errores.`);
      } else {
        setLogsPanel((prev) => `${prev}\n[Compilador] Etapa ${stage.label}: OK.`);
      }
    } catch (error) {
      const msg = `[Compilador] Error de conexión backend: ${error.message}`;
      setLogsPanel(msg);
      setExecutionPanel("[Ejecución] Falló la comunicación con backend.");
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
      setLogsPanel((prev) => `${prev}\n[Webviewer] ${status.error}`);
    }
  };

  const lineNumbers = useMemo(() => {
    const lineCount = (activeTab?.content ?? "").split("\n").length;
    return Array.from({ length: lineCount || 1 }, (_, i) => i + 1).join("\n");
  }, [activeTab?.content]);

  const onEditorScroll = () => {
    if (!editorRef.current || !lineNumbersRef.current) return;
    lineNumbersRef.current.scrollTop = editorRef.current.scrollTop;
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
          <div className="editorWrapper">
            <pre ref={lineNumbersRef} className="lineNumbers">
              {lineNumbers}
            </pre>
            <textarea
              ref={editorRef}
              className="editor"
              value={activeTab?.content ?? ""}
              onChange={(e) => setActiveContent(e.target.value)}
              onScroll={onEditorScroll}
              placeholder="Escribe tu código aquí..."
              spellCheck={false}
            />
          </div>
        </section>

        <section className="panelsGrid">
          <article className="panel">
            <div className="paneTitle">Tokens</div>
            <pre className="output">{tokensPanel}</pre>
          </article>
          <article className="panel">
            <div className="paneTitle">Ejecución</div>
            <pre className="output">{executionPanel}</pre>
          </article>
          <article className="panel">
            <div className="paneTitle">Ensamblador</div>
            <pre className="output">{nasmPanel}</pre>
          </article>
          <article className="panel">
            <div className="paneTitle">Logs de Proceso</div>
            <pre className="output">{logsPanel}</pre>
          </article>
        </section>
      </main>
    </div>
  );
}
