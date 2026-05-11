import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    UNIQUE NOT NULL,
                title       TEXT,
                source      TEXT,
                topic       TEXT,
                relevance   TEXT,
                summary     TEXT,
                image       TEXT,
                crawled_at  TEXT    DEFAULT (datetime('now','localtime')),
                sent        INTEGER DEFAULT 0
            )
        """)
        try:
            conn.execute("ALTER TABLE articles ADD COLUMN summary TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE articles ADD COLUMN image TEXT")
        except sqlite3.OperationalError:
            pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sent ON articles(sent)")
        conn.commit()
    logger.info("DB 초기화 완료")

def is_duplicate(url):
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM articles WHERE url=?", (url,)).fetchone()
        return row is not None

def save_article(article):
    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO articles (url, title, source, topic, relevance, summary, image)
                   VALUES (:url, :title, :source, :topic, :relevance, :summary, :image)""",
                {
                    "url": article.get("url"),
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "topic": article.get("topic", ""),
                    "relevance": article.get("relevance", ""),
                    "summary": article.get("summary", ""),
                    "image": article.get("image", ""),
                },
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def mark_sent(urls):
    with get_connection() as conn:
        conn.executemany("UPDATE articles SET sent=1 WHERE url=?", [(u,) for u in urls])
        conn.commit()

def get_unsent_articles():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE sent=0 ORDER BY crawled_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
