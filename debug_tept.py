"""
debug_tept.py — ¿Qué recupera para TEPT y por qué no citó fuentes?
Ejecutar desde la raíz: python debug_tept.py
"""
import logging
logging.basicConfig(level=logging.WARNING)  # menos ruido

from retrieval.retriever import Retriever

retriever = Retriever.from_disk()

query = "cuales son los sintomas del trastorno de estres postraumatico"
results = retriever.retrieve(query, top_k=5, preferred_lang="es")

print("\n" + "=" * 70)
print(f"RETRIEVAL para TEPT")
print("=" * 70)
for r in results:
    print(f"  doc_id={r.get('doc_id')}  score={r.get('score'):.4f}")
    print(f"     título: {r.get('title', '?')[:75]}")
    print()

# Simular el filtro del Fix B
FLOOR = 1.0
relevant = [r for r in results if r.get("score", 0) >= FLOOR]
print("=" * 70)
print(f"Docs que superan RAG_RELEVANCE_FLOOR={FLOOR}: {len(relevant)}")
for r in relevant:
    print(f"  doc_id={r.get('doc_id')} score={r.get('score'):.4f} — {r.get('title','?')[:60]}")
print()

# ¿Existe en el corpus un buen doc de TEPT?
print("=" * 70)
print("BÚSQUEDA EN CORPUS: docs con 'postraumático' o 'estrés postrauma'")
print("=" * 70)
ds = retriever._doc_store
hits = []
for did, doc in ds._store.items():
    blob = (doc.get("title", "") + " " + doc.get("content", "")).lower()
    if "postraum" in blob or "post-traum" in blob or "tept" in blob:
        hits.append((did, doc.get("title", "?")))
for did, title in hits[:10]:
    print(f"  doc_id={did}: {title[:70]}")
print(f"\nTotal docs sobre TEPT en corpus: {len(hits)}")