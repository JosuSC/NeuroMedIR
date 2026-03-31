# Crawler & Scraper Module — NeuroMedIR

Este módulo maneja la recolección, extracción, validación y almacenamiento de documentos médicos desde fuentes web públicas.

## Arquitectura

```
crawler/
├── crawler.py              # Orquestador: BFS traversal, politeness, URLs visitadas
├── scraper.py             # Fetch con reintentos/backoff, parsing HTML, extracción de contenido
├── document_classifier.py # Validación de schema, categorización automática por dominio/contenido
├── storage.py             # Persistencia: organización por categoría, logging de rechazos
├── utils.py               # Utilidades: logging, validación URLs, limpieza texto
├── __pycache__/           # Compilados Python
└── test_crawler.py        # Tests unitarios end-to-end
```

## Flujo de Procesamiento

```
seed_urls (MedlinePlus, PubMed, OMS)
    ↓
[Crawler: BFS con límites de profundidad]
    ↓
[Scraper: fetch_page() con reintentos + backoff exponencial]
    ↓
[Scraper: parse_content() → extrae título, contenido, dominio]
    ↓
[DocumentClassifier: valida schema + infiere categoría]
    ↓
┌─────────────────────────┬────────────────────────────┐
│ VÁLIDO                  │ INVÁLIDO                   │
│ → data/processed/{cat}/ │ → data/rejected/           │
│   doc_1.json            │   rejected_doc_1.json      │
└─────────────────────────┴────────────────────────────┘
```

## Características Implementadas

### 1. Crawling Respetuoso
- Verifica `robots.txt` antes de acceder a cada URL
- Aplica delays configurable entre peticiones
- BFS con control de profundidad máxima
- Límite de páginas totales
- User-Agent transparente

### 2. Scraping Robusto
- **Reintentos con backoff exponencial** para errores transitorios (timeouts, 5xx)
- Diferencia entre errores recuperables (5xx, timeout) y no recuperables (4xx, conexión)
- Timeout configurable por petición
- Limpieza automática de HTML ruidoso (script, nav, footer, etc.)

### 3. Validación de Documentos
- Schema mínimo requerido:
  - `title`: no vacío, tipo string
  - `content`: mín. 100 caracteres
  - `source`: dominio identificable
  - `url`: URL válida y no vacía
- Rechaza documentos cortos (boilerplate, páginas de error)
- Registra motivo del rechazo en `data/rejected/`

### 4. Categorización Automática
Documentos se clasifican por:
- **health_topic**: MedlinePlus, recursos de salud
- **research_article**: PubMed, artículos académicos
- **health_guideline**: OMS, recomendaciones oficiales
- **news**: artículos de actualidad médica
- **generic_content**: otros

Mapeo: `source` → categoría predeterminada, luego palabras clave en `content`.

### 5. Organización Jerárquica
```
data/
├── raw/                          # HTML crudos (opcional)
├── processed/                    # Documentos válidos
│   ├── health_topic/
│   │   ├── doc_1.json
│   │   ├── doc_5.json
│   │   └── ...
│   ├── research_article/
│   │   ├── doc_2.json
│   │   └── ...
│   ├── health_guideline/
│   ├── news/
│   └── generic_content/
└── rejected/                     # Documentos inválidos
    ├── rejected_doc_3.json       # Con motivo del rechazo
    └── ...
```

### 6. Logging Detallado
- Logs por etapa: crawl, scrape, validación, guardado
- Diferencia entre WARN (reintento) e ERROR (fallo definitivo)
- Estadísticas finales: documentos válidos vs rechazados

## Uso

### 1. Ejecutar Crawl Desde Cero

```bash
cd NeuroMedIR
python main.py
```

**Qué hace `main.py`:**
- Define seeds médicas (MedlinePlus EN/ES, PubMed trending, OMS)
- Configuración: max_pages=20, max_depth=2, delay=1.5s
- Inicia crawl completo
- Resultados en `data/processed/` y `data/rejected/`

**Parámetros personalizables en `main.py`:**
```python
my_crawler = Crawler(
    seed_urls=[...],          # URLs iniciales
    max_pages=20,             # Límite total de documentos a recolectar
    max_depth=2,              # Profundidad máxima de crawling
    delay_seconds=1.5,        # Segundos entre peticiones
    user_agent="..."          # User-Agent transparente
)
```

### 2. Personalizar Scraper (Reintentos)

```python
from crawler.scraper import Scraper

scraper = Scraper(
    max_retries=3,            # Número de reintentos
    backoff_base=2.0          # Base exponencial: delay = 2^attempt
)
# Automáticamente reintenta en timeout y errores 5xx
response = scraper.fetch_page(url, headers, timeout=10)
```

### 3. Clasificar y Validar Manualmente

```python
from crawler.document_classifier import DocumentClassifier

doc = {
    "title": "...",
    "content": "...",
    "source": "medlineplus.gov",
    "url": "..."
}

# Enriquecer con validación + categoría
enriched = DocumentClassifier.enrich_document(doc)
print(enriched["is_valid"])      # bool
print(enriched["category"])       # str
print(enriched["validation_error"]) # str o None
```

### 4. Ejecutar Tests

```bash
cd crawler
python -m unittest test_crawler.py -v
```

**Tests cubiertos:**
- URLs: validación de formato
- Texto: limpieza, normalización
- Clasificación: inferencia de categoría, validación de schema
- Scraping: extracción de enlaces, parsing HTML, reintentos
- Storage: organización por categoría, guardado de rechazos

## Estadísticas y Monitoreo

Tras ejecutar `main.py`, verás logs como:

```
2026-03-31 14:22:00 - crawler.crawler - INFO - Crawleando (1/20) [Depth 0]: https://medlineplus.gov/healthtopics.html
2026-03-31 14:22:02 - crawler.document_classifier - WARNING - Invalid document: Content too short (45 chars, min 100)
2026-03-31 14:22:03 - crawler.storage - INFO - Documento 1 guardado en categoría 'health_topic'
...
2026-03-31 14:25:00 - crawler.crawler - INFO - Crawling finalizado. Total documentos recolectados: 20 | Válidos: 18 | Rechazados: 2
```

**Interpretar resultado:**
- **Total recolectados**: Páginas procesadas (válidas + rechazadas)
- **Válidos**: Documentos guardados en `processed/{category}/`
- **Rechazados**: Documentos guardados en `rejected/` con motivo

## Formato de Documento Válido

```json
{
  "title": "Health Topics: MedlinePlus",
  "content": "health topics read about symptoms, causes, treatment...",
  "source": "medlineplus.gov",
  "url": "https://medlineplus.gov/healthtopics.html",
  "id": 1,
  "is_valid": true,
  "category": "health_topic",
  "validation_error": null
}
```

## Formato de Documento Rechazado

```json
{
  "title": "...",
  "content": "...",
  "source": "...",
  "url": "...",
  "id": 3,
  "is_valid": false,
  "category": null,
  "validation_error": "Content too short (45 chars, min 100)",
  "rejection_reason": "Content too short (45 chars, min 100)"
}
```

## Manejo de Errores

| Error | Comportamiento |
|-------|-----------------|
| Timeout | Reintenta 3 veces con backoff exponencial, luego falla |
| HTTP 5xx | Reintenta, sino falla |
| HTTP 4xx | Falla inmediatamente (político, no culpa del servidor) |
| Ruido de red | Falla inmediatamente |
| Content-Type no HTML | Salta URL, continúa crawling |
| robots.txt bloquea | Salta URL, continúa crawling |
| Contenido muy corto | Valida como rechazado, guarda en rejected/ |

## Configuración Recomendada para Producción

```python
Crawler(
    seed_urls=[...],
    max_pages=1000,          # Corpus de escala mediana
    max_depth=3,             # Más cobertura
    delay_seconds=2.0,       # Respeto a servidores
    user_agent="NeuroMedIR-Bot/1.0 (+https://proyecto.edu)"
)

Scraper(
    max_retries=5,           # Más resilencia
    backoff_base=2.0         # Backoff: 1s, 2s, 4s, 8s, 16s
)
```

## Próximos Pasos

1. Ejecutar tests: `python -m unittest crawler/test_crawler.py -v`
2. Ejecutar crawl: `python main.py`
3. Revisar resultados en `data/processed/` y `data/rejected/`
4. Ajustar categorías en `document_classifier.py` si es necesario
5. Usar documentos válidos como entrada para indexación offline (módulo `indexing/`)

## Integración con Indexación

Una vez validados, los documentos en `data/processed/` se pasan al indexador:

```python
from indexing.indexer import Indexer
import json
import os

indexer = Indexer()

# Cargar todos los documentos válidos
docs = []
for cat in os.listdir("data/processed"):
    cat_dir = os.path.join("data/processed", cat)
    if os.path.isdir(cat_dir):
        for fname in os.listdir(cat_dir):
            with open(os.path.join(cat_dir, fname)) as f:
                docs.append(json.load(f))

# Indexar
indexer.index_documents(docs)
indexer.save_indices()
```
