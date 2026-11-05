import tempfile
from pathlib import Path
import backend.database as database
import backend.search as search


def setup_module():
    database.DB_PATH = Path(tempfile.gettempdir()) / "openseek-test.sqlite"
    try:
        database.DB_PATH.unlink()
    except FileNotFoundError:
        pass
    database.initialize_database()
    database.upsert_page({
        "url": "https://example.test/python", "domain": "example.test",
        "title": "Python Search Tutorial", "description": "Learn search indexing",
        "content": "Python is a programming language used for web search and indexing.",
        "content_hash": "abc", "status_code": 200
    })


def test_search_returns_indexed_page():
    result = search.search_pages("Python", 1, 10)
    assert result["total"] == 1
    assert result["results"][0]["url"] == "https://example.test/python"


def test_empty_or_punctuation_query_is_safe():
    assert search.search_pages("!!!")["total"] == 0
    assert search.search_pages("   ")["total"] == 0
