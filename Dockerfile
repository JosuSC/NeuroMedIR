# =============================================================================
# NeuroMedIR — Dockerfile multi-stage
# =============================================================================

# -----------------------------------------------------------------------------
# Etapa 1 — Compilar el frontend (React + Vite)
# -----------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ENV VITE_API_URL=""
RUN npm run build

# -----------------------------------------------------------------------------
# Etapa 2 — Runtime Python (sirve API + frontend compilado)
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

WORKDIR /app

# Solo libgomp1 (runtime de OpenMP que FAISS necesita). NO hace falta
# build-essential: todas las dependencias vienen como wheels precompilados.
# Acquire::Retries hace que apt reintente ante cortes de red.
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
 && apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# --- Dependencias de Python ---
# torch CPU primero, desde su índice propio, para evitar bajar la build CUDA (~2 GB).
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# --- Descargar modelos de HuggingFace en build (quedan en la imagen) ---
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# --- Datos de NLTK ---
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True); nltk.download('stopwords', quiet=True)" || true

# --- Copiar código del backend (incluye el corpus inicial) ---
COPY . .

# --- Frontend compilado desde la etapa 1 ---
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# --- Script de arranque (normaliza CRLF->LF por si se editó en Windows) ---
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
 && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]