# Whoogle-style Internet Search (local prototype)

This project now performs **live web metasearch** through the `ddgs` Python package. It does not require an API key. It is a Whoogle-inspired interface, not the original Whoogle software.

## Requirements
- Python 3.11 or newer
- Internet connection

## Windows setup

```cmd
cd whoogle
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Terminal 1 (backend):

```cmd
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 (frontend):

```cmd
python -m http.server 5500 --directory frontend
```

Open http://127.0.0.1:5500 . API docs: http://127.0.0.1:8000/docs . Health: http://127.0.0.1:8000/api/health .

## Search categories
- All: live web text results
- News: live news results
- Images: live image results (availability depends on the upstream provider)

The old `/api/crawl` endpoint remains for indexing permitted websites locally. The normal search screen now queries the live metasearch provider instead of only searching that local index.

## Important limitations
- This is not a full-web crawler and cannot guarantee every page on the internet is indexed or searchable.
- Live results depend on third-party search providers, their uptime, policies, regional coverage, and rate limits. A provider can change or block automated access without notice.
- No API key is required for the default DDGS integration, but availability is not guaranteed. For production reliability, configure a supported commercial search API or operate a SearXNG instance with compliant upstreams.
- The original Whoogle project announced that its Google-scraping approach stopped returning results after Google blocked its non-JavaScript requests. This project therefore uses a search-client integration rather than trying to scrape Google's HTML.
- Do not expose the crawler endpoint publicly without authentication, SSRF protections, strict domain/IP validation, and rate limiting.

## Tests
Run `pytest -q` from this directory. The tests cover local FTS search and API validation; live provider calls are intentionally not part of automated tests because they require external network access and can be rate-limited.


## Public deployment (Render)
This version serves the frontend and API from one FastAPI service. The browser uses the same-origin `/api` path, so no localhost URL or separate static server is needed after deployment.

1. Push the contents of this `whoogle` directory to a GitHub repository (so `backend/`, `frontend/`, and `requirements.txt` are at the repository root).
2. In Render, choose **New → Web Service**, connect the repository, and select Python.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Deploy. Open the `onrender.com` URL shown by Render. Test `/api/health` and `/docs`.

Render free web services can spin down after inactivity, so the first request after idle time may take longer. The default filesystem is ephemeral; the live metasearch function does not depend on the SQLite crawler index. If you want to retain crawled pages across restarts/deploys, configure a persistent disk and set `WHOOGLE_DB` to a database file path on that disk.

The public crawler endpoint is disabled unless `WHOOGLE_CRAWL_TOKEN` is set as a secret environment variable. If enabled, send that value in the `X-Crawl-Token` header. Do not publish the token in frontend JavaScript. Use additional SSRF/network restrictions before enabling public crawling.
