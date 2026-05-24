import sys
import time
import subprocess
import threading
from pathlib import Path
import webview

"""
run_app.py — Lanzador de la app de escritorio.

Lo uso como una especie de wrapper de desarrollo para abrir a la vez el
backend FastAPI, el frontend Vite y la ventana nativa con pywebview.
Es una pieza pequeña pero importante porque junta todo el sistema.
"""


def start_dev_server():
    """Inicia el servidor de Vite en segundo plano."""
    print("Iniciando motor de interfaz (Vite)...")
    return subprocess.Popen("npm run dev", cwd="frontend", shell=True)


def start_backend_api():
    """Inicia el API FastAPI local del sistema."""
    print("Iniciando motor de Backend NeuroMedIR (API)...")
    
    # Intento usar el Python del entorno virtual para no mezclar intérpretes
    import os
    base_dir = Path(__file__).resolve().parent
    project_parent = base_dir.parent
    venv_python = base_dir / ".venv" / "Scripts" / "python.exe"
    if os.path.exists(venv_python):
        python_exe = str(venv_python)
    else:
        python_exe = sys.executable
        
    return subprocess.Popen(
        [python_exe, "-m", "uvicorn", "NeuroMedIR.api:app", "--port", "8000"],
        cwd=str(project_parent),
    )


def main():
    """Levanta backend, frontend y ventana nativa en una sola corrida."""
    # 1. Levantar API y Vite
    api_process = start_backend_api()
    server_process = start_dev_server()
    
    # Dar tiempo a que los servidores estén activos
    time.sleep(4)
    
    # 2. Crear una ventana de aplicación nativa (Escritorio)
    window = webview.create_window(
        'NeuroMedIR - Sistema de Recuperación de Información Médico',
        'http://localhost:5173',
        width=1280,
        height=850,
        min_size=(1024, 768),
        background_color='#f8f9fa' # Mantengo el mismo fondo visual del sistema
    )
    
    print("\nAbriendo aplicación NeuroMedIR...")
    
    # 3. Lanzar el loop principal de la GUI nativa
    webview.start(debug=True)
    
    # 4. Limpiar los procesos hijos cuando se cierre la ventana
    print("\nCerrando aplicación...")
    server_process.kill()
    api_process.kill()
    sys.exit(0)


if __name__ == "__main__":
    main()