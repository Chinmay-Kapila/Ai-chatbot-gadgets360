"""
Ranking + Filtering + Deduplication stage.

Sits between raw API retrieval (Products / Reviews / News clients) and
the Prompt Builder / card assembly in the orchestrator. Its job is to
turn a possibly noisy, possibly redundant list of upstream results into
a small, deduplicated, relevance-ranked list — so Gemini (and the
frontend) never sees unrelated products or duplicate articles.

Scoring combines:
  - keyword overlap between the parsed query and each candidate
  - exact / fuzzy product-name (or article-title) matching
  - entity matching (phone/laptop/tv/... vs the candidate's category)
  - intent-aware boosts (named comparison items, budget fit, priority
    match, rating, recency)

Selection is data-driven rather than intent-hardcoded: if one candidate
clearly dominates the score distribution (a specific, named product or
article), only that one is kept — matching "if only one highly relevant
result exists, answer only from that result." Otherwise, the ranked
top-k is returned as a normal list (e.g. a 5-phone recommendation set,
or a handful of today's news headlines, where no single item should
crowd out the rest).
"""

import difflib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.models.schemas import ParsedQuery
from app.utils.helpers import normalize_text
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Tunable defaults; call sites may override top_k explicitly.
DEFAULT_PRODUCT_TOP_K = 5
DEFAULT_ARTICLE_TOP_K = 3

# A candidate is treated as "the one clear answer" (collapsing the result
# set to just that item) when its score is at least this many times the
# runner-up's score, and clears an absolute floor so two near-zero scores
# don't trigger a false collapse.
DOMINANCE_RATIO = 1.8
DOMINANCE_MIN_SCORE = 1.0

# Minimal English stopword set for tokenizing free-text query strings into
# meaningful keywords. Only needs to strip common noise words from
# queries like "give me the latest ... review" or "top phones under ...".
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "in",
    "on", "for", "to", "and", "or", "with", "about", "give", "me", "latest",
    "top", "best", "show", "tell", "what", "which", "how", "much", "many",
    "please", "i", "want", "need", "review", "reviews", "phone", "phones",
    "under", "price", "today", "current", "news", "compare", "comparison",
    "vs", "versus", "buy", "buying", "guide", "recommend", "suggest",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: Optional[str]) -> List[str]:
    """Lowercase word/number tokens, dropping anything shorter than 2 chars."""
    if not text:
        return []
    return [t for t in _WORD_RE.findall(text.lower()) if len(t) >= 2]


def _meaningful_tokens(text: Optional[str]) -> List[str]:
    """Tokenize and strip common stopwords, leaving the distinctive terms."""
    return [t for t in _tokenize(text) if t not in _STOPWORDS]


def _normalize(text: Optional[str]) -> str:
    return normalize_text(text) if text else ""


def _build_query_tokens(parsed: ParsedQuery) -> List[str]:
    """Collect every distinctive token the user's query implies."""
    parts = [parsed.query_text or ""]
    parts.extend(parsed.keywords or [])
    if parsed.brand:
        parts.append(parsed.brand)
    parts.extend(parsed.compare_items or [])

    tokens: List[str] = []
    for part in parts:
        tokens.extend(_meaningful_tokens(part))

    seen = set()
    unique: List[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _keyword_overlap_score(query_tokens: List[str], haystack: str) -> float:
    """Fraction of query tokens found in the candidate's text (0..1)."""
    if not query_tokens:
        return 0.0
    haystack_tokens = set(_tokenize(haystack))
    if not haystack_tokens:
        return 0.0
    hits = sum(1 for t in query_tokens if t in haystack_tokens)
    return hits / len(query_tokens)


def _fuzzy_score(a: Optional[str], b: Optional[str]) -> float:
    """Character-level similarity ratio (0..1) via difflib."""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _exact_phrase_boost(query_text: Optional[str], candidate_text: Optional[str]) -> float:
    """1.0 if one string contains the other (after normalization), else 0."""
    q, c = _normalize(query_text), _normalize(candidate_text)
    if not q or not c:
        return 0.0
    return 1.0 if (q in c or c in q) else 0.0


def _recency_score(published_at: Optional[str]) -> float:
    """
    Small boost (0..1) favoring more recent items, used as a tiebreaker
    for "latest ..." style queries where keyword signal is otherwise flat.
    """
    if not published_at:
        return 0.0
    parsed_date = None
    for candidate in (published_at, published_at.replace("Z", "+00:00")):
        try:
            parsed_date = datetime.fromisoformat(candidate)
            break
        except (TypeError, ValueError):
            continue
    if parsed_date is None:
        return 0.0
    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
    days_ago = (datetime.now(timezone.utc) - parsed_date).days
    return max(0.0, 1.0 - min(days_ago, 365) / 365.0)


@dataclass
class ScoredItem:
    item: Dict[str, Any]
    score: float


def _deduplicate(scored: List[ScoredItem], key_fn: Callable[[Dict[str, Any]], str]) -> List[ScoredItem]:
    """Drop items whose dedup key (e.g. normalized title) has been seen."""
    seen = set()
    result: List[ScoredItem] = []
    for s in scored:
        key = key_fn(s.item) or id(s.item)
        if key in seen:
            continue
        seen.add(key)
        result.append(s)
    return result


def _select_relevant(scored: List[ScoredItem], top_k: int) -> List[ScoredItem]:
    """
    Data-driven selection: if the top result clearly dominates the score
    distribution, it's treated as a specific, single-target match and
    returned alone. Otherwise the ranked top-k is returned as a normal
    list (recommendations, news roundups, comparisons, etc.).
    """
    if not scored:
        return []

    top_score = scored[0].score
    second_score = scored[1].score if len(scored) > 1 else 0.0

    is_dominant = top_score >= DOMINANCE_MIN_SCORE and (
        second_score <= 0 or top_score >= second_score * DOMINANCE_RATIO
    )

    if is_dominant:
        return [scored[0]]

    return scored[:top_k]


# ---------------------------------------------------------------------------
# Product scoring + ranking
# ---------------------------------------------------------------------------

def _score_product(product: Dict[str, Any], parsed: ParsedQuery, query_tokens: List[str]) -> float:
    name = product.get("name") or ""
    brand = product.get("brand") or ""
    entity = (product.get("entity") or product.get("category") or "").lower()
    specs = product.get("key_specs") or {}
    specs_text = " ".join(f"{k} {v}" for k, v in specs.items())
    haystack = f"{name} {brand} {specs_text}"

    score = 0.0
    score += 2.0 * _keyword_overlap_score(query_tokens, haystack)
    score += 1.5 * _exact_phrase_boost(parsed.query_text, name)
    score += 1.0 * _fuzzy_score(" ".join(query_tokens), name)

    # Named comparison items (comparison intent) get a strong boost.
    for item_name in parsed.compare_items or []:
        if not item_name:
            continue
        if item_name.lower() in name.lower() or name.lower() in item_name.lower():
            score += 2.5
        else:
            score += 0.5 * _fuzzy_score(item_name, name)

    # Entity match (phone/laptop/tablet/...).
    if parsed.entity and parsed.entity != "none" and parsed.entity == entity:
        score += 1.0

    # Brand match.
    if parsed.brand and brand and parsed.brand.lower() == brand.lower():
        score += 0.75

    # Budget fit: reward in-budget, penalize (not exclude) over-budget —
    # the products client already applies budget as a hard filter
    # upstream, this just re-affirms it in the ranking signal.
    price = product.get("price")
    if parsed.budget and price is not None:
        score += 0.5 if price <= parsed.budget else -1.5

    # Priority match (e.g. "camera", "battery") against the spec sheet.
    if parsed.priority:
        priority_tokens = _meaningful_tokens(parsed.priority)
        if priority_tokens and _keyword_overlap_score(priority_tokens, specs_text) > 0:
            score += 0.75

    # Rating as a small continuous tiebreaker.
    rating = product.get("rating")
    if rating:
        try:
            score += min(float(rating), 5.0) / 10.0
        except (TypeError, ValueError):
            pass

    return score


def _filter_by_entity(products: List[Dict[str, Any]], parsed: ParsedQuery) -> List[Dict[str, Any]]:
    """
    Hard-exclude candidates whose entity/category clearly doesn't match
    the parsed query's entity (e.g. a laptop showing up in a phone
    recommendation). Upstream clients already filter by entity, but this
    makes "remove unrelated products" a guarantee of the ranking stage
    itself, not just something we hope the API did correctly. Items with
    no entity/category info at all are kept (can't judge them), and if
    filtering would remove everything, the original list is returned
    unchanged rather than producing an empty result.
    """
    if not parsed.entity or parsed.entity == "none":
        return products

    filtered = [
        p for p in products
        if not (p.get("entity") or p.get("category"))
        or (p.get("entity") or p.get("category") or "").lower() == parsed.entity
    ]
    return filtered if filtered else products


def rank_products(
    products: List[Dict[str, Any]],
    parsed: ParsedQuery,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Rank, deduplicate, and filter products down to the most relevant top-k."""
    if not products:
        return []

    products = _filter_by_entity(products, parsed)

    resolved_top_k = top_k or min(parsed.count or DEFAULT_PRODUCT_TOP_K, DEFAULT_PRODUCT_TOP_K)
    query_tokens = _build_query_tokens(parsed)

    scored = [
        ScoredItem(item=p, score=_score_product(p, parsed, query_tokens)) for p in products
    ]
    scored = _deduplicate(
        scored, key_fn=lambda p: _normalize(p.get("name", "")) or str(p.get("id", ""))
    )
    scored.sort(key=lambda s: s.score, reverse=True)

    selected = _select_relevant(scored, resolved_top_k)

    logger.info(
        "Ranked %d product(s) -> %d selected (top score=%.2f)",
        len(products), len(selected), scored[0].score if scored else 0.0,
    )

    return [s.item for s in selected]


# ---------------------------------------------------------------------------
# Article (review / news) scoring + ranking
# ---------------------------------------------------------------------------

def _score_article(article: Dict[str, Any], parsed: ParsedQuery, query_tokens: List[str]) -> float:
    title = article.get("title") or ""
    summary = article.get("summary") or ""
    category = (article.get("category") or "").lower()
    haystack = f"{title} {summary} {category}"

    score = 0.0
    score += 2.5 * _keyword_overlap_score(query_tokens, haystack)
    score += 2.0 * _exact_phrase_boost(parsed.query_text, title)
    score += 1.5 * _fuzzy_score(" ".join(query_tokens), title)

    if parsed.entity and parsed.entity != "none" and parsed.entity in category:
        score += 0.5

    # Recency as a small, always-applied tiebreaker so "latest ..." style
    # queries with flat keyword signal still surface the freshest items.
    score += 0.4 * _recency_score(article.get("published_at"))

    return score


def rank_articles(
    articles: List[Dict[str, Any]],
    parsed: ParsedQuery,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Rank, deduplicate, and filter articles down to the most relevant top-k."""
    if not articles:
        return []

    resolved_top_k = top_k or min(parsed.count or DEFAULT_ARTICLE_TOP_K, DEFAULT_ARTICLE_TOP_K)
    query_tokens = _build_query_tokens(parsed)

    scored = [
        ScoredItem(item=a, score=_score_article(a, parsed, query_tokens)) for a in articles
    ]
    scored = _deduplicate(
        scored,
        key_fn=lambda a: _normalize(a.get("title", "")) or str(a.get("id", "")),
    )
    scored.sort(key=lambda s: s.score, reverse=True)

    selected = _select_relevant(scored, resolved_top_k)

    logger.info(
        "Ranked %d article(s) -> %d selected (top score=%.2f)",
        len(articles), len(selected), scored[0].score if scored else 0.0,
    )

    return [s.item for s in selected]
