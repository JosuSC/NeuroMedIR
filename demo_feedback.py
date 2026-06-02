#!/usr/bin/env python3
"""
demo_feedback.py — Demostración del módulo de retroalimentación por relevancia (Rocchio).

Ejecuta tres pasos en secuencia y muestra los rankings en consola:

  PASO 1 ─ Ranking inicial         (POST /api/query)
  PASO 2 ─ Ranking con Rocchio     (POST /api/feedback)
             El documento en --relevant-rank sube; el de --irrelevant-rank baja.
  PASO 3 ─ Ranking restaurado      (POST /api/query de nuevo)
             Confirma que el cambio NO es permanente.

Uso rápido:
    python demo_feedback.py
    python demo_feedback.py -q "síntomas de la diabetes tipo 2"
    python demo_feedback.py -q "tratamiento del asma" --relevant-rank 2 --irrelevant-rank 1
"""

import sys
import argparse
import requests

# ─── ANSI colors ────────────────────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
C  = "\033[96m"   # cyan
R  = "\033[91m"   # red
W  = "\033[97m"   # white
B  = "\033[1m"    # bold
DIM = "\033[2m"   # dim
RST = "\033[0m"   # reset


# ─── Helpers HTTP ───────────────────────────────────────────────────────────

def _get(results: list, rank: int) -> dict | None:
    """Devuelve el resultado cuyo campo 'rank' coincide, o el de esa posición."""
    # El endpoint /api/query no devuelve 'rank', así que usamos posición
    by_rank = [r for r in results if r.get("rank") == rank]
    if by_rank:
        return by_rank[0]
    if 1 <= rank <= len(results):
        return results[rank - 1]
    return None


def do_query(query: str, base_url: str) -> list:
    """POST /api/query — retrieval normal sin feedback."""
    resp = requests.post(
        f"{base_url}/api/query",
        json={"query": query},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def do_feedback(query: str, feedback_map: dict[int, bool],
                top_k: int, base_url: str) -> list:
    """POST /api/feedback — retrieval con ajuste Rocchio."""
    payload = {
        "query": query,
        "results": [
            {"doc_id": doc_id, "relevant": rel}
            for doc_id, rel in feedback_map.items()
        ],
        "top_k": top_k,
    }
    resp = requests.post(
        f"{base_url}/api/feedback",
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


# ─── Visualización ──────────────────────────────────────────────────────────

def print_header(title: str) -> None:
    bar = "─" * 62
    print(f"\n{B}{C}{bar}{RST}")
    print(f"{B}{C}  {title}{RST}")
    print(f"{C}{bar}{RST}")


def print_results(results: list, highlight: set[int] = None,
                  dim_docs: set[int] = None) -> None:
    highlight = highlight or set()
    dim_docs  = dim_docs  or set()

    for i, r in enumerate(results[:5], start=1):
        doc_id = r.get("doc_id", "?")
        # rank puede venir explícito (feedback) o inferirse por posición (query)
        rank   = r.get("rank", i)
        score  = r.get("score", 0.0)
        title  = (r.get("title") or "Sin título")[:56]
        source = (r.get("source") or "")[:30]

        if doc_id in highlight:
            col    = G
            marker = f"  {G}{B}◄ MARCADO RELEVANTE{RST}"
        elif doc_id in dim_docs:
            col    = R
            marker = f"  {R}◄ MARCADO NO RELEVANTE{RST}"
        else:
            col    = W
            marker = ""

        print(f"  {col}{B}#{rank}{RST}  "
              f"{DIM}doc_id={doc_id}{RST}  "
              f"{col}score={score:.4f}{RST}{marker}")
        print(f"       {col}{title}{RST}")
        print(f"       {DIM}{source}{RST}")
        print()


# ─── Lógica principal ────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo retroalimentación Rocchio — NeuroMedIR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-q", "--query",
        default="síntomas de la diabetes tipo 2",
        help="Consulta médica a usar en la demo (default: síntomas diabetes)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="URL base del backend (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--relevant-rank",
        type=int, default=2,
        help="Rank del doc a marcar RELEVANTE en el paso 2 (default: 2)",
    )
    parser.add_argument(
        "--irrelevant-rank",
        type=int, default=1,
        help="Rank del doc a marcar NO RELEVANTE en el paso 2 (default: 1)",
    )
    parser.add_argument(
        "--top-k",
        type=int, default=5,
        help="Número de resultados a pedir (default: 5)",
    )
    args = parser.parse_args()

    print(f"\n{B}{'═'*62}{RST}")
    print(f"{B}  NeuroMedIR — Retroalimentación por Relevancia (Rocchio){RST}")
    print(f"{B}  α=1.0  β=0.75  γ=0.25{RST}")
    print(f"{B}{'═'*62}{RST}")
    print(f"\n  Consulta : {Y}{B}{args.query}{RST}")
    print(f"  Backend  : {DIM}{args.base_url}{RST}")

    # ── PASO 1: ranking inicial ──────────────────────────────────────────────
    print_header("PASO 1 — Ranking inicial  (POST /api/query)")
    print(f"  {DIM}Llamando a {args.base_url}/api/query ...{RST}\n")

    try:
        initial = do_query(args.query, args.base_url)
    except requests.exceptions.ConnectionError:
        print(f"\n  {R}✗ No se pudo conectar con el backend.{RST}")
        print(f"  {DIM}Verifica que el servidor esté corriendo en {args.base_url}{RST}\n")
        sys.exit(1)
    except Exception as exc:
        print(f"\n  {R}✗ Error: {exc}{RST}\n")
        sys.exit(1)

    if not initial:
        print(f"  {R}✗ Sin resultados. ¿Están cargados los índices?{RST}\n")
        sys.exit(1)

    print_results(initial)

    # Identificar docs por rank
    rel_doc   = _get(initial, args.relevant_rank)
    irrel_doc = _get(initial, args.irrelevant_rank)

    if rel_doc is None:
        print(f"  {R}✗ No existe un resultado con rank={args.relevant_rank}.{RST}\n")
        sys.exit(1)

    rel_id    = rel_doc["doc_id"]
    rel_title = (rel_doc.get("title") or "")[:50]
    irrel_id  = irrel_doc["doc_id"] if irrel_doc else None

    # ── PASO 2: aplicar Rocchio ──────────────────────────────────────────────
    print_header("PASO 2 — Aplicar Rocchio  (POST /api/feedback)")
    print(f"  {G}{B}RELEVANTE    {RST}: doc_id={rel_id}   rank original=#{args.relevant_rank}")
    print(f"               {DIM}\"{rel_title}\"{RST}")
    if irrel_id is not None:
        irrel_title = (irrel_doc.get("title") or "")[:50]
        print(f"  {R}{B}NO RELEVANTE {RST}: doc_id={irrel_id}   rank original=#{args.irrelevant_rank}")
        print(f"               {DIM}\"{irrel_title}\"{RST}")
    print(f"\n  {DIM}Llamando a {args.base_url}/api/feedback ...{RST}\n")

    feedback_map: dict[int, bool] = {rel_id: True}
    if irrel_id is not None:
        feedback_map[irrel_id] = False

    try:
        reranked = do_feedback(
            args.query, feedback_map, args.top_k, args.base_url
        )
    except Exception as exc:
        print(f"  {R}✗ Error en /api/feedback: {exc}{RST}\n")
        sys.exit(1)

    print_results(
        reranked,
        highlight={rel_id},
        dim_docs={irrel_id} if irrel_id else set(),
    )

    # Verificar si el doc relevante subió
    new_rank = next(
        (r.get("rank", i + 1) for i, r in enumerate(reranked)
         if r.get("doc_id") == rel_id),
        args.relevant_rank,
    )
    if new_rank < args.relevant_rank:
        print(f"  {G}{B}✓ El documento marcado como relevante subió: "
              f"#{args.relevant_rank} → #{new_rank}{RST}")
    elif new_rank == args.relevant_rank:
        print(f"  {Y}ℹ  El documento está en el mismo rank #{new_rank} "
              f"(la consulta ya era bastante precisa).{RST}")
    else:
        print(f"  {Y}ℹ  Rank nuevo: #{new_rank} (el ajuste vectorial puede "
              f"haber favorecido otros documentos aún más cercanos).{RST}")

    # ── PASO 3: consulta normal — sin cambios ────────────────────────────────
    print_header("PASO 3 — Sin feedback  (POST /api/query)  — cambio NO permanente")
    print(f"  {DIM}Llamando a {args.base_url}/api/query de nuevo ...{RST}\n")

    try:
        restored = do_query(args.query, args.base_url)
    except Exception as exc:
        print(f"  {R}✗ Error: {exc}{RST}\n")
        sys.exit(1)

    print_results(restored)

    # Comparar posición del doc relevante
    restored_rank = next(
        (i + 1 for i, r in enumerate(restored) if r.get("doc_id") == rel_id),
        None,
    )
    if restored_rank is not None and restored_rank == args.relevant_rank:
        print(f"  {G}{B}✓ Ranking restaurado:{RST} doc_id={rel_id} "
              f"vuelve a #{restored_rank} (igual que el inicial).")
        print(f"  {DIM}→ El ajuste Rocchio no modificó los índices: "
              f"es efímero por diseño.{RST}")
    elif restored_rank is not None:
        print(f"  {Y}ℹ  doc_id={rel_id}: inicial=#{args.relevant_rank}, "
              f"restaurado=#{restored_rank} "
              f"(posible variación por query expansion).{RST}")
    else:
        print(f"  {Y}ℹ  doc_id={rel_id} no aparece en el top-{args.top_k} restaurado.{RST}")

    print(f"\n{B}{'═'*62}{RST}")
    print(f"{B}  Demostración completada.{RST}")
    print(f"{B}{'═'*62}{RST}\n")


if __name__ == "__main__":
    main()