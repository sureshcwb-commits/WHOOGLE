import sqlite3
from contextlib import contextmanager
from .config import DB_PATH


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():
    with db_session() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                domain TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                content_hash TEXT NOT NULL DEFAULT '',
                fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status_code INTEGER NOT NULL DEFAULT 200
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS page_index USING fts5(
                title, description, content, url UNINDEXED,
                content='pages', content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            )
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
                INSERT INTO page_index(rowid,title,description,content,url)
                VALUES(new.id,new.title,new.description,new.content,new.url);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
                INSERT INTO page_index(page_index,rowid,title,description,content,url)
                VALUES('delete',old.id,old.title,old.description,old.content,old.url);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
                INSERT INTO page_index(page_index,rowid,title,description,content,url)
                VALUES('delete',old.id,old.title,old.description,old.content,old.url);
                INSERT INTO page_index(rowid,title,description,content,url)
                VALUES(new.id,new.title,new.description,new.content,new.url);
            END
        """)


def upsert_page(page: dict):
    with db_session() as conn:
        conn.execute("""
            INSERT INTO pages(url,domain,title,description,content,content_hash,fetched_at,status_code)
            VALUES(:url,:domain,:title,:description,:content,:content_hash,CURRENT_TIMESTAMP,:status_code)
            ON CONFLICT(url) DO UPDATE SET
                domain=excluded.domain,title=excluded.title,
                description=excluded.description,content=excluded.content,
                content_hash=excluded.content_hash,fetched_at=CURRENT_TIMESTAMP,
                status_code=excluded.status_code
        """, page)


def page_count():
    with db_session() as conn:
        return conn.execute("SELECT count(*) FROM pages").fetchone()[0]
