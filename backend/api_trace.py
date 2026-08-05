"""
API Trace Utility for Gadgets360 Assistant Backend.

Runs a test query through the backend orchestrator and passively intercepts 
all live upstream API requests and responses at runtime without modifying 
any backend files. Generates `api_trace.md`.
"""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Force load environment variables from root .env
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Backend imports (read-only, no backend files are modified)
from app.models.schemas import ParsedQuery
from app.services.gemini_service import GeminiService
from app.services.orchestrator import orchestrator
from app.api_clients.products_client import ProductsClient
from app.api_clients.reviews_client import ReviewsClient
from app.api_clients.search_client import SearchClient


# ============================================================================
# 1. DATA MODELS & SENSITIVE DATA MASKING
# ============================================================================

def mask_sensitive(data: Any) -> Any:
    """Recursively mask sensitive keys (API keys, authorization tokens) in strings/dicts."""
    if isinstance(data, dict):
        masked_dict = {}
        for k, v in data.items():
            if any(secret in k.lower() for secret in ["key", "auth", "token", "password"]):
                masked_dict[k] = "****************"
            else:
                masked_dict[k] = mask_sensitive(v)
        return masked_dict
    elif isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    elif isinstance(data, str):
        # Mask API keys passed as query params in URLs
        return re.sub(r'([?&](?:key|client_key|api_key)=)[^&]+', r'\1****************', data)
    return data


@dataclass
class APICallLog:
    """Represents a captured API call trace."""
    api_name: str
    method: str
    url: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)
    request_body: Any = None
    response_body: Any = None
    status_code: Optional[int] = 200
    duration_seconds: float = 0.0


# ============================================================================
# 2. RUNTIME INTERCEPTOR / TRACER
# ============================================================================

class APITracer:
    """Intercepts live backend client execution in memory to capture trace logs."""

    def __init__(self):
        self.logs: Dict[str, APICallLog] = {}

    def log_call(
        self,
        api_name: str,
        method: str,
        url: str,
        parameters: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        request_body: Any = None,
        response_body: Any = None,
        status_code: int = 200,
        duration: float = 0.0,
    ):
        self.logs[api_name.upper()] = APICallLog(
            api_name=api_name.upper(),
            method=method.upper(),
            url=mask_sensitive(url),
            parameters=mask_sensitive(parameters or {}),
            headers=mask_sensitive(headers or {}),
            request_body=mask_sensitive(request_body),
            response_body=mask_sensitive(response_body),
            status_code=status_code,
            duration_seconds=round(duration, 3),
        )


# ============================================================================
# 3. REPORT GENERATORS (MODULAR STRUCTURE)
# ============================================================================

class MarkdownReportWriter:
    """Renders traced API logs into the required Markdown report format."""

    @staticmethod
    def _format_json(data: Any) -> str:
        if data is None:
            return "N/A"
        if isinstance(data, str):
            try:
                # Pretty print if valid JSON string
                parsed = json.loads(data)
                return json.dumps(parsed, indent=2)
            except Exception:
                return data
        return json.dumps(data, indent=2)

    def generate_report(self, query: str, tracer: APITracer) -> str:
        md = []
        md.append("# API Flow Test\n")
        md.append("## Test Query")
        md.append(f"{query}\n")
        md.append("---\n")

        # Required order of sections
        sections = ["INTENT", "REVIEW", "PRODUCT", "SEARCH", "OUTPUT"]

        for sec in sections:
            log = tracer.logs.get(sec)
            md.append(f"# {sec} API\n")

            if not log:
                md.append("URL:\nNot Called\n")
                md.append("Parameters:\nN/A\n")
                md.append("Request:\nN/A\n")
                md.append("Response:\nSkipped or Not Triggered by Query Intent\n")
            else:
                md.append(f"URL:\n{log.url}\n")
                md.append(f"Method:\n{log.method}\n")
                
                md.append("Parameters:")
                if log.parameters:
                    md.append("```json")
                    md.append(self._format_json(log.parameters))
                    md.append("```\n")
                else:
                    md.append("None\n")

                md.append("Request:")
                if log.request_body:
                    md.append("```json")
                    md.append(self._format_json(log.request_body))
                    md.append("```\n")
                else:
                    md.append("None\n")

                md.append("Response:")
                md.append("```json")
                md.append(self._format_json(log.response_body))
                md.append("```\n")

            md.append("---\n")

        return "\n".join(md)


class PDFReportWriter:
    """Placeholder for future PDF extension."""
    def generate_report(self, query: str, tracer: APITracer):
        raise NotImplementedError("PDF Exporter can be attached here in the future.")


class DocxReportWriter:
    """Placeholder for future DOCX extension."""
    def generate_report(self, query: str, tracer: APITracer):
        raise NotImplementedError("DOCX Exporter can be attached here in the future.")


# ============================================================================
# 4. MAIN TRACING RUNNER
# ============================================================================

async def run_api_trace(test_query: str = "Laptop under ₹50,000 with Best Review"):
    print(f"\n[TRACER] Starting live API trace for test query: '{test_query}'...\n")
    tracer = APITracer()

    # ------------------------------------------------------------------------
    # MONKEY-PATCH BACKEND CLIENTS IN MEMORY TO CAPTURE RUNTIME VALUES
    # ------------------------------------------------------------------------
    
    # 1. Intercept Intent API (Gemini Query Parsing)
    original_parse_query = GeminiService.parse_query

    async def patched_parse_query(self, user_message: str, history: List[Dict[str, Any]]):
        start = time.time()
        result = await original_parse_query(self, user_message, history)
        duration = time.time() - start

        tracer.log_call(
            api_name="INTENT",
            method="POST",
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            request_body={"user_message": user_message, "history": history},
            response_body=result.model_dump(),
            duration=duration,
        )
        return result

    GeminiService.parse_query = patched_parse_query

    # 2. Intercept Review API
    original_get_reviews = ReviewsClient.get_reviews

    async def patched_get_reviews(self, entity=None, product_id=None, keywords=None, count=5):
        start = time.time()
        results = await original_get_reviews(self, entity, product_id, keywords, count)
        duration = time.time() - start

        tracer.log_call(
            api_name="REVIEW",
            method="GET",
            url=f"{self.base_url}",
            parameters={"entity": entity, "product_id": product_id, "keywords": keywords, "count": count},
            response_body=results,
            duration=duration,
        )
        return results

    ReviewsClient.get_reviews = patched_get_reviews

    # 3. Intercept Product API
    original_search_products = ProductsClient.search_products

    async def patched_search_products(self, entity=None, budget=None, priority=None, brand=None, count=5, keywords=None, query_text=None):
        start = time.time()
        results = await original_search_products(self, entity, budget, priority, brand, count, keywords, query_text)
        duration = time.time() - start

        tracer.log_call(
            api_name="PRODUCT",
            method="GET",
            url=f"{self._detail_client.base_url}",
            parameters={
                "entity": entity,
                "budget": budget,
                "priority": priority,
                "brand": brand,
                "count": count,
                "keywords": keywords,
                "query_text": query_text,
            },
            response_body=results,
            duration=duration,
        )
        return results

    ProductsClient.search_products = patched_search_products

    # 4. Intercept Search API
    original_search = SearchClient.search

    async def patched_search(self, query: str, keywords=None, count=5):
        start = time.time()
        results = await original_search(self, query, keywords, count)
        duration = time.time() - start

        tracer.log_call(
            api_name="SEARCH",
            method="GET",
            url="Pricee Search / Gadgets360 News Composite Endpoint",
            parameters={"query": query, "keywords": keywords, "count": count},
            response_body=results,
            duration=duration,
        )
        return results

    SearchClient.search = patched_search

    # 5. Intercept Output API (Gemini Response Generation)
    # 5. Intercept Output API (Gemini Response Generation)
    original_generate_response = GeminiService.generate_response

    async def patched_generate_response(self, user_message: str, parsed_query: Dict[str, Any], api_data: Dict[str, Any]):
        start = time.time()
        summary = await original_generate_response(self, user_message, parsed_query, api_data)
        duration = time.time() - start

        combined_request = {
            "user_message": user_message,
            "parsed_query": parsed_query,
            "context_data": api_data
        }

        tracer.log_call(
            api_name="OUTPUT",
            method="POST",
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            request_body=combined_request,
            response_body={"generated_summary": summary},
            duration=duration,
        )
        return summary

    GeminiService.generate_response = patched_generate_response

    # ------------------------------------------------------------------------
    # EXECUTE BACKEND FLOW
    # ------------------------------------------------------------------------
    
    # Step A: Run parser
    parsed_query = await orchestrator.gemini_service.parse_query(test_query, [])

    # Step B: Run Orchestrator flow
    final_response = await orchestrator.handle_query(
        user_message=test_query,
        parsed=parsed_query,
        history=[]
    )

    # ------------------------------------------------------------------------
    # GENERATE MARKDOWN REPORT
    # ------------------------------------------------------------------------
    writer = MarkdownReportWriter()
    report_md = writer.generate_report(test_query, tracer)

    output_file = BASE_DIR / "backend_flow_report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"[TRACER SUCCESS] API trace complete! Report written to '{output_file.name}'.\n")


if __name__ == "__main__":
    asyncio.run(run_api_trace())