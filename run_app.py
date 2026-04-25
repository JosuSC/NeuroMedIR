import sys
import time
import subprocess
import threading
import webview

def start_dev_server():
    """Inicia el servidor de Vite en segundo plano"""
    print("Iniciando motor de interfaz (Vite)...")
    # Usa shell=True para comandos npm en Windows
    return subprocess.Popen("npm run dev", cwd="frontend", shell=True)

def main():
    # 1. Levantar la interfaz gráfica compilada
    server_process = start_dev_server()
    
    # Dar tiempo a que el servidor esté activo antes de mostrar la ventana
    time.sleep(3)
    
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
    
    # 4. Limpiar el proceso hijo cuando se cierre la ventana de la app
    print("Cerrando aplicación...")
    server_process.kill()
    sys.exit(0)

if __name__ == "__main__":
    main()