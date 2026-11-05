"""Live web metasearch using the DDGS library; no API key required.

Search providers can rate-limit or change their interfaces. This module deliberately
uses a supported search client rather than scraping Google's HTML pages.
"""
from __future__ import annotations

import os
from typing import Any


def _clean_result(item: dict[str, Any], category: str) -> dict[str, Any] | None:
    url = item.get("href") or item.get("url")
    title = item.get("title") or item.get("name") or "Untitled result"
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    return {
        "title": str(title)[:500],
        "url": url,
        "snippet": str(item.get("body") or item.get("description") or item.get("excerpt") or "")[:1500],
        "source": url.split("/")[2],
        "category": category,
        "score": None,
    }


def search_web(query: str, page: int = 1, page_size: int = 10, category: str = "web") -> dict:
    query = query.strip()
    if not query:
        return {"query": query, "total": 0, "page": page, "page_size": page_size, "category": category, "results": []}
    if category not in {"web", "news", "images"}:
        category = "web"
    # DDGS exposes a no-key metasearch client. It may return fewer than requested
    # results when upstream engines throttle or challenge automated traffic.
    try:
        from ddgs import DDGS
        client = DDGS(timeout=15)
        offset = (page - 1) * page_size
        limit = min(offset + page_size, 50)
        if category == "news":
            raw = list(client.news(query, max_results=limit))
        elif category == "images":
            raw = list(client.images(query, max_results=limit))
        else:
            raw = list(client.text(query, max_results=limit))
        normalized = []
        for item in raw[offset:offset + page_size]:
            result = _clean_result(item, category)
            if result:
                if category == "images":
                    result["image"] = item.get("image") or item.get("thumbnail")
                normalized.append(result)
        return {
            "query": query, "total": len(raw), "page": page,
            "page_size": page_size, "category": category,
            "provider": "DuckDuckGo via DDGS", "results": normalized,
            "notice": "Live results are supplied by external search providers and may be rate-limited."
        }
    except ImportError as exc:
        raise RuntimeError("Missing dependency 'ddgs'. Run: pip install -r requirements.txt") from exc
    except Exception as exc:
        # Keep internal exception details out of the public response.
        raise RuntimeError(f"Live search provider unavailable ({type(exc).__name__}). Try again later or configure another provider.") from exc
