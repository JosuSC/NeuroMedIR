# NeuroMedIR Skills Catalog

Este documento define habilidades reutilizables para el desarrollo del sistema NeuroMedIR.
Cada habilidad está diseñada para ejecución modular, trazable y escalable.

## Skill 1: Web Crawling

### Descripción
Recolecta páginas web médicas de manera ética y controlada, respetando políticas de acceso y límites operativos.

### Cuándo usarla
1. Cuando se necesita construir o ampliar el corpus documental.
2. Cuando se requiere rastreo por dominio con control de profundidad.
3. Cuando se desea automatizar descubrimiento de nuevas URLs médicas.

### Pasos de ejecución
1. Definir seeds confiables y alcance por dominio.
2. Validar URLs iniciales y normalizar formato.
3. Configurar estrategia de recorrido (BFS o prioridad por relevancia).
4. Aplicar validación robots.txt por host.
5. Ejecutar crawling con rate limit y timeout configurables.
6. Registrar URL visitada, estado HTTP, profundidad y timestamp.
7. Detectar duplicados por URL canónica o hash.
8. Encolar enlaces válidos hasta límite de páginas o profundidad.

### Buenas prácticas
1. Usar user-agent explícito y transparente.
2. Implementar delays conservadores y backoff en errores transitorios.
3. Evitar crawling fuera del dominio sin política explícita.
4. Persistir checkpoints para reanudación de procesos largos.

### Ejemplo
Entrada:
- Seeds: https://medlineplus.gov/healthtopics.html
- max_pages: 500
- max_depth: 2

Salida:
- Lista de documentos crudos con URL, HTML, estado de extracción y metadatos de rastreo.

## Skill 2: Web Scraping

### Descripción
Extrae contenido relevante de HTML médico eliminando ruido estructural y conservando metadatos útiles para IR.

### Cuándo usarla
1. Cuando hay HTML crudo y se necesita texto utilizable.
2. Cuando se requiere transformar páginas web en documentos indexables.

### Pasos de ejecución
1. Parsear HTML con parser tolerante a errores.
2. Eliminar bloques no informativos: script, style, nav, footer y elementos de tracking.
3. Identificar región principal: main, article o body como fallback.
4. Extraer título, contenido, enlaces y metadatos de fuente.
5. Normalizar espacios, encoding y caracteres especiales.
6. Guardar documento procesado en esquema estable.

### Buenas prácticas
1. Implementar selectores robustos y fallback por estructura variable.
2. Medir densidad de texto para descartar páginas vacías o boilerplate.
3. Mantener vínculo entre documento procesado y URL original.

### Ejemplo
Entrada:
- HTML de una página de salud

Salida:
- JSON con campos: title, content, source, url, extracted_at.

## Skill 3: Text Preprocessing

### Descripción
Normaliza y transforma texto médico para mejorar indexación y recuperación.

### Cuándo usarla
1. Antes de construir índices léxicos.
2. Antes de generar embeddings.
3. Cuando se requiere estandarizar corpus heterogéneo.

### Pasos de ejecución
1. Aplicar normalización básica: lowercase o casefolding.
2. Limpiar ruido: HTML residual, símbolos irrelevantes y espacios redundantes.
3. Tokenizar según idioma objetivo.
4. Remover stopwords según tarea y evaluación.
5. Aplicar stemming o lematización según estrategia IR.
6. Opcional: detectar entidades biomédicas para enriquecer metadatos.
7. Persistir versión procesada con número de pipeline.

### Buenas prácticas
1. Versionar pipeline de preprocessing para reproducibilidad.
2. No eliminar términos clínicos de alto valor semántico.
3. Evaluar impacto de cada transformación en métricas de recuperación.

### Ejemplo
Entrada:
- Texto médico en bruto con ruido y formatos mixtos.

Salida:
- Tokens normalizados listos para indexación y búsqueda.

## Skill 4: Indexing (BM25 o TF-IDF)

### Descripción
Construye índices léxicos para recuperación eficiente basada en coincidencia de términos.

### Cuándo usarla
1. Cuando se necesita baseline fuerte de IR clásico.
2. Cuando se desea búsqueda transparente y explicable.

### Pasos de ejecución
1. Seleccionar representación documental final.
2. Tokenizar y construir vocabulario controlado.
3. Calcular estadísticas globales: DF, IDF, longitud de documento.
4. Construir índice invertido.
5. Configurar parámetros de ranking (ejemplo BM25 k1 y b).
6. Persistir índice y metadatos de versión.
7. Validar con conjunto de queries de referencia.

### Buenas prácticas
1. Separar claramente etapa de indexación y etapa de consulta.
2. Mantener compatibilidad entre versión del índice y versión de corpus.
3. Medir latencia de consulta y consumo de memoria.

### Ejemplo
Entrada:
- Colección de documentos procesados.

Salida:
- Índice invertido y puntuaciones de ranking por query.

## Skill 5: Embedding Generation

### Descripción
Genera representaciones vectoriales densas de documentos o fragmentos para recuperación semántica.

### Cuándo usarla
1. Cuando la búsqueda léxica no captura sinónimos o contexto.
2. Cuando se implementa recuperación semántica o híbrida.

### Pasos de ejecución
1. Seleccionar modelo de embeddings adecuado al dominio médico.
2. Definir estrategia de chunking por longitud semántica.
3. Limpiar y normalizar texto previo al embedding.
4. Generar vectores por chunk o documento.
5. Registrar metadatos: modelo, dimensión, versión y timestamp.
6. Validar distribución vectorial y cobertura de documentos.

### Buenas prácticas
1. Fijar versión de modelo para evitar deriva silenciosa.
2. Controlar longitud máxima por chunk para evitar truncamiento crítico.
3. Validar que dimensión de embedding sea consistente con la base vectorial.

### Ejemplo
Entrada:
- Documento médico procesado.

Salida:
- Lista de vectores con metadatos trazables por fragmento.

## Skill 6: Vector Search

### Descripción
Permite recuperar documentos por similitud semántica usando una base vectorial.

### Cuándo usarla
1. Cuando se requiere recuperación basada en intención y contexto.
2. Cuando se implementa capa semántica para RAG futuro.

### Pasos de ejecución
1. Indexar embeddings en motor vectorial.
2. Definir métrica de similitud: cosine, dot-product o L2.
3. Transformar query a embedding en el mismo espacio vectorial.
4. Ejecutar top-k nearest neighbors.
5. Aplicar filtros por metadatos: fuente, fecha, idioma o tipo de documento.
6. Devolver resultados con score y referencias trazables.

### Buenas prácticas
1. Mantener sincronía entre índice vectorial y repositorio documental.
2. Evaluar recall at k y precision at k con queries reales.
3. Combinar con reranking léxico-semántico en escenarios complejos.

### Ejemplo
Entrada:
- Query: tratamiento para hipertension resistente

Salida:
- Top-k documentos semánticamente cercanos con score y URL.

## Skill 7: JSON Data Storage

### Descripción
Define almacenamiento estructurado en JSON para documentos crudos y procesados con trazabilidad completa.

### Cuándo usarla
1. En fases tempranas o medianas del pipeline.
2. Cuando se necesita inspección manual y depuración rápida de datos.

### Pasos de ejecución
1. Definir esquema JSON para raw y processed.
2. Validar campos obligatorios antes de guardar.
3. Guardar en directorios separados por tipo de dato.
4. Nombrar archivos con identificador estable.
5. Incluir metadatos de versión y fecha de procesamiento.
6. Mantener codificación UTF-8 y serialización consistente.

### Buenas prácticas
1. No mezclar datos crudos y transformados en el mismo artefacto.
2. Evitar romper compatibilidad de esquema sin migración.
3. Agregar validación de integridad al cargar datos.

### Ejemplo
Entrada:
- Documento parseado con id y metadatos.

Salida:
- Archivo JSON persistido en processed con estructura validada.

## Skill 8: Error Handling

### Descripción
Implementa control robusto de errores para mantener estabilidad del sistema ante fallos de red, parsing, indexación o almacenamiento.

### Cuándo usarla
1. En cualquier módulo de producción.
2. Cuando existen dependencias externas o datos no confiables.

### Pasos de ejecución
1. Identificar fallos esperables por componente.
2. Definir excepciones específicas por dominio.
3. Aplicar reintentos selectivos en errores transitorios.
4. Registrar errores con contexto operativo suficiente.
5. Aislar documentos problemáticos sin detener todo el pipeline.
6. Exponer métricas de fallos por etapa.

### Buenas prácticas
1. Evitar catch-all sin acciones de diagnóstico.
2. Diferenciar warning, error y critical por severidad real.
3. Priorizar mensajes de error accionables para depuración.

### Ejemplo
Entrada:
- Timeout al acceder a URL médica.

Salida:
- Reintento con backoff, log estructurado y continuidad del crawling.

## Skill 9: Modular Code Design

### Descripción
Estructura el sistema en módulos cohesivos y desacoplados para facilitar mantenimiento, pruebas y escalado.

### Cuándo usarla
1. Desde el inicio del proyecto.
2. En cada refactor significativo.
3. Al preparar evolución hacia recuperación híbrida y RAG.

### Pasos de ejecución
1. Dividir por capas: ingestion, processing, indexing, retrieval y storage.
2. Definir interfaces estables entre módulos.
3. Mantener una responsabilidad principal por archivo o clase.
4. Inyectar dependencias para facilitar pruebas y sustitución de componentes.
5. Separar configuración, lógica de negocio y acceso a datos.
6. Añadir pruebas unitarias por módulo y pruebas de integración de flujo.

### Buenas prácticas
1. Evitar acoplamiento circular y utilidades monolíticas.
2. Diseñar componentes reemplazables por contratos.
3. Documentar límites de módulo y supuestos de diseño.

### Ejemplo
Entrada:
- Necesidad de reemplazar indexador TF-IDF por BM25.

Salida:
- Sustitución del módulo de indexación sin impacto en crawling ni storage.

## Reglas Transversales para Todas las Skills
1. Toda skill debe ejecutarse con configuración externa versionada.
2. Toda etapa debe dejar trazabilidad de entrada, salida y versión de pipeline.
3. Toda modificación relevante debe incluir validación y pruebas mínimas.
4. Toda optimización debe justificarse con métricas reproducibles.
