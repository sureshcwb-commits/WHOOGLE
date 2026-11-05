import re
from .database import db_session


def clean_query(q: str) -> str:
    # FTS5 syntax is intentionally restricted to simple user-entered terms.
    terms = re.findall(r"[\w-]+", q, flags=re.UNICODE)
    return " AND ".join('"' + term.replace('"', '""') + '"' for term in terms[:12])


def search_pages(q: str, page: int = 1, page_size: int = 10):
    match_query = clean_query(q)
    if not match_query:
        return {"query": q, "total": 0, "page": page, "results": []}
    offset = (page - 1) * page_size
    with db_session() as conn:
        total = conn.execute(
            "SELECT count(*) FROM page_index WHERE page_index MATCH ?", (match_query,)
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT p.id,p.url,p.title,p.description,p.fetched_at,
                   snippet(page_index,2,'<mark>','</mark>','…',22) AS snippet,
                   bm25(page_index,8.0,3.0,1.0,0.0) AS score
            FROM page_index JOIN pages p ON p.id=page_index.rowid
            WHERE page_index MATCH ?
            ORDER BY score ASC
            LIMIT ? OFFSET ?
        """, (match_query, page_size, offset)).fetchall()
    return {
        "query": q,
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [dict(row) for row in rows]
    }
