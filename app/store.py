import sqlite3
import logging
from datetime import datetime, timezone
import pytz
import os

from .sources_config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

DB_PATH = 'articles.db'
TZ = pytz.timezone("America/Sao_Paulo")

def _now_br_iso():
    """Returns the current time in a readable local ISO format."""
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def update_feed_stats(conn, source: str, path: str, found: int, added: int):
    """Updates the statistics for a specific feed in the database."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE feeds
           SET last_refreshed_at = ?,
               last_found_count  = ?,
               last_added_count  = ?
         WHERE source = ? AND path = ?
    """, (_now_br_iso(), found, added, source, path))
    if cur.rowcount == 0:
        # If the feed doesn't exist, create it.
        # This is a fallback; the table should be pre-populated.
        display_name = f"{source}/{path}"
        cur.execute("""
            INSERT INTO feeds (source, path, display_name, last_refreshed_at, last_found_count, last_added_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source, path, display_name, _now_br_iso(), found, added))
    conn.commit()

def get_all_feeds_with_stats(conn):
    """Retrieves all feeds and their latest scraping statistics."""
    cur = conn.cursor()
    cur.execute("""
        SELECT source, path, display_name, last_refreshed_at, last_found_count, last_added_count
          FROM feeds
         ORDER BY display_name ASC
    """)
    rows = cur.fetchall()
    return [
        {
            "source": r[0],
            "path": r[1],
            "display_name": r[2] or f"{r[0]}/{r[1]}",
            "last_refreshed_at": r[3],
            "last_found_count": r[4] or 0,
            "last_added_count": r[5] or 0,
        }
        for r in rows
    ]

class ArticleStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.info(f"Database file not found at {self.db_path}, creating a new one.")
        self._init_db()

    def get_conn(self):
        """Returns a new database connection."""
        return sqlite3.connect(self.db_path)

    def _add_column_if_not_exists(self, cursor, table_name, column_name, column_type):
        """Helper to add a column to a table if it doesn't exist."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        if column_name not in columns:
            logger.info(f"Adding column '{column_name}' to table '{table_name}'.")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def _init_db(self):
        """Initializes the database tables if they don't exist."""
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            # Articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE NOT NULL, source TEXT NOT NULL,
                    section TEXT, title TEXT NOT NULL, description TEXT, image TEXT, author TEXT,
                    pub_date TEXT, scraped_at TEXT NOT NULL
                )
            ''')
            # Feeds table for stats
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feeds (
                    source TEXT NOT NULL, path TEXT NOT NULL, display_name TEXT,
                    last_refreshed_at TEXT, last_found_count INTEGER DEFAULT 0,
                    last_added_count INTEGER DEFAULT 0, PRIMARY KEY (source, path)
                )
            ''')
            self._add_column_if_not_exists(cursor, 'feeds', 'last_refreshed_at', 'TEXT')
            self._add_column_if_not_exists(cursor, 'feeds', 'last_found_count', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'feeds', 'last_added_count', 'INTEGER DEFAULT 0')
            
            conn.commit()
            logger.info("Database tables initialized successfully.")
        finally:
            conn.close()

    def populate_feeds_from_config(self):
        """Pre-populates the feeds table from the sources config."""
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            for source_key, source_data in SOURCES_CONFIG.items():
                for section_key, section_data in source_data.get('sections', {}).items():
                    display_name = f"{source_data.get('name', source_key)} - {section_data.get('name', section_key)}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO feeds (source, path, display_name) VALUES (?, ?, ?)
                    """, (source_key, section_key, display_name))
            conn.commit()
            logger.info("Feeds table populated/updated from SOURCES_CONFIG.")
        finally:
            conn.close()

    # Keep other existing methods like get_recent_articles, get_stats, etc.
    # ... (rest of the class methods from the original file) ...