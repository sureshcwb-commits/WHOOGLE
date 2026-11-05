import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _default_db() -> Path:
    candidate = ROOT / "whoogle.db"
    try:
        with open(ROOT / ".write_test", "w") as f:
            f.write("ok")
        (ROOT / ".write_test").unlink()
        return candidate
    except OSError:
        return Path(tempfile.gettempdir()) / "whoogle.db"


DB_PATH = Path(os.getenv("WHOOGLE_DB") or _default_db())
USER_AGENT = os.getenv("WHOOGLE_USER_AGENT", "WhoogleLikeBot/0.2 (+local educational search engine)")
MAX_PAGE_BYTES = int(os.getenv("WHOOGLE_MAX_PAGE_BYTES", "2000000"))
REQUEST_TIMEOUT = float(os.getenv("WHOOGLE_REQUEST_TIMEOUT", "12"))
CRAWL_DELAY_SECONDS = float(os.getenv("WHOOGLE_CRAWL_DELAY", "1.5"))
MAX_CRAWL_PAGES = int(os.getenv("WHOOGLE_MAX_CRAWL_PAGES", "100"))
