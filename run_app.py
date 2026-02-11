import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import webview

# Ajusta estas rutas a tu estructura:
# proyecto/
#   run_app.py
#   interfaz-compilador/   (React/Vite)
#       package.json
REACT_DIR = Path(__file__).parent / "compilador"
DEV_URL = "http://127.0.0.1:5173"


def wait_for_url(url: str, timeout_sec: int = 30) -> None:
    start = time.time()
    last_err = None
    while time.time() - start < timeout_sec:
        try:
            with urlopen(url, timeout=1) as resp:
                if 200 <= resp.status < 500:
                    return
        except Exception as e:
            last_err = e
            time.sleep(0.25)
    raise RuntimeError(f"No se pudo abrir {url} en {timeout_sec}s. Último error: {last_err}")


def start_react_dev_server() -> subprocess.Popen:
    if not (REACT_DIR / "package.json").exists():
        raise FileNotFoundError(f"No existe package.json en {REACT_DIR}")

    # En Windows conviene shell=True para resolver npm.cmd
    is_windows = (os.name == "nt")

    # Evita que Vite abra navegador por su cuenta
    env = os.environ.copy()
    env["BROWSER"] = "none"

    cmd = "bun dev -- --host 127.0.0.1 --port 5173"
    proc = subprocess.Popen(
        cmd,
        cwd=str(REACT_DIR),
        env=env,
        shell=is_windows,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def main():
    react_proc = None
    try:
        react_proc = start_react_dev_server()
        wait_for_url(DEV_URL, timeout_sec=45)

        # Abre ventana "tipo app" usando WebView2 (en Windows)
        window = webview.create_window(
            title="Compiladores - Diseño Compilador",
            url=DEV_URL,
            width=1200,
            height=800,
            resizable=True,
        )
        webview.start()

    finally:
        # Cierra el dev server al salir
        if react_proc and react_proc.poll() is None:
            react_proc.terminate()
            try:
                react_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                react_proc.kill()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)