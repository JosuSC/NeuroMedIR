"""
debug_corpus_gap.py — ¿Existe un buen doc de síntomas de diabetes en el corpus?
Ejecutar desde la raíz: python debug_corpus_gap.py
"""
import json
from pathlib import Path
from indexing.configs import settings as idx_settings
from retrieval.document_store import DocumentStore

doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)

# 1) Ver el contenido de los docs que el reranker eligió en debug_pipeline
print("=" * 70)
print("CONTENIDO DE LOS TOP DOCS RERANKEADOS (de tu debug previo)")
print("=" * 70)
for did in [1411, 792, 797, 791, 793]:
    doc = doc_store.get(did)
    if doc:
        title = doc.get("title", "?")
        content = doc.get("content", "")
        # ¿menciona síntomas clásicos?
        low = content.lower()
        sintomas = [s for s in ["poliuria", "polidipsia", "polifagia", "sed",
                                 "orinar", "visión borrosa", "fatiga", "cansancio",
                                 "pérdida de peso", "hambre"] if s in low]
        print(f"\n[doc_id={did}] {title}")
        print(f"  longitud: {len(content)} chars")
        print(f"  síntomas mencionados: {sintomas}")
        print(f"  primeros 200 chars: {content[:200]}")

# 2) Buscar en TODO el corpus docs cuyo título mencione 'síntomas' + diabetes
print("\n" + "=" * 70)
print("DOCS EN EL CORPUS CON 'sintoma' O 'diabetes' EN EL TÍTULO")
print("=" * 70)
count = 0
for did, doc in doc_store._store.items():
    title = doc.get("title", "").lower()
    if ("síntoma" in title or "sintoma" in title) and "diabet" in title:
        print(f"  [doc_id={did}] {doc.get('title')}")
        count += 1
print(f"\nTotal docs 'síntomas de diabetes' en título: {count}")

# 3) Docs que mencionan síntomas clásicos en el CONTENIDO (no solo título)
print("\n" + "=" * 70)
print("DOCS CON SÍNTOMAS CLÁSICOS DE DIABETES EN EL CONTENIDO")
print("=" * 70)
hits = []
for did, doc in doc_store._store.items():
    low = doc.get("content", "").lower()
    if "diabet" in low and "poliuria" in low and "polidipsia" in low:
        hits.append((did, doc.get("title", "?")))
for did, title in hits[:10]:
    print(f"  [doc_id={did}] {title}")
print(f"\nTotal docs con diabetes+poliuria+polidipsia en contenido: {len(hits)}")