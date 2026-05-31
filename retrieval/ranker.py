"""
ranker.py — Multi-factor ranking for NeuroMedIR.

Applies a weighted combination of 5 signals to re-order results
after cross-encoder re-ranking (Stage 3 of the retrieval pipeline):

    score_final = w_rel   * relevance
                + w_src   * source_reliability
                + w_fresh * freshness
                + w_lang  * language_match
                + w_div   * source_diversity

All individual factors are normalized to [0, 1] before weighting.
The final score replaces the cross-encoder score in the result dict
so downstream code (enrichment, API response) needs no changes.
"""

import logging
import math
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlparse

from retrieval.configs import settings as ret_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source reliability weights
# Static dictionary: domain → reliability score [0.0, 1.0]
# Based on whether the source is a government/academic/major health org.
# Domains not listed fall back to RANKER_DEFAULT_SOURCE_WEIGHT.
# ---------------------------------------------------------------------------

SOURCE_RELIABILITY: Dict[str, float] = {
    # Organismos internacionales / gubernamentales
    "who.int":              1.00,
    "paho.org":             1.00,
    "nih.gov":              1.00,
    "medlineplus.gov":      1.00,
    "cdc.gov":              1.00,
    "fda.gov":              0.95,
    "cancer.gov":           0.98,
    "nhlbi.nih.gov":        0.98,

    # Ministerios y entidades nacionales de salud
    "minsalud.gov.co":      0.95,
    "salud.gob.mx":         0.95,
    "minsal.cl":            0.95,
    "sld.cu":               0.90,

    # Portales médicos de referencia
    "mayoclinic.org":       0.95,
    "clevelandclinic.org":  0.93,
    "medscape.com":         0.90,
    "webmd.com":            0.80,
    "healthline.com":       0.78,
    "medicalnewstoday.com": 0.75,

    # Portales en español de referencia
    "msdmanuals.com":       0.92,
    "cun.es":               0.90,   # Clínica Universidad de Navarra
    "topdoctors.es":        0.78,
    "saludemia.com":        0.72,
    "elsevier.es":          0.88,
    "scielo.org":           0.85,
    "kidshealth.org":       0.85,
    "familydoctor.org":     0.82,
    "geosalud.com":         0.70,
}


class MultiFactorRanker:
    """
    Re-orders retrieval results using a weighted multi-factor score.

    Designed to be applied after cross-encoder re-ranking — it refines
    the final order without discarding any results.
    """

    def __init__(
        self,
        w_relevance:   float = None,
        w_source:      float = None,
        w_freshness:   float = None,
        w_language:    float = None,
        w_diversity:   float = None,
        max_per_source: int  = None,
    ):
        """
        Args:
            w_relevance:    Weight for cross-encoder relevance score.
            w_source:       Weight for source reliability.
            w_freshness:    Weight for document freshness.
            w_language:     Weight for language match with user query.
            w_diversity:    Weight for source diversity penalty.
            max_per_source: Max docs from one domain before penalty kicks in.
        """
        self.w_relevance   = w_relevance   if w_relevance   is not None else ret_settings.RANKER_W_RELEVANCE
        self.w_source      = w_source      if w_source      is not None else ret_settings.RANKER_W_SOURCE
        self.w_freshness   = w_freshness   if w_freshness   is not None else ret_settings.RANKER_W_FRESHNESS
        self.w_language    = w_language    if w_language    is not None else ret_settings.RANKER_W_LANGUAGE
        self.w_diversity   = w_diversity   if w_diversity   is not None else ret_settings.RANKER_W_DIVERSITY
        self.max_per_source = max_per_source if max_per_source is not None else ret_settings.RANKER_MAX_PER_SOURCE

        total = self.w_relevance + self.w_source + self.w_freshness + self.w_language + self.w_diversity
        if abs(total - 1.0) > 1e-6:
            logger.warning(f"Ranker weights sum to {total:.4f}, not 1.0. Scores will not be in [0,1].")

        logger.info(
            f"MultiFactorRanker ready — "
            f"rel={self.w_relevance}, src={self.w_source}, "
            f"fresh={self.w_freshness}, lang={self.w_language}, "
            f"div={self.w_diversity}, max_per_source={self.max_per_source}"
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def rerank(
        self,
        results: List[Dict],
        preferred_lang: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Applies multi-factor scoring to a list of enriched results and
        returns them sorted by final score descending.

        Must be called AFTER _enrich_results() so that each result dict
        already contains: score, title, snippet, source, url, category.
        The doc metadata must also include 'crawled_at' (ISO string) for
        freshness scoring — missing dates fall back to a neutral score.

        Args:
            results:        Enriched result dicts from Retriever._enrich_results().
            preferred_lang: ISO language code of the user query ('es' or 'en').
                            If None, language factor is neutral (0.5) for all docs.
            now:            Reference datetime for freshness (defaults to UTC now).
                            Inject in tests to get deterministic results.

        Returns:
            Same list re-sorted by multi-factor score. Each dict gains
            a 'ranking_score' key with the final composite score.
        """
        if not results:
            return results

        now = now or datetime.now(timezone.utc)

        # Normalize relevance scores across the result set to [0, 1]
        raw_scores = [r.get("score", 0.0) for r in results]
        norm_relevance = _minmax_normalize(raw_scores)

        source_counts: Dict[str, int] = {}
        scored = []

        for idx, result in enumerate(results):
            rel_score   = norm_relevance[idx]
            src_score   = self._source_score(result)
            fresh_score = self._freshness_score(result, now)
            lang_score  = self._language_score(result, preferred_lang)
            div_score   = self._diversity_score(result, source_counts)

            # Update source counter AFTER computing diversity score for this doc
            domain = _extract_domain(result.get("url", ""))
            source_counts[domain] = source_counts.get(domain, 0) + 1

            final = (
                self.w_relevance * rel_score
                + self.w_source   * src_score
                + self.w_freshness * fresh_score
                + self.w_language  * lang_score
                + self.w_diversity * div_score
            )

            entry = dict(result)
            entry["ranking_score"] = round(final, 6)
            entry["_factors"] = {
                "relevance":  round(rel_score,   4),
                "source":     round(src_score,   4),
                "freshness":  round(fresh_score, 4),
                "language":   round(lang_score,  4),
                "diversity":  round(div_score,   4),
            }
            scored.append(entry)

        scored.sort(key=lambda x: x["ranking_score"], reverse=True)

        # Re-assign rank after re-ordering
        for new_rank, entry in enumerate(scored, start=1):
            entry["rank"] = new_rank

        logger.debug(
            f"MultiFactorRanker: re-ordered {len(scored)} results "
            f"(lang={preferred_lang})"
        )
        return scored

    # -----------------------------------------------------------------------
    # Individual factor scorers — all return float in [0, 1]
    # -----------------------------------------------------------------------

    def _source_score(self, result: Dict) -> float:
        """
        Returns the reliability score for the document's source domain.
        Unknown domains return the configured default weight.
        """
        url = result.get("url", "")
        domain = _extract_domain(url)
        return SOURCE_RELIABILITY.get(domain, ret_settings.RANKER_DEFAULT_SOURCE_WEIGHT)

    def _freshness_score(self, result: Dict, now: datetime) -> float:
        """
        Returns a freshness score based on how recently the document
        was crawled. Uses exponential decay with a configurable half-life.

        score = exp(-λ * age_days)  where λ = ln(2) / half_life_days

        A doc crawled today → 1.0. A doc at half-life → 0.5.
        Missing crawl date → neutral score (0.5).
        """
        crawled_at = result.get("crawled_at") or result.get("date", "")
        if not crawled_at:
            return 0.5

        try:
            if isinstance(crawled_at, str):
                # Handle both 'Z' suffix and '+00:00'
                crawled_at = crawled_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(crawled_at)
            else:
                dt = crawled_at

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            age_days = max((now - dt).total_seconds() / 86400, 0)
            half_life = ret_settings.RANKER_FRESHNESS_HALF_LIFE_DAYS
            lam = math.log(2) / half_life
            return math.exp(-lam * age_days)

        except (ValueError, TypeError):
            return 0.5

    def _language_score(self, result: Dict, preferred_lang: Optional[str]) -> float:
        """
        Returns 1.0 if the document language matches the preferred language,
        0.3 if it doesn't match, 0.5 if either is unknown.
        """
        if not preferred_lang:
            return 0.5

        doc_lang = result.get("lang") or result.get("language", "")
        if not doc_lang:
            return 0.5

        return 1.0 if doc_lang.lower().startswith(preferred_lang.lower()) else 0.3

    def _diversity_score(self, result: Dict, source_counts: Dict[str, int]) -> float:
        """
        Penalizes documents from domains already heavily represented
        in the ranked list so far.

        First max_per_source docs from a domain → 1.0 (no penalty).
        Each additional doc → score halved.

        score = 1.0                          if count < max_per_source
        score = 0.5 ^ (count - max + 1)     otherwise
        """
        domain = _extract_domain(result.get("url", ""))
        count = source_counts.get(domain, 0)  # count BEFORE this doc is added

        if count < self.max_per_source:
            return 1.0

        excess = count - self.max_per_source + 1
        return 0.5 ** excess


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> str:
    """Extracts the registered domain from a URL string."""
    if not url:
        return ""
    try:
        hostname = urlparse(url).hostname or ""
        # Strip 'www.' prefix
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def _minmax_normalize(values: List[float]) -> List[float]:
    """Min-max normalizes a list of floats to [0, 1]."""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    span = max_v - min_v
    if span < 1e-12:
        return [1.0] * len(values)
    return [(v - min_v) / span for v in values]