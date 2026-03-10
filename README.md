# Compilador (Python + React)

Proyecto de compilador educativo con:

- **Backend Python (POO)** para análisis léxico/sintáctico/semántico y generación NASM.
- **Frontend React** para editor multi-pestaña, paneles de resultados y terminal de salida.

## Estado actual y cobertura de requisitos

| Requisito | Estado | Evidencia | Acción |
|---|---|---|---|
| Lexer con línea/columna | Sí | `/backend.py` (`Lexer`, `Token`, `Diagnostic`) | Mantener y extender tokens según lenguaje |
| Parser AST (funciones, return, while, for, break/continue, bloque global) | Sí | `/backend.py` (`Parser`, `Node`) | Mejorar recuperación de errores |
| Semántica (variables, tipos, funciones, retorno, break/continue) | Sí (básico) | `/backend.py` (`SemanticAnalyzer`) | Agregar coerciones/promoción de tipos si se requiere |
| Generación NASM | Sí (subset mínimo) | `/backend.py` (`NasmCodeGenerator`) | Ampliar soporte de tipos/calling convention |
| Pipeline por etapas | Sí | `/backend.py` (`CompilationPipeline`) | Añadir IR intermedio opcional |
| API por etapa | Sí | `/backend.py` (`BackendHandler`) | Integrar autenticación/versión API si aplica |
| Editor multi-pestaña | Sí | `/compilador/src/App.jsx` | Persistencia de sesión opcional |
| Abrir/guardar/descargar/cerrar archivo | Sí | `/compilador/src/App.jsx` | Guardado local avanzado opcional |
| Paneles fuente/tokens/NASM/errores/terminal | Sí | `/compilador/src/App.jsx` | Añadir panel AST opcional |
| Flujo con bloque global tipo main implícito | Sí | `/backend.py` (`Program.globalBlock`, `NasmCodeGenerator`) | Mantener regla documentada |

## Arquitectura

### Backend

- `Lexer`: tokeniza el código y reporta diagnósticos léxicos con posición.
- `Parser`: construye AST con nodos:
  - `FunctionDeclaration`
  - `FunctionCall`
  - `ReturnStatement`
  - `WhileStatement`
  - `ForStatement`
  - `BreakStatement`
  - `ContinueStatement`
  - `GlobalProgramBlock`
- `SemanticAnalyzer`: valida:
  - uso de variables declaradas,
  - redeclaraciones,
  - compatibilidad de tipos,
  - firmas de función (cantidad/tipo de argumentos),
  - tipo de retorno,
  - contexto válido de `break` / `continue`.
- `NasmCodeGenerator`: traduce el AST a NASM para el subset soportado.
- `CompilationPipeline`: orquesta etapas (`lexical`, `syntax`, `semantic`, `compile`).
- `Diagnostic`: formato unificado de error.

### Regla de punto de entrada (`main` explícito + bloque global)

1. Todo código fuera de funciones se ubica en un **bloque global ejecutable** (main implícito).
2. En NASM, `_start` ejecuta:
   - primero bloque global implícito,
   - luego `main()` explícito si existe.

## Endpoints backend

- `POST /api/lexico`
- `POST /api/sintactico`
- `POST /api/semantico`
- `POST /api/compile`

Body:

```json
{ "source": "codigo..." }
```

## Frontend

UI en `/compilador` con:

- Editor multi-pestaña.
- Acciones: abrir, guardar, descargar, cerrar, nueva pestaña.
- Botones por etapa: léxico, sintáctico, semántico, compilar.
- Paneles:
  - Fuente
  - Terminal de tokens
  - Terminal de ejecución
  - Terminal de ensamblador
  - Terminal de logs de proceso
- Botón **Abrir webviewer** con fallback embebido si no hay soporte.

## Instalación y ejecución

### Backend

```bash
cd /home/runner/work/Compilador/Compilador
python backend.py
```

> Alternativa recomendada para desarrollo de escritorio: `python run_app.py`

### Frontend

```bash
cd /home/runner/work/Compilador/Compilador/compilador
npm install
npm run dev
```

Build/lint:

```bash
npm run lint
npm run build
```

Pruebas backend:

```bash
cd /home/runner/work/Compilador/Compilador
python -m pytest -q
```

## Flujo de compilación

1. Tokenización (`Lexer`)
2. Parsing (`Parser`) -> AST
3. Análisis semántico (`SemanticAnalyzer`)
4. Generación NASM (`NasmCodeGenerator`) si no hay errores
5. Ejecución interpretada (`ExecutionEngine`) para mostrar salida en terminal de ejecución (incluye `console.log(...)`)

### Flujo de paneles en frontend

Cada ejecución de una etapa refresca de forma independiente:

- **Tokens**: salida de `tokens`.
- **Ejecución**: salida de `execution` (ejemplo: `console.log("hola")`).
- **Ensamblador**: salida de `nasm`.
- **Logs de proceso**: pasos del pipeline (`processLogs`) y diagnósticos con línea/columna.

## Prueba manual mínima

1. Iniciar backend y frontend.
2. Ingresar:

```ts
console.log("hola");
```

3. Presionar **Compilar** y verificar:
   - Tokens: aparecen `console`, `.`, `log`, `(`, `"hola"`, `)`, `;`.
   - Ejecución: aparece `hola`.
   - Ensamblador: se genera NASM.
   - Logs de proceso: aparecen pasos exitosos y estado final.

## Limitaciones actuales del lenguaje

- Subconjunto intencionalmente reducido (no hay clases/objetos).
- No hay optimización ni IR intermedio separado.
- Convención de llamadas NASM simplificada (educativa).
- Manejo de `string` en NASM es básico.

## Ejemplos válidos del lenguaje

```ts
var juan = 4;
var nombre = "Juan";
var x = 1;
x = 2;
```

```ts
function suma(a, b) { return a + b; }
var r = suma(2, 3);
```

```ts
// Flujo tipo burbuja (3 valores)
var a = 3;
var b = 1;
var c = 2;
var i = 0;
while (i < 2) {
  if (a > b) { var t1 = a; a = b; b = t1; }
  if (b > c) { var t2 = b; b = c; c = t2; }
  i = i + 1;
}
```
