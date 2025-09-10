import sqlite3
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class ArticleStore:
    def __init__(self, db_path='data/app.db'):
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        url TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        image TEXT,
                        author TEXT,
                        date_published TIMESTAMP,
                        date_modified TIMESTAMP,
                        fetched_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT DEFAULT 'lance',
                        section TEXT DEFAULT 'futebol',
                        site TEXT DEFAULT 'lance.com.br'
                    )
                ''')

                # Add new columns to existing table if they don't exist
                try:
                    conn.execute('ALTER TABLE articles ADD COLUMN source TEXT DEFAULT "lance"')
                except:
                    pass  # Column already exists

                try:
                    conn.execute('ALTER TABLE articles ADD COLUMN section TEXT DEFAULT "futebol"')
                except:
                    pass  # Column already exists

                try:
                    conn.execute('ALTER TABLE articles ADD COLUMN site TEXT DEFAULT "lance.com.br"')
                except:
                    pass  # Column already exists

                # Create indexes for performance (after columns exist)
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_articles_date_published 
                    ON articles(date_published DESC)
                ''')

                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_articles_fetched_at 
                    ON articles(fetched_at DESC)
                ''')

                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_articles_source_section 
                    ON articles(source, section, COALESCE(date_published, fetched_at) DESC)
                ''')

                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_articles_author 
                    ON articles(author)
                ''')

                conn.commit()
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _row_to_dict(self, row):
        """Convert database row to dictionary"""
        if not row:
            return None

        # Handle both old and new schema
        result = {
            'url': row[0],
            'title': row[1],
            'description': row[2],
            'image': row[3],
            'author': row[4],
            'date_published': datetime.fromisoformat(row[5]) if row[5] else None,
            'date_modified': datetime.fromisoformat(row[6]) if row[6] else None,
            'fetched_at': datetime.fromisoformat(row[7]) if row[7] else None,
            'created_at': datetime.fromisoformat(row[8]) if row[8] else None,
            'updated_at': datetime.fromisoformat(row[9]) if row[9] else None
        }

        # Add new fields if they exist in the row
        if len(row) > 10:
            result['source'] = row[10] or 'lance'
            result['section'] = row[11] or 'futebol'
            result['site'] = row[12] or 'lance.com.br'
        else:
            # Default values for backward compatibility
            result['source'] = 'lance'
            result['section'] = 'futebol'
            result['site'] = 'lance.com.br'

        return result

    def has_article(self, url):
        """Check if article already exists in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT 1 FROM articles WHERE url = ?', (url,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking article existence: {e}")
            return False

    def upsert_article(self, article):
        """Insert or update article in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert datetime objects to ISO strings
                date_published = article['date_published'].isoformat() if article['date_published'] else None
                date_modified = article['date_modified'].isoformat() if article['date_modified'] else None
                fetched_at = article['fetched_at'].isoformat()

                # Check if new columns exist
                cursor = conn.execute("PRAGMA table_info(articles)")
                columns = [row[1] for row in cursor.fetchall()]

                if 'source' in columns:
                    conn.execute('''
                        INSERT OR REPLACE INTO articles 
                        (url, title, description, image, author, date_published, date_modified, fetched_at, updated_at, source, section, site)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                    ''', (
                        article['url'],
                        article['title'],
                        article['description'],
                        article['image'],
                        article['author'],
                        date_published,
                        date_modified,
                        fetched_at,
                        article.get('source', 'lance'),
                        article.get('section', 'futebol'),
                        article.get('site', 'lance.com.br')
                    ))
                else:
                    # Use old schema
                    conn.execute('''
                        INSERT OR REPLACE INTO articles 
                        (url, title, description, image, author, date_published, date_modified, fetched_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        article['url'],
                        article['title'],
                        article['description'],
                        article['image'],
                        article['author'],
                        date_published,
                        date_modified,
                        fetched_at
                    ))

                conn.commit()
                logger.debug(f"Article upserted: {article['url']}")
                return True

        except Exception as e:
            logger.error(f"Error upserting article {article['url']}: {e}")
            return False

    def get_recent_articles(self, limit=30, hours=24, query_filter=None, source=None, section=None):
        """Get recent articles from the database with optional source/section filtering"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Build base WHERE conditions
            where_conditions = ["fetched_at >= ?"]
            params = [cutoff_time]

            # Add source filter if provided
            if source:
                where_conditions.append("source = ?")
                params.append(source)

            # Add section filter if provided  
            if section:
                where_conditions.append("section = ?")
                params.append(section)

            if query_filter:
                # Build search query
                search_terms = query_filter.get('terms', [])
                if search_terms:
                    # Create LIKE conditions for title and description
                    like_conditions = []
                    for term in search_terms:
                        like_conditions.append("(title LIKE ? OR description LIKE ?)")
                        params.extend([f'%{term}%', f'%{term}%'])

                    where_conditions.append(f"({' OR '.join(like_conditions)})")

            where_clause = ' AND '.join(where_conditions)

            query = f"""
                SELECT * FROM articles 
                WHERE {where_clause}
                ORDER BY date_published DESC, fetched_at DESC 
                LIMIT ?
            """
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                articles = []
                for row in rows:
                    article = dict(row)
                    # Parse dates
                    article['date_published'] = self._parse_date(article['date_published'])
                    article['date_modified'] = self._parse_date(article['date_modified'])  
                    article['fetched_at'] = self._parse_date(article['fetched_at'])
                    articles.append(article)

                logger.debug(f"Retrieved {len(articles)} articles (limit={limit}, source={source}, section={section})")
                return articles

        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []

    def _parse_date(self, date_str):
        """Helper to parse date strings, returning None for invalid inputs."""
        if not date_str:
            return None
        try:
            # Attempt to parse as ISO format first
            return datetime.fromisoformat(date_str)
        except ValueError:
            try:
                # Fallback for other potential formats if needed, though ISO is preferred
                # Example: return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return None # Or handle other formats as necessary
            except ValueError:
                return None

    def get_stats(self):
        """Get basic statistics about stored articles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total articles count
                cursor = conn.execute('SELECT COUNT(*) FROM articles')
                total_articles = cursor.fetchone()[0]

                # Last update time
                cursor = conn.execute('''
                    SELECT MAX(fetched_at) FROM articles
                ''')
                last_update = cursor.fetchone()[0]

                return {
                    'total_articles': total_articles,
                    'last_update': last_update
                }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_articles': 0,
                'last_update': None
            }

    def get_detailed_stats(self):
        """Get detailed statistics for admin interface"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Basic counts
                cursor = conn.execute('SELECT COUNT(*) FROM articles')
                stats['total_articles'] = cursor.fetchone()[0]

                # Articles by date ranges
                now = datetime.utcnow()
                day_ago = now - timedelta(days=1)
                week_ago = now - timedelta(days=7)

                cursor = conn.execute('''
                    SELECT COUNT(*) FROM articles 
                    WHERE fetched_at >= ?
                ''', (day_ago.isoformat(),))
                stats['articles_last_24h'] = cursor.fetchone()[0]

                cursor = conn.execute('''
                    SELECT COUNT(*) FROM articles 
                    WHERE fetched_at >= ?
                ''', (week_ago.isoformat(),))
                stats['articles_last_week'] = cursor.fetchone()[0]

                # Last update
                cursor = conn.execute('SELECT MAX(fetched_at) FROM articles')
                stats['last_update'] = cursor.fetchone()[0]

                # Articles with images
                cursor = conn.execute('SELECT COUNT(*) FROM articles WHERE image IS NOT NULL AND image != ""')
                stats['articles_with_images'] = cursor.fetchone()[0]

                # Top authors
                cursor = conn.execute('''
                    SELECT author, COUNT(*) as count 
                    FROM articles 
                    WHERE author IS NOT NULL AND author != ""
                    GROUP BY author 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                stats['top_authors'] = [{'author': row[0], 'count': row[1]} for row in cursor.fetchall()]

                return stats

        except Exception as e:
            logger.error(f"Error getting detailed stats: {e}")
            return {}

    def cleanup_old_articles(self, days_to_keep=30):
        """Remove articles older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM articles 
                    WHERE fetched_at < ?
                ''', (cutoff_date.isoformat(),))

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Cleaned up {deleted_count} old articles")
                return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
            return 0