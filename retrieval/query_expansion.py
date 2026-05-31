"""
query_expansion.py — Query expansion for NeuroMedIR hybrid retrieval.

Two complementary techniques applied sequentially:

    1. Synonym expansion (static dictionary)
       Maps common Spanish medical terms to their clinical equivalents.
       Applied first; always runs if enabled, no external dependency.

    2. Pseudo-Relevance Feedback (PRF)
       Fetches a small initial result set via BM25 only (no re-ranking),
       extracts the most representative terms with TF-IDF, and appends
       them to the lexical tokens for the real retrieval pass.
       Applied second; requires a Retriever reference at call time.

Usage (called from Retriever.retrieve):
    expander = QueryExpander()
    processed = expander.expand(processed, retriever=self)
    # processed["lexical_tokens"] and processed["semantic_text"] are now enriched

Design notes:
    - expand() returns the same dict shape as QueryProcessor.process() so the
      rest of the retrieval pipeline is untouched.
    - PRF calls search_bm25() + _enrich_results() directly on the retriever
      (no re-ranking, no embedding) to keep latency low.
    - All expansion terms are lowercased and deduplicated against the
      original tokens before appending.
"""

import logging
import math
from collections import Counter
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from retrieval.retriever import Retriever

from retrieval.configs import settings as ret_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Medical synonym dictionary (Spanish)
# ---------------------------------------------------------------------------
# Format: {term: [synonym1, synonym2, ...]}
# Keys are lowercase, stemmed-friendly short forms.
# Synonyms are added to BOTH lexical tokens and semantic text.
# ---------------------------------------------------------------------------

MEDICAL_SYNONYMS: Dict[str, List[str]] = {
    # Respiratory
    "tos": ["bronquitis", "infección respiratoria", "expectoración"],
    "asma": ["broncoespasmo", "disnea", "sibilancias"],
    "gripe": ["influenza", "fiebre", "virus gripal"],
    "neumonía": ["infección pulmonar", "consolidación pulmonar"],
    "bronquitis": ["inflamación bronquial", "tos productiva"],

    # Cardiovascular
    "infarto": ["infarto miocardio", "iam", "cardiopatía isquémica"],
    "hipertensión": ["presión alta", "hta", "tensión arterial elevada"],
    "arritmia": ["fibrilación auricular", "taquicardia", "bradicardia"],
    "angina": ["angina pecho", "dolor precordial", "isquemia coronaria"],

    # Metabolic / endocrine
    "diabetes": ["diabetes mellitus", "hiperglucemia", "resistencia insulina"],
    "obesidad": ["sobrepeso", "índice masa corporal", "imc elevado"],
    "tiroides": ["hipotiroidismo", "hipertiroidismo", "enfermedad tiroidea"],
    "colesterol": ["dislipidemia", "hipercolesterolemia", "ldl elevado"],

    # Neurological
    "cefalea": ["dolor de cabeza", "migraña", "jaqueca"],
    "migraña": ["cefalea pulsátil", "hemicránea", "dolor cabeza unilateral"],
    "epilepsia": ["convulsiones", "crisis epiléptica", "trastorno convulsivo"],
    "alzheimer": ["demencia", "deterioro cognitivo", "pérdida memoria"],
    "parkinson": ["temblor esencial", "enfermedad parkinson", "síndrome parkinsoniano"],
    "ictus": ["accidente cerebrovascular", "acv", "infarto cerebral", "apoplejía"],

    # Gastrointestinal
    "gastritis": ["inflamación gástrica", "úlcera péptica", "dispepsia"],
    "diarrea": ["gastroenteritis", "síndrome diarreico", "colitis"],
    "estreñimiento": ["constipación", "tránsito intestinal lento"],
    "reflujo": ["erge", "reflujo gastroesofágico", "pirosis"],
    "hígado": ["hepatitis", "cirrosis", "enfermedad hepática"],

    # Musculoskeletal
    "artritis": ["artritis reumatoide", "inflamación articular", "poliartritis"],
    "artrosis": ["osteoartritis", "degeneración articular", "desgaste cartílago"],
    "lumbalgia": ["dolor lumbar", "lumbago", "ciática"],
    "fractura": ["rotura ósea", "traumatismo óseo"],
    "osteoporosis": ["pérdida densidad ósea", "fragilidad ósea"],

    # Infectious disease
    "fiebre": ["hipertermia", "pirexia", "temperatura elevada"],
    "infección": ["proceso infeccioso", "sepsis", "bacteriemia"],
    "antibiótico": ["antimicrobiano", "antibacteriano", "tratamiento antibiótico"],
    "vacuna": ["inmunización", "vacunación", "profilaxis vacunal"],

    # Mental health
    "depresión": ["trastorno depresivo", "depresión mayor", "síndrome depresivo"],
    "ansiedad": ["trastorno ansioso", "crisis ansiedad", "estrés crónico"],
    "insomnio": ["trastorno sueño", "dificultad conciliar sueño"],
    "estrés": ["estrés crónico", "burnout", "síndrome de agotamiento"],

    # Dermatology
    "eccema": ["dermatitis", "dermatitis atópica", "eczema"],
    "psoriasis": ["enfermedad psoriásica", "placas psoriásicas"],
    "acné": ["acné vulgar", "comedones", "foliculitis"],

    # Oncology (general)
    "cáncer": ["tumor maligno", "neoplasia", "carcinoma"],
    "tumor": ["neoplasia", "masa tumoral", "lesión tumoral"],
    "quimioterapia": ["tratamiento oncológico", "citostáticos", "quimio"],

    # Pediatrics
    "fiebre niño": ["fiebre pediátrica", "hipertermia infantil"],
    "otitis": ["infección oído", "otitis media", "dolor oído"],

    # Women's health
    "menopausia": ["climaterio", "síndrome menopáusico", "perimenopausia"],
    "endometriosis": ["endometriosis pélvica", "tejido endometrial ectópico"],
}


class QueryExpander:
    """
    Enriches a processed query dict with additional terms via synonym
    lookup and pseudo-relevance feedback.

    Instantiated once and reused across queries (stateless between calls).
    """

    def __init__(
        self,
        use_synonyms: bool = None,
        use_prf: bool = None,
        prf_docs: int = None,
        prf_terms: int = None,
        prf_min_score: float = None,
    ):
        """
        Args:
            use_synonyms: Enable static synonym expansion.
                          Defaults to settings.EXPANSION_USE_SYNONYMS.
            use_prf:      Enable pseudo-relevance feedback.
                          Defaults to settings.EXPANSION_USE_PRF.
            prf_docs:     Number of top docs to analyse for PRF.
                          Defaults to settings.PRF_TOP_DOCS.
            prf_terms:    Number of TF-IDF terms to add per query.
                          Defaults to settings.PRF_TOP_TERMS.
            prf_min_score: Minimum TF-IDF score to include a term.
                          Defaults to settings.PRF_MIN_SCORE.
        """
        self.use_synonyms = use_synonyms if use_synonyms is not None else ret_settings.EXPANSION_USE_SYNONYMS
        self.use_prf = use_prf if use_prf is not None else ret_settings.EXPANSION_USE_PRF
        self.prf_docs = prf_docs or ret_settings.PRF_TOP_DOCS
        self.prf_terms = prf_terms or ret_settings.PRF_TOP_TERMS
        self.prf_min_score = prf_min_score if prf_min_score is not None else ret_settings.PRF_MIN_SCORE

        logger.info(
            f"QueryExpander ready — synonyms: {self.use_synonyms}, "
            f"PRF: {self.use_prf} (docs={self.prf_docs}, terms={self.prf_terms})"
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def expand(
        self,
        processed: Dict,
        retriever: Optional["Retriever"] = None,
    ) -> Dict:
        """
        Applies all enabled expansion techniques in order and returns
        an enriched copy of the processed query dict.

        Args:
            processed: Output of QueryProcessor.process() —
                       {"raw", "lexical_tokens", "semantic_text"}.
            retriever: Retriever instance needed for PRF. If None and
                       use_prf is True, PRF is silently skipped.

        Returns:
            Same dict shape with potentially longer lexical_tokens
            and a slightly extended semantic_text.
        """
        result = {
            "raw": processed["raw"],
            "lexical_tokens": list(processed["lexical_tokens"]),
            "semantic_text": processed["semantic_text"],
        }

        original_token_count = len(result["lexical_tokens"])

        if self.use_synonyms:
            result = self.expand_with_synonyms(result)

        if self.use_prf:
            if retriever is not None:
                result = self.expand_with_prf(result, retriever)
            else:
                logger.debug("PRF skipped: no retriever provided.")

        added = len(result["lexical_tokens"]) - original_token_count
        if added > 0:
            logger.debug(
                f"Query expansion: '{processed['raw']}' → +{added} tokens "
                f"(total: {len(result['lexical_tokens'])})"
            )

        return result

    def expand_with_synonyms(self, processed: Dict) -> Dict:
        """
        Stage 1: Adds medical synonyms for any term found in the
        static dictionary.

        Matching is case-insensitive. Only adds terms not already
        present in the token list (deduplication).

        Args:
            processed: Processed query dict.

        Returns:
            Enriched dict with synonym tokens appended.
        """
        raw_lower = processed["raw"].lower()
        existing_tokens = set(processed["lexical_tokens"])
        new_tokens: List[str] = []
        semantic_additions: List[str] = []

        for term, synonyms in MEDICAL_SYNONYMS.items():
            if term in raw_lower:
                for synonym in synonyms:
                    # Multi-word synonyms: add each word as a token
                    syn_tokens = synonym.lower().split()
                    for tok in syn_tokens:
                        if tok not in existing_tokens and tok not in new_tokens:
                            new_tokens.append(tok)
                    # Keep full phrase for semantic text (encoder handles phrases well)
                    if synonym not in processed["semantic_text"]:
                        semantic_additions.append(synonym)

        if new_tokens:
            expanded_tokens = processed["lexical_tokens"] + new_tokens
            expanded_semantic = processed["semantic_text"]
            if semantic_additions:
                expanded_semantic += " " + " ".join(semantic_additions)

            logger.debug(
                f"Synonym expansion: +{len(new_tokens)} tokens "
                f"for terms matching '{processed['raw']}'"
            )
            return {
                "raw": processed["raw"],
                "lexical_tokens": expanded_tokens,
                "semantic_text": expanded_semantic,
            }

        return processed

    def expand_with_prf(self, processed: Dict, retriever: "Retriever") -> Dict:
        """
        Stage 2: Pseudo-Relevance Feedback.

        Fetches top-N documents using BM25 only (fast, no embedding,
        no re-ranking), then scores all terms in those documents with
        TF-IDF and appends the highest-scoring ones that are not
        already in the query.

        Args:
            processed: Processed (and possibly synonym-expanded) query dict.
            retriever: Live Retriever instance used for the initial fetch.

        Returns:
            Enriched dict with PRF terms appended to lexical_tokens.
        """
        # Initial retrieval: BM25 only, no re-ranking, small top-k
        try:
            initial_results = retriever.search_bm25(
                processed["lexical_tokens"],
                top_k=self.prf_docs,
            )
        except Exception as exc:
            logger.warning(f"PRF initial retrieval failed: {exc}")
            return processed

        if not initial_results:
            logger.debug("PRF: no initial results, skipping.")
            return processed

        # Fetch document texts for the retrieved doc_ids
        doc_ids = [r["doc_id"] for r in initial_results]
        try:
            doc_texts_map = retriever._doc_store.get_texts(doc_ids)
        except Exception as exc:
            logger.warning(f"PRF doc fetch failed: {exc}")
            return processed

        doc_texts = [doc_texts_map.get(doc_id, "") for doc_id in doc_ids]
        doc_texts = [t for t in doc_texts if t]  # drop empties

        if not doc_texts:
            return processed

        # Score terms with TF-IDF across the small pseudo-relevant corpus
        prf_terms = self._extract_tfidf_terms(
            doc_texts=doc_texts,
            query_tokens=set(processed["lexical_tokens"]),
            top_k=self.prf_terms,
            min_score=self.prf_min_score,
        )

        if not prf_terms:
            return processed

        logger.debug(
            f"PRF: top terms from {len(doc_texts)} docs → {prf_terms}"
        )

        return {
            "raw": processed["raw"],
            "lexical_tokens": processed["lexical_tokens"] + prf_terms,
            "semantic_text": processed["semantic_text"],
        }

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _extract_tfidf_terms(
        self,
        doc_texts: List[str],
        query_tokens: set,
        top_k: int,
        min_score: float,
    ) -> List[str]:
        """
        Computes TF-IDF scores for all terms in the given documents
        and returns the top_k terms above min_score that are not in
        the original query.

        TF is computed per-document (normalized by doc length).
        IDF uses the small pseudo-relevant corpus (log-smoothed).
        Final score: mean(TF) * IDF across all docs containing the term.

        Args:
            doc_texts: List of document text strings.
            query_tokens: Set of original query tokens to exclude.
            top_k: Maximum number of terms to return.
            min_score: Minimum TF-IDF score threshold.

        Returns:
            List of expansion term strings, sorted by score descending.
        """
        N = len(doc_texts)
        if N == 0:
            return []

        # Tokenize each document (simple whitespace + lowercase)
        tokenized_docs = [
            self._tokenize(text) for text in doc_texts
        ]

        # Document frequency: how many docs contain each term
        df: Counter = Counter()
        for tokens in tokenized_docs:
            df.update(set(tokens))

        # Compute mean TF * IDF for each candidate term
        scores: Dict[str, float] = {}
        for tokens in tokenized_docs:
            if not tokens:
                continue
            tf_doc = Counter(tokens)
            doc_len = len(tokens)
            for term, count in tf_doc.items():
                if term in query_tokens:
                    continue
                if len(term) < 3:  # skip very short tokens
                    continue
                tf = count / doc_len
                idf = math.log((N + 1) / (df[term] + 1)) + 1.0  # smooth IDF
                score = tf * idf
                # Accumulate (will average later)
                scores[term] = scores.get(term, 0.0) + score

        # Average over number of docs containing each term
        for term in scores:
            scores[term] /= df[term]

        # Filter by min_score and return top_k
        filtered = [
            (term, score)
            for term, score in scores.items()
            if score >= min_score
        ]
        filtered.sort(key=lambda x: x[1], reverse=True)

        return [term for term, _ in filtered[:top_k]]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Minimal tokenizer for PRF term extraction.
        Lowercases and splits on non-alphanumeric characters.
        Kept simple intentionally — PRF only needs rough term frequency.
        """
        import re
        tokens = re.findall(r"[a-záéíóúüñ\w]{3,}", text.lower())
        return tokens