#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Arranque del contenedor NeuroMedIR
#
# 1. Si los índices no existen, los construye desde el corpus crudo
#    (cumple el requisito: "la carga del sistema debe indexar el corpus
#     inicial como un paso requerido").
# 2. Arranca el servidor FastAPI en el puerto 8000.
# =============================================================================
set -e

INDEX_FILE="/app/indices/bm25_lexical.pkl"

if [ ! -f "$INDEX_FILE" ]; then
    echo "============================================================"
    echo " Índices no encontrados. Construyendo desde el corpus..."
    echo " (Este es un paso único; puede tardar varios minutos.)"
    echo "============================================================"
    python run_indexing.py
    echo " Indexación completada."
else
    echo "Índices encontrados. Omitiendo reconstrucción."
fi

echo "Iniciando NeuroMedIR en http://0.0.0.0:8000 ..."
exec python -m uvicorn api:app --host 0.0.0.0 --port 8000
