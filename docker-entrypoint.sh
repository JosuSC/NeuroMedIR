#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Arranque del contenedor NeuroMedIR
#
# 1. Si la carpeta de índices está vacía, construye los índices desde el corpus
#    inicial (cumple el requisito: "la carga del sistema debe indexar su corpus
#    inicial como un paso requerido").
# 2. Arranca el servidor FastAPI en el puerto 8000.
# =============================================================================
set -e

INDEX_DIR="/app/indices"

# Comprobar si la carpeta de índices está vacía (robusto frente al nombre exacto
# de los archivos que genere run_indexing.py).
if [ -z "$(ls -A "$INDEX_DIR" 2>/dev/null)" ]; then
    echo "============================================================"
    echo " Índices no encontrados. Construyendo desde el corpus..."
    echo " (Paso único; puede tardar varios minutos.)"
    echo "============================================================"
    python run_indexing.py
    echo " Indexación completada."
else
    echo "Índices encontrados. Omitiendo reconstrucción."
fi

echo "Iniciando NeuroMedIR en http://0.0.0.0:8000 ..."
exec python -m uvicorn api:app --host 0.0.0.0 --port 8000