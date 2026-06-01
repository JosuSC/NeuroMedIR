"""
debug_sarna.py — ¿Por qué no se disparó la expansión web?
Ejecutar desde la raíz: python debug_sarna.py
"""
import logging
logging.basicConfig(level=logging.INFO)

from retrieval.retriever import Retriever

retriever = Retriever.from_disk()

query = "síntomas de la sarna"
results = retriever.retrieve(query, top_k=5, preferred_lang="es")

print("\n" + "=" * 70)
print(f"RETRIEVAL para: '{query}'")
print("=" * 70)
print(f"Número de resultados: {len(results)}")
print()
for r in results:
    print(f"  doc_id={r.get('doc_id')}  score={r.get('score'):.4f}  "
          f"ranking_score={r.get('ranking_score', 'N/A')}")
    print(f"     título: {r.get('title', '?')[:70]}")
    print()

# Simular la decisión de _should_expand con los valores nuevos
MIN_RESULTS = 2
THRESHOLD = 0.5

print("=" * 70)
print("DECISIÓN _should_expand")
print("=" * 70)
if not results:
    print("  → results vacío → EXPANDIR")
elif len(results) < MIN_RESULTS:
    print(f"  → len={len(results)} < {MIN_RESULTS} → EXPANDIR")
else:
    top = results[0].get("score", 0.0)
    decision = "EXPANDIR" if top < THRESHOLD else "NO EXPANDIR"
    print(f"  → len={len(results)} >= {MIN_RESULTS}")
    print(f"  → top_score={top:.4f}  vs  threshold={THRESHOLD}")
    print(f"  → {decision}")

print(f"\nNota: el campo usado por _should_expand es 'score' (logit del")
print(f"cross-encoder), NO 'ranking_score'. Si top_score es alto pero los")
print(f"docs son irrelevantes a sarna, el umbral necesita recalibrarse.")