import os
import secrets
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, Field

from .config import MAX_CRAWL_PAGES
from .metasearch import search_web

app = FastAPI(title="Whoogle-like Internet Search API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_startup_error = None


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=20, ge=1, le=MAX_CRAWL_PAGES)
    same_domain: bool = True


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Always answer with JSON so the frontend can show a readable error.
    return JSONResponse(status_code=500, content={"detail": f"Server error: {type(exc).__name__}: {str(exc)[:200]}"})


@app.on_event("startup")
def startup():
    global _startup_error
    # The local crawl index is optional; never let it stop the site from starting.
    try:
        from .database import initialize_database
        initialize_database()
    except Exception:
        _startup_error = traceback.format_exc()[-500:]


@app.get("/api/health")
def health():
    pages = None
    try:
        from .database import page_count
        pages = page_count()
    except Exception:
        pass
    return {"status": "ok", "indexed_pages": pages, "live_search": True,
            "provider": "DDGS", "python": sys.version.split()[0],
            "startup_error": _startup_error}


@app.get("/api/diagnose")
def diagnose():
    """Open /api/diagnose in the browser to see exactly why live search fails."""
    info = {"python": sys.version.split()[0]}
    try:
        import ddgs
        info["ddgs_version"] = getattr(ddgs, "__version__", "installed")
        from ddgs import DDGS
        results = list(DDGS(timeout=15).text("python", max_results=3))
        info["search_ok"] = True
        info["result_count"] = len(results)
        info["first_result"] = results[0] if results else None
    except Exception as exc:
        info["search_ok"] = False
        info["error_type"] = type(exc).__name__
        info["error_message"] = str(exc)[:500]
    return info


@app.get("/api/search")
def api_search(
    q: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1, le=5),
    category: str = Query(default="web", pattern="^(web|news|images)$"),
):
    try:
        return search_web(q, page=page, page_size=10, category=category)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:250]) from exc


@app.post("/api/crawl")
def api_crawl(body: CrawlRequest, x_crawl_token: str | None = Header(default=None)):
    expected = os.getenv("WHOOGLE_CRAWL_TOKEN")
    if not expected:
        raise HTTPException(status_code=404, detail="Crawler is disabled on this deployment")
    if not x_crawl_token or not secrets.compare_digest(x_crawl_token, expected):
        raise HTTPException(status_code=401, detail="Invalid crawler token")
    try:
        from .crawler import crawl
        return crawl(str(body.url), max_pages=body.max_pages, same_domain=body.same_domain)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:300]) from exc

		
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")

from fastapi.responses import Response

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#4285f4"/>
<circle cx="28" cy="28" r="12" fill="none" stroke="#fff" stroke-width="6"/>
<line x1="37" y1="37" x2="50" y2="50" stroke="#fff" stroke-width="6" stroke-linecap="round"/>
</svg>"""


@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(
        content=FAVICON_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
