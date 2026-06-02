# Despliegue de NeuroMedIR con Docker

Guía para construir y ejecutar NeuroMedIR en cualquier entorno compatible con
Docker. La imagen empaqueta el backend (FastAPI), el frontend compilado (React +
Vite) y el corpus inicial; al primer arranque indexa ese corpus de forma automática.

## Archivos del despliegue

| Archivo | Función |
|---|---|
| `Dockerfile` | Definición de la imagen (multi-stage: Node para el frontend, Python para el runtime). |
| `docker-compose.yml` | Orquestación: puerto, variables de entorno y volúmenes persistentes. |
| `docker-entrypoint.sh` | Arranque: indexa el corpus si no hay índices y levanta el servidor. |
| `.dockerignore` | Qué se excluye del contexto de build (`.venv`, `.env`, `node_modules`, etc.). |
| `.env.example` | Plantilla de claves de API; se copia a `.env`. |
| `requirements.txt` | Dependencias de Python. |

## Requisitos previos

- **Docker** y **Docker Compose** instalados (Docker Desktop en Windows/macOS, o
  Docker Engine + plugin Compose en Linux).
- **Conexión a internet para el build:** la construcción descarga las imágenes base
  (Python y Node), PyTorch CPU y los modelos de Hugging Face. Son varios GB; con
  buena conexión tarda unos minutos, con conexión lenta puede tardar bastante. Una
  vez construida, la imagen no necesita volver a descargar nada.
- Espacio en disco: contar con ~6–8 GB libres para la imagen y los modelos.

## Pasos de despliegue

1. **Configurar las claves de API.** Copiar la plantilla y rellenar los valores:
   ```bash
   cp .env.example .env
   # editar .env y poner OPENROUTER_API_KEY, GEMINI_API_KEY y SERPAPI_API_KEY
   ```
   (El sistema arranca aunque falten claves, pero la generación RAG y la búsqueda
   web quedarán limitadas.)

2. **Construir y levantar:**
   ```bash
   docker compose up --build
   ```
   Este paso requiere internet (ver "Requisitos previos").

3. **Primer arranque — indexación automática.** La primera vez, al no existir
   índices, el contenedor ejecuta `run_indexing.py` y construye los índices desde el
   corpus inicial. Esto es un paso único que tarda varios minutos; los logs lo
   indican ("Construyendo desde el corpus...").

4. **Acceder al sistema.** Cuando el log muestre que el servidor está activo, abrir
   en el navegador:
   ```
   http://localhost:8000
   ```

5. **Arranques posteriores.** Los índices quedan en un volumen persistente, así que
   en siguientes ejecuciones no se reconstruyen:
   ```bash
   docker compose up
   ```

## Operación

- **Detener:** `docker compose down`
- **Detener y borrar los índices persistidos** (fuerza reindexar en el próximo
  arranque, útil para reproducir la indexación desde cero):
  ```bash
  docker compose down -v
  ```
- **Ver logs:** `docker compose logs -f`

## Notas importantes

- **Build vs. runtime.** El build necesita internet (imágenes base, torch, modelos).
  En runtime, internet solo hace falta para la generación RAG (API del LLM) y la
  búsqueda web (SerpApi); la recuperación funciona sin conexión.
- **Las claves nunca van en la imagen.** Se inyectan en runtime desde `.env` vía
  `docker-compose.yml` (`env_file`). El `.env` está excluido en `.dockerignore`.
- **Reproducir las dependencias exactas.** Para que la imagen reproduzca con
  exactitud el entorno que funciona en local, regenerar `requirements.txt` desde el
  entorno virtual de trabajo:
  ```bash
  pip freeze > requirements.txt
  ```
  Verificar en particular la versión de **torch** (`pip freeze | findstr torch` en
  Windows, `pip freeze | grep torch` en Linux/macOS) y, si difiere de la del
  `Dockerfile` (`torch==2.11.0`), ajustarla allí para que coincida.
- **Saltos de línea del entrypoint.** El `Dockerfile` normaliza `docker-entrypoint.sh`
  a saltos de línea Unix (LF) durante el build, así que funciona aunque se haya
  editado en Windows.
- **Puerto.** El servicio expone el 8000. Si está ocupado, cambiar el mapeo en
  `docker-compose.yml` (p. ej. `"8080:8000"`) y acceder por ese puerto.
