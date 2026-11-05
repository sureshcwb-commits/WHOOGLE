import hashlib
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from .config import USER_AGENT, MAX_PAGE_BYTES, REQUEST_TIMEOUT, CRAWL_DELAY_SECONDS, MAX_CRAWL_PAGES
from .database import upsert_page

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})
_robot_cache = {}


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url.strip())
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only valid http/https URLs can be crawled")
    return url


def robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url not in _robot_cache:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = SESSION.get(robots_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            elif response.status_code in (401, 403):
                parser.parse(["User-agent: *", "Disallow: /"])
            else:
                parser.parse(["User-agent: *", "Allow: /"])
        except requests.RequestException:
            # Fail closed on robots retrieval errors.
            parser.parse(["User-agent: *", "Disallow: /"])
        _robot_cache[robots_url] = parser
    return _robot_cache[robots_url].can_fetch(USER_AGENT, url)


def fetch_page(url: str):
    url = normalize_url(url)
    if not robots_allowed(url):
        return {"url": url, "skipped": "robots.txt disallows this URL"}
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return {"url": url, "skipped": "not HTML"}
    chunks, size = [], 0
    for chunk in response.iter_content(65536):
        size += len(chunk)
        if size > MAX_PAGE_BYTES:
            return {"url": url, "skipped": "page exceeds configured byte limit"}
        chunks.append(chunk)
    raw = b"".join(chunks)
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else response.url
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "") if description_tag else ""
    content = soup.get_text(" ", strip=True)
    content = " ".join(content.split())[:500_000]
    final_url = normalize_url(response.url)
    return {
        "url": final_url,
        "domain": urlparse(final_url).hostname or "",
        "title": title[:500],
        "description": description[:2000],
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8", "ignore")).hexdigest(),
        "status_code": response.status_code,
        "links": [urljoin(final_url, a.get("href")) for a in soup.find_all("a", href=True)]
    }


def crawl(seed_url: str, max_pages: int = MAX_CRAWL_PAGES, same_domain: bool = True):
    seed = normalize_url(seed_url)
    seed_domain = urlparse(seed).hostname
    queue = deque([seed])
    visited = set()
    indexed, skipped, errors = 0, 0, []
    while queue and len(visited) < max_pages:
        url = normalize_url(queue.popleft())
        if url in visited:
            continue
        visited.add(url)
        try:
            page = fetch_page(url)
            if page.get("skipped"):
                skipped += 1
                continue
            links = page.pop("links", [])
            upsert_page(page)
            indexed += 1
            for link in links:
                try:
                    link = normalize_url(link)
                    host = urlparse(link).hostname
                    if same_domain and host != seed_domain:
                        continue
                    if link not in visited and len(queue) < max_pages * 5:
                        queue.append(link)
                except ValueError:
                    pass
        except (requests.RequestException, ValueError) as exc:
            errors.append({"url": url, "error": str(exc)[:300]})
        time.sleep(max(0, CRAWL_DELAY_SECONDS))
    return {"seed": seed, "visited": len(visited), "indexed": indexed, "skipped": skipped, "errors": errors[:20]}
