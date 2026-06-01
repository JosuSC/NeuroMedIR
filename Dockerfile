# =============================================================================
# NeuroMedIR — Dockerfile multi-stage
# =============================================================================

# -----------------------------------------------------------------------------
# Etapa 1 - Compilar el frontend
# -----------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ENV VITE_API_URL=""
RUN npm run build

# -----------------------------------------------------------------------------
# Etapa 2 - Runtime Python
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

WORKDIR /app

# --- Dependencias de Python ---
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# --- Descargar modelos de HuggingFace en build ---
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# --- Datos de NLTK ---
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)" || true

# --- Copiar codigo del backend ---
COPY . .

# --- Frontend compilado ---
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# --- Script de arranque ---
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]