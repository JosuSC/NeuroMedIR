import sys
import time
import subprocess
import threading
import webview

def start_dev_server():
    """Inicia el servidor de Vite en segundo plano"""
    print("Iniciando motor de interfaz (Vite)...")
    return subprocess.Popen("npm run dev", cwd="frontend", shell=True)

def start_backend_api():
    """Inicia el API FastAPI local del sistema"""
    print("Iniciando motor de Backend NeuroMedIR (API)...")
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "api:app", "--port", "8000"])

def main():
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
        background_color='#f8f9fa' # Mismo fondo de tu sistema
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