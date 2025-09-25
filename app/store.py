import sqlite3
import logging
from datetime import datetime, timezone, timedelta
import pytz
import os
import re
import json

from .sources_config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

DB_PATH = 'articles.db'
TZ = pytz.timezone("America/Sao_Paulo")

def _now_br_iso():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def _add_column_if_not_exists(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        logger.info(f"Adding column '{column_name}' to table '{table_name}'.")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

def _parse_date(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date string '{date_str}', returning None.")
        return None

def get_stats(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM articles')
        total_articles = cursor.fetchone()[0]
        cursor.execute('SELECT MAX(scraped_at) FROM articles')
        last_update = cursor.fetchone()[0]
        return {'total_articles': total_articles, 'last_update': last_update}
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {'total_articles': 0, 'last_update': None}

def has_article(conn, url: str) -> bool:
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM articles WHERE url = ?', (url,))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking for article {url}: {e}")
        return False

def upsert_article(conn, article: dict) -> bool:
    from .utils import canonical_url as c_url
    try:
        cursor = conn.cursor()
        date_published = article['date_published'].isoformat() if article.get('date_published') else None
        date_modified = article['date_modified'].isoformat() if article.get('date_modified') else None
        scraped_at = article['fetched_at'].isoformat()
        canonical = c_url(article['url'])
        cursor.execute("""
            INSERT INTO articles 
            (url, canonical_url, source, section, title, description, image, author, date_published, date_modified, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, section, canonical_url) DO NOTHING
        """, (
            article['url'], canonical, article.get('source', 'unknown'),
            article.get('section', 'general'), article['title'], article['description'],
            article['image'], article['author'],
            date_published, date_modified, scraped_at
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error upserting article {article.get('url')}: {e}", exc_info=True)
        return False

def get_recent_articles(conn, limit=30, hours=72, query_filter=None, source=None, section=None, exclude_authors=None):
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        where_conditions = ["scraped_at >= ?"]
        params = [cutoff_time.isoformat()]
        if source:
            where_conditions.append("source = ?")
            params.append(source)
        if section:
            where_conditions.append("section = ?")
            params.append(section)
        if exclude_authors:
            placeholders = ','.join(['?' for _ in exclude_authors])
            where_conditions.append(f"(author IS NULL OR author NOT IN ({placeholders}))")
            params.extend(exclude_authors)
        if query_filter:
            search_terms = query_filter.get('terms', [])
            if search_terms:
                like_conditions = ["(title LIKE ? OR description LIKE ?)" for _ in search_terms]
                where_conditions.append(f"({' OR '.join(like_conditions)})")
                for term in search_terms:
                    params.extend([f'%{term}%', f'%{term}%'])
        where_clause = ' AND '.join(where_conditions)
        query = f"""
            SELECT url, source, section, title, description, image, author, date_published, date_modified, scraped_at as fetched_at
            FROM articles 
            WHERE {where_clause}
            ORDER BY COALESCE(date_published, scraped_at) DESC
            LIMIT ?
        """
        params.append(limit)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        articles = [dict(row) for row in rows]
        for article in articles:
            article['date_published'] = _parse_date(article['date_published'])
            article['date_modified'] = _parse_date(article.get('date_modified'))
            article['fetched_at'] = _parse_date(article['fetched_at'])
        logger.debug(f"Retrieved {len(articles)} articles")
        return articles
    except Exception as e:
        logger.error(f"Error getting recent articles: {e}", exc_info=True)
        return []

def cleanup_old_articles(conn, days_to_keep=30):
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM articles WHERE scraped_at < ?', (cutoff_date.isoformat(),))
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old articles.")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old articles: {e}", exc_info=True)
        return 0

def get_last_update_for_section(conn, source, section):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(scraped_at) FROM articles WHERE source = ? AND section = ?", (source, section))
        result = cursor.fetchone()[0]
        return _parse_date(result) if result else None
    except Exception as e:
        logger.error(f"Error getting last update for {source}/{section}: {e}")
        return None

def update_feed_stats(conn, source: str, path: str, found: int, added: int):
    cur = conn.cursor()
    cur.execute("""
        UPDATE feeds
           SET last_refreshed_at = ?,
               last_found_count  = ?,
               last_added_count  = ?
         WHERE source = ? AND path = ?
    """, (_now_br_iso(), found, added, source, path))
    if cur.rowcount == 0:
        display_name = f"{source}/{path}"
        cur.execute("""
            INSERT INTO feeds (source, path, display_name, last_refreshed_at, last_found_count, last_added_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source, path, display_name, _now_br_iso(), found, added))
    conn.commit()

def get_all_feeds_with_stats(conn):
    cur = conn.cursor()
    cur.execute("SELECT source, path, display_name, last_refreshed_at, last_found_count, last_added_count FROM feeds ORDER BY display_name ASC")
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

def save_processed_topic(conn, topic_name, json_data, updated_at):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO processed_topics (topic_name, json_data, updated_at)
            VALUES (?, ?, ?)
        """, (topic_name, json_data, updated_at))
        conn.commit()
        logger.info(f"Successfully saved processed topic: {topic_name}")
        return True
    except Exception as e:
        logger.error(f"Error saving processed topic {topic_name}: {e}", exc_info=True)
        return False

def get_processed_topic(conn, topic_name):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT json_data FROM processed_topics WHERE topic_name = ?", (topic_name,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    except Exception as e:
        logger.error(f"Error retrieving processed topic {topic_name}: {e}", exc_info=True)
        return None

class ArticleStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.info(f"Database file not found at {self.db_path}, creating a new one.")
        self._init_db()
        self.populate_feeds_from_config()

    def get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, canonical_url TEXT,
                    source TEXT NOT NULL, section TEXT, title TEXT NOT NULL, description TEXT,
                    image TEXT, author TEXT, date_published TEXT, date_modified TEXT, scraped_at TEXT NOT NULL
                )
            ''')
            _add_column_if_not_exists(cursor, 'articles', 'canonical_url', 'TEXT')
            _add_column_if_not_exists(cursor, 'articles', 'date_published', 'TEXT')
            _add_column_if_not_exists(cursor, 'articles', 'date_modified', 'TEXT')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_articles_source_section_canonical ON articles (source, section, canonical_url)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feeds (
                    source TEXT NOT NULL, path TEXT NOT NULL, display_name TEXT, last_refreshed_at TEXT,
                    last_found_count INTEGER DEFAULT 0, last_added_count INTEGER DEFAULT 0, PRIMARY KEY (source, path)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_topics (
                    topic_name TEXT PRIMARY KEY, json_data TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            ''')
            conn.commit()
            logger.info("Database tables initialized successfully.")
        finally:
            conn.close()

    def populate_feeds_from_config(self):
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            for source_key, source_data in SOURCES_CONFIG.items():
                for section_key, section_data in source_data.get('sections', {}).items():
                    display_name = f"{source_data.get('name', source_key)} - {section_data.get('name', section_key)}"
                    cursor.execute("INSERT OR IGNORE INTO feeds (source, path, display_name) VALUES (?, ?, ?)", (source_key, section_key, display_name))
            conn.commit()
            logger.info("Feeds table populated/updated from SOURCES_CONFIG.")
            
            # Perform cleanups
            self._perform_cleanup(cursor, conn, 'ole', ["/suscripciones/", "/estadisticas/", "/agenda/"])
            self._perform_cleanup(cursor, conn, 'abola', ["/video/", "/a-bola-tv/"])

        finally:
            conn.close()

    def _perform_cleanup(self, cursor, conn, source_name, patterns):
        try:
            logger.info(f"Performing cleanup of invalid {source_name} articles...")
            like_conditions = " OR ".join(["url LIKE ?" for _ in patterns])
            query = f"DELETE FROM articles WHERE source = ? AND ({like_conditions})"
            params = [source_name] + [f'%{p}%' for p in patterns]
            
            cursor.execute(query, params)
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} invalid {source_name} articles.")
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to perform {source_name} cleanup: {e}")