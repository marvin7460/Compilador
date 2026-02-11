import { useMemo, useRef, useState } from "react";
import "./App.css";

const AVAILABLE_LIBS = [
  { id: "io", label: "io" },
  { id: "math", label: "math" },
  { id: "string", label: "string" },
];

const TYPES = [
  // Puedes ajustar estos a tu lenguaje
  { id: "int", label: "int", requiredLib: "math" },
  { id: "float", label: "float", requiredLib: "math" },
  { id: "string", label: "string", requiredLib: "string" },
  { id: "bool", label: "bool", requiredLib: "io" },
];

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function insertAtCursor(textarea, insertText) {
  const start = textarea.selectionStart ?? 0;
  const end = textarea.selectionEnd ?? 0;
  const value = textarea.value ?? "";
  const next = value.slice(0, start) + insertText + value.slice(end);
  const newCursor = start + insertText.length;
  return { next, newCursor };
}

export default function App() {
  const [source, setSource] = useState("");
  const [output, setOutput] = useState(
    "Salida: aquí se mostrarán resultados de Léxico/Sintáctico/Semántico/Código intermedio.\n"
  );

  const [activeLibs, setActiveLibs] = useState([]); // array de ids
  const [selectedType, setSelectedType] = useState(TYPES[0].id);

  const fileInputRef = useRef(null);
  const editorRef = useRef(null);

  const selectedTypeObj = useMemo(
    () => TYPES.find((t) => t.id === selectedType),
    [selectedType]
  );

  // ====== Archivo ======
  const onOpenClick = () => fileInputRef.current?.click();

  const onFileChosen = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setSource(text);
    setOutput((prev) => prev + `\n[Archivo] Abierto: ${file.name}\n`);
    e.target.value = ""; // permite volver a abrir el mismo archivo
  };

  const onSaveClick = () => {
    downloadText("programa.ts", source);
    setOutput((prev) => prev + "\n[Archivo] Guardado: programa.ts\n");
  };

  const onClearClick = () => {
    setSource("");
    setOutput((prev) => prev + "\n[Archivo] Pantalla limpiada\n");
  };

  const onCloseClick = () => {
    // En web no se puede cerrar la pestaña de forma segura si no la abriste con script.
    // Simulación: limpiar estado y mostrar mensaje.
    setSource("");
    setActiveLibs([]);
    setOutput("Aplicación cerrada (simulado). Recarga la página para iniciar de nuevo.\n");
  };

  // ====== Ayuda -> Librerías ======
  const addLibrary = (libId) => {
    setActiveLibs((prev) => (prev.includes(libId) ? prev : [...prev, libId]));
    setOutput((prev) => prev + `[Ayuda] Librería agregada: ${libId}\n`);
  };

  const removeLibrary = (libId) => {
    setActiveLibs((prev) => prev.filter((x) => x !== libId));
    setOutput((prev) => prev + `[Ayuda] Librería removida: ${libId}\n`);
  };

  // ====== Variable -> Tipo ======
  const onTypeChange = (e) => {
    const nextType = e.target.value;
    setSelectedType(nextType);

    const t = TYPES.find((x) => x.id === nextType);
    if (t?.requiredLib) {
      setActiveLibs((prev) => (prev.includes(t.requiredLib) ? prev : [...prev, t.requiredLib]));
      setOutput((prev) => prev + `[Variable] Tipo: ${t.label} (activa lib: ${t.requiredLib})\n`);
    } else {
      setOutput((prev) => prev + `[Variable] Tipo: ${t?.label ?? nextType}\n`);
    }
  };

  const insertVariableTemplate = () => {
    const textarea = editorRef.current;
    if (!textarea) return;

    const varName = "miVar";
    const typeLabel = selectedTypeObj?.label ?? selectedType;
    const snippet = `let ${varName}: ${typeLabel};\n`;

    const { next, newCursor } = insertAtCursor(textarea, snippet);
    setSource(next);

    // reposicionar cursor
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursor, newCursor);
    });

    setOutput((prev) => prev + `[Variable] Insertado: ${snippet}`);
  };

  // ====== Compilador (solo UI por ahora) ======
  const runStage = (stage) => {
    // Aquí después harás fetch a tu backend Python.
    setOutput((prev) => prev + `\n[Compilador] Ejecutar: ${stage}\n` + `(pendiente conectar backend)\n`);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="title">
          <div className="h1">Compiladores</div>
          <div className="h2">Tema: Diseño Compilador — Actividad 1</div>
          <div className="h3">Phd.MCC. Ramiro Lupercio Coronel</div>
        </div>

        <nav className="menu">
          <div className="menuGroup">
            <div className="menuTitle">Archivo</div>
            <div className="menuItems">
              <button onClick={onOpenClick}>Abrir</button>
              <button onClick={onSaveClick}>Guardar</button>
              <button onClick={onClearClick}>Limpiar</button>
              <button onClick={onCloseClick}>Cerrar</button>
            </div>
          </div>

          <div className="menuGroup">
            <div className="menuTitle">Compilador</div>
            <div className="menuItems">
              <button onClick={() => runStage("Análisis Léxico")}>Léxico</button>
              <button onClick={() => runStage("Análisis Sintáctico")}>Sintáctico</button>
              <button onClick={() => runStage("Análisis Semántico")}>Semántico</button>
              <button onClick={() => runStage("Código Intermedio")}>Código Intermedio</button>
            </div>
          </div>

          <div className="menuGroup">
            <div className="menuTitle">Ayuda</div>
            <div className="menuItems">
              {AVAILABLE_LIBS.map((lib) => (
                <button key={lib.id} onClick={() => addLibrary(lib.id)}>
                  + {lib.label}
                </button>
              ))}
            </div>
          </div>

          <div className="menuGroup">
            <div className="menuTitle">Variable</div>
            <div className="menuItems">
              <select value={selectedType} onChange={onTypeChange}>
                {TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <button onClick={insertVariableTemplate}>Insertar</button>
            </div>
          </div>
        </nav>

        <input
          ref={fileInputRef}
          type="file"
          accept=".ts,.txt"
          onChange={onFileChosen}
          style={{ display: "none" }}
        />
      </header>

      <main className="main">
        <section className="editorPane">
          <div className="paneTitle">Editor</div>
          <textarea
            ref={editorRef}
            className="editor"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="Escribe tu código aquí..."
            spellCheck={false}
          />
        </section>

        <aside className="sidePane">
          <div className="paneTitle">Librerías en la interfaz</div>
          <div className="chips">
            {activeLibs.length === 0 ? (
              <div className="muted">Ninguna</div>
            ) : (
              activeLibs.map((libId) => (
                <div key={libId} className="chip">
                  <span>{libId}</span>
                  <button className="chipClose" onClick={() => removeLibrary(libId)}>
                    x
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="paneTitle">Salida</div>
          <pre className="output">{output}</pre>
        </aside>
      </main>
    </div>
  );
}