"""
annotate_queries.py — Anotación semi-automática de test_queries.json.

Para cada query corre el retriever (top-15), muestra título + snippet
de cada candidato y te pide que marques cuáles son relevantes.

Uso:
    python annotate_queries.py
    python annotate_queries.py --k 15          # más candidatos por query
    python annotate_queries.py --resume        # salta queries ya anotadas
    python annotate_queries.py --query q05     # anota solo una query

Controles durante la anotación:
    1 3 5      → marcar docs 1, 3 y 5 como relevantes (por número de lista)
    0          → ninguno es relevante
    s          → saltar esta query (la deja como estaba)
    q          → guardar lo que hay y salir

Salida:
    evaluation/test_queries.json  (sobreescribe con los relevant rellenos)
    evaluation/test_queries.json.bak  (backup del original)
"""

import json
import shutil
import argparse
from pathlib import Path

from retrieval.retriever import Retriever

QUERIES_PATH = Path("evaluation/test_queries.json")
DEFAULT_K = 15


def load_queries(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queries(queries, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=4)
    print(f"\n✓ Guardado en {path}")


def annotate(queries, retriever: Retriever, k: int, resume: bool, only_query: str):
    total = len(queries)

    for i, q in enumerate(queries):
        qid = q["query_id"]

        # Filtros
        if only_query and qid != only_query:
            continue
        if resume and q["relevant"]:
            print(f"[{qid}] ya anotada ({len(q['relevant'])} relevantes) — saltando.")
            continue

        print("\n" + "=" * 72)
        print(f"  Query {i+1}/{total}  [{qid}]")
        print(f"  \"{q['query']}\"")
        print("=" * 72)

        # Recuperar candidatos
        try:
            results = retriever.retrieve(q["query"], top_k=k)
        except Exception as e:
            print(f"  ERROR en retrieval: {e}")
            continue

        if not results:
            print("  Sin resultados. Marcando como sin relevantes.")
            q["relevant"] = []
            continue

        # Mostrar candidatos numerados
        print()
        for idx, doc in enumerate(results, 1):
            title   = doc.get("title", "Sin título")
            snippet = doc.get("snippet", "")[:180].replace("\n", " ")
            score   = doc.get("score", 0.0)
            doc_id  = doc.get("doc_id")
            source  = doc.get("source", "")
            print(f"  [{idx:>2}] doc_id={doc_id}  score={score:.3f}  ({source})")
            print(f"       {title}")
            print(f"       {snippet}...")
            print()

        # Input del anotador
        while True:
            raw = input(
                "  ¿Cuáles son relevantes? "
                "(números separados por espacio, 0=ninguno, s=saltar, q=guardar+salir): "
            ).strip().lower()

            if raw == "q":
                return "quit"

            if raw == "s":
                print(f"  [{qid}] saltada.")
                break

            if raw == "0":
                q["relevant"] = []
                print(f"  [{qid}] marcada: sin relevantes.")
                break

            # Parsear números
            try:
                nums = [int(x) for x in raw.split()]
                valid = [n for n in nums if 1 <= n <= len(results)]
                invalid = [n for n in nums if n not in valid]

                if invalid:
                    print(f"  Números fuera de rango: {invalid}. Intenta de nuevo.")
                    continue

                doc_ids = [results[n - 1]["doc_id"] for n in valid]
                q["relevant"] = doc_ids
                print(f"  [{qid}] relevantes → doc_ids: {doc_ids}")
                break

            except ValueError:
                print("  Entrada inválida. Usa números separados por espacio.")

    return "done"


def main():
    parser = argparse.ArgumentParser(description="Anotar test_queries.json semi-automáticamente.")
    parser.add_argument("--k",      type=int, default=DEFAULT_K, help="Candidatos a mostrar por query")
    parser.add_argument("--resume", action="store_true",          help="Saltar queries ya anotadas")
    parser.add_argument("--query",  type=str, default="",         help="Anotar solo una query (ej: q05)")
    args = parser.parse_args()

    # Backup
    bak = QUERIES_PATH.with_suffix(".json.bak")
    shutil.copy(QUERIES_PATH, bak)
    print(f"Backup creado en {bak}")

    # Cargar queries
    queries = load_queries(QUERIES_PATH)
    print(f"Cargadas {len(queries)} queries desde {QUERIES_PATH}")

    # Cargar retriever
    print("Cargando retriever desde disco...")
    retriever = Retriever.from_disk()
    print("Retriever listo.\n")
    print("─" * 72)
    print("INSTRUCCIONES:")
    print("  - Escribe los NÚMEROS de la lista (no los doc_ids) de los docs relevantes")
    print("  - Un doc es relevante si contiene información útil para responder la query")
    print("  - Puedes marcar varios: '1 3 7'  o ninguno: '0'")
    print("─" * 72)

    # Anotar
    result = annotate(queries, retriever, args.k, args.resume, args.query)

    # Guardar siempre (incluso si se salió con 'q')
    save_queries(queries, QUERIES_PATH)

    if result == "quit":
        print("Salida anticipada. Progreso guardado.")
    else:
        # Resumen
        annotated = sum(1 for q in queries if q["relevant"] != [])
        empty     = sum(1 for q in queries if q["relevant"] == [])
        skipped   = sum(1 for q in queries if q["relevant"] == [] and result == "done")
        print(f"\nResumen:")
        print(f"  Queries con relevantes: {annotated}/{ len(queries)}")
        print(f"  Queries sin relevantes (0 marcado): {empty}")
        print(f"\nPróximo paso:")
        print(f"  python -m evaluation.run_eval --k 10")


if __name__ == "__main__":
    main()