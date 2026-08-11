"""
Chat endpoint.

Wires together the full pipeline:

  user message
    -> session lookup (last 5 messages)
    -> pre-filter (fast keyword rejection, never calls Gemini)
    -> LLM Query Parser (Gemini, cached)               [structured JSON only]
    -> Domain Validation Layer                         [reject out-of-scope]
    -> Daily Intent Cache Check                        [FAST PATH: Skip APIs + LLM #2]
    -> API Orchestrator                                [routes to upstream APIs]
    -> Prompt Builder + Response Generator (Gemini)     [only on cache miss]
    -> ChatResponse with cards, links, metadata
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ArticleCard,
    ChatRequest,
    ChatResponse,
    ProductCard,
    RelatedLink,
    RejectedResponse,
    ResponseMetadata,
)
from app.services.cache_service import get_cached_parser_result, set_cached_parser_result
from app.services.daily_cache_service import daily_cache_service
from app.services.domain_validator import (
    REJECTION_MESSAGE,
    pre_filter_check,
    validate_parsed_query,
)
from app.services.gemini_service import GeminiService, GeminiServiceError
from app.services.orchestrator import orchestrator
from app.services.session_service import session_service
from app.utils.helpers import stable_hash
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

gemini_service = GeminiService()


@router.post("/chat", response_model=None)
async def chat(request: ChatRequest):
    """Main conversational endpoint for the Gadgets360 AI Assistant."""

    session = await session_service.get_or_create_session(request.session_id)
    session_id = session.session_id

    # --- Step 1: fast pre-filter (no Gemini call for obviously bad queries) ---
    is_rejected, reason = pre_filter_check(request.message)
    if is_rejected:
        await session_service.append_message(session_id, "user", request.message)
        await session_service.append_message(session_id, "assistant", REJECTION_MESSAGE)
        return RejectedResponse(session_id=session_id, answer=REJECTION_MESSAGE, reason=reason)

    history = await session_service.get_history(session_id)

    # --- Step 2: LLM Query Parser (cached, structured JSON only) ---
    parser_cache_key = stable_hash({"message": request.message, "history": history})
    cached_parsed = await get_cached_parser_result(parser_cache_key)

    if cached_parsed is not None:
        parsed = cached_parsed
        logger.info("Parser cache hit for session %s", session_id)
    else:
        try:
            parsed = await gemini_service.parse_query(request.message, history)
        except GeminiServiceError as exc:
            logger.error("Query parsing failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="The assistant is temporarily unable to understand your request. Please try again.",
            ) from exc

        await set_cached_parser_result(parser_cache_key, parsed)

    # --- Step 3: Domain Validation Layer ---
    is_valid, rejection_reason = validate_parsed_query(parsed, request.message)
    if not is_valid:
        await session_service.append_message(session_id, "user", request.message)
        await session_service.append_message(session_id, "assistant", REJECTION_MESSAGE)
        return RejectedResponse(
            session_id=session_id, answer=REJECTION_MESSAGE, reason=rejection_reason
        )
# --- NEW: Step 3.5: Daily Intent Response Cache Lookup ---
    intent_key = daily_cache_service.generate_intent_key(parsed)
    cached_entry = await daily_cache_service.get_cached_response(intent_key)

    if cached_entry:
        answer = cached_entry["answer"]
        product_cards = [ProductCard(**p) for p in cached_entry.get("product_cards", [])]
        article_cards = [ArticleCard(**a) for a in cached_entry.get("article_cards", [])]
        related_links = [RelatedLink(**l) for l in cached_entry.get("related_links", [])]
        
        cached_metadata_dict = cached_entry.get("metadata", {})
        metadata = ResponseMetadata(
            intent=cached_metadata_dict.get("intent", parsed.intent),
            entity=cached_metadata_dict.get("entity", parsed.entity),
            used_gemini=False,  # Skipped LLM #2!
            source_apis=cached_metadata_dict.get("source_apis", []),
            cached=True,
        )

        # Update session history & return cached payload directly
        await session_service.append_message(session_id, "user", request.message)
        await session_service.append_message(session_id, "assistant", answer)

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            product_cards=product_cards,
            article_cards=article_cards,
            related_links=related_links,
            metadata=metadata,
        )

    # --- Step 4: API Orchestrator (cache miss: fetch APIs & run Gemini #2) ---
    try:
        result = await orchestrator.handle_query(request.message, parsed, history)
    except Exception as exc:  # noqa: BLE001
        logger.error("Orchestrator failed for session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=500,
            detail="I ran into a problem fetching that information. Please try again.",
        ) from exc

    # Prepare response metadata
    metadata = ResponseMetadata(
        intent=parsed.intent,
        entity=parsed.entity,
        used_gemini=result["used_gemini"],
        source_apis=result["source_apis"],
        cached=False,
    )

    # --- NEW: Step 4.5: Write result to today's daily cache ---
    serializable_payload = {
        "answer": result["answer"],
        "product_cards": [p.model_dump() for p in result["product_cards"]],
        "article_cards": [a.model_dump() for a in result["article_cards"]],
        "related_links": [l.model_dump() for l in result["related_links"]],
        "metadata": metadata.model_dump(),
    }
    await daily_cache_service.set_cached_response(intent_key, parsed, serializable_payload)

    # --- Step 5: Update session history (last 5 messages only) ---
    await session_service.append_message(session_id, "user", request.message)
    await session_service.append_message(session_id, "assistant", result["answer"])

    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        product_cards=result["product_cards"],
        article_cards=result["article_cards"],
        related_links=result["related_links"],
        metadata=metadata,
    )