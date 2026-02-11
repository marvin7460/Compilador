# Compilador (UI React + Vite) + App de escritorio (PyWebView)

Este repositorio contiene una interfaz construida con **React + Vite** (carpeta `compilador/`) y un launcher en **Python** (`run_app.py`) que inicia el servidor de desarrollo y lo muestra en una ventana de escritorio usando **pywebview**.

## Estructura del proyecto

- `run_app.py`: inicia el dev server y abre la app en una ventana con WebView.
- `compilador/`: proyecto frontend (React + Vite).
  - `package.json`: scripts `dev`, `build`, `preview`, `lint`
  - `src/`: código fuente (por ejemplo `main.jsx`, `App.jsx`)
  - `public/`: assets estáticos

## Requisitos

### Para ejecutar el frontend (modo web)
- **Bun** (recomendado, porque `run_app.py` ejecuta `bun dev`)
  - Alternativa: Node.js + npm (ver nota abajo)

### Para ejecutar como app de escritorio
- **Python 3.10+** (recomendado)
- Paquete **pywebview**
- (Windows) WebView2 suele ser el backend más común para pywebview.

## Instalación

### 1) Instalar dependencias del frontend

```bash
cd compilador
bun install
```

## Ejecutar (web)

Desde `compilador/`:

```bash
bun dev
```

Luego abre en el navegador:
- `http://127.0.0.1:5173`

## Ejecutar (escritorio con PyWebView)

1) Instala dependencias de Python:

```bash
pip install pywebview
```

2) Instala dependencias del frontend (si no lo hiciste):

```bash
cd compilador
bun install
cd ..
```

3) Ejecuta el launcher:

```bash
python run_app.py
```

Esto:
- ejecuta `bun dev -- --host 127.0.0.1 --port 5173`
- espera a que el servidor esté disponible
- abre una ventana titulada **"Compiladores - Diseño Compilador"**

## Scripts disponibles (frontend)

En `compilador/package.json`:

- `bun dev` → servidor de desarrollo (Vite)
- `bun run build` → build de producción
- `bun run preview` → previsualizar build
- `bun run lint` → lint con ESLint

## Nota si NO usas Bun

Actualmente `run_app.py` ejecuta `bun dev`.  
Si prefieres npm, puedes:
- cambiar `cmd = "bun dev -- --host 127.0.0.1 --port 5173"` por `cmd = "npm run dev -- --host 127.0.0.1 --port 5173"` en `run_app.py`, o
- ejecutar el frontend manualmente con npm y abrir `http://127.0.0.1:5173`.

## Estado actual

El README dentro de `compilador/` proviene del template de React+Vite. Este README (en la raíz) describe cómo correr el proyecto completo (web + desktop).

## Licencia

No especificada.