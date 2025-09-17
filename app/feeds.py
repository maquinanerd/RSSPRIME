import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from feedgen.feed import FeedGenerator as FG
from .utils import extract_mime_type
from .sources_config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

class FeedGenerator:
    def __init__(self):
        self.base_info = {
            'id': 'https://lance-feeds.repl.co/',
            'title': 'LANCE! - Feed não oficial',
            'link': {'href': 'https://www.lance.com.br/', 'rel': 'alternate'},
            'description': 'Feed RSS/Atom não oficial do LANCE! - Notícias de futebol e esportes',
            'language': 'pt-BR',
            'generator': 'Lance Feed Generator v1.0'
        }
        self.brasilia_tz = ZoneInfo("America/Sao_Paulo")
    
    def _create_base_feed(self, source='lance', section='futebol', feed_format='rss'):
        """Create base feed with source-specific metadata"""
        fg = FG()
        
        # Get source configuration
        source_config = SOURCES_CONFIG.get(source, SOURCES_CONFIG['lance'])
        section_config = source_config['sections'].get(section, list(source_config['sections'].values())[0])
        
        # Basic feed information with unique IDs
        unique_id = f"https://lance-feeds.repl.co/feeds/{source}/{section}/{feed_format}"
        fg.id(unique_id)
        fg.title(f"{source_config['name']} - {section_config['name']} - Feed não oficial")
        fg.link(href=source_config['base_url'], rel='alternate')
        fg.description(section_config['description'])
        fg.language(source_config.get('language', 'pt-BR'))
        fg.generator('Multi-Source Feed Generator v1.0')
        
        # Additional metadata
        fg.lastBuildDate(datetime.now(timezone.utc).astimezone(self.brasilia_tz))
        fg.managingEditor('noreply@lance-feeds.repl.co (Multi-Source Feed Bot)')
        fg.webMaster('noreply@lance-feeds.repl.co (Multi-Source Feed Bot)')
        
        return fg
    
    def _add_article_to_feed(self, fg, article):
        """Add a single article to the feed"""
        try:
            fe = fg.add_entry()
            
            # Required fields
            fe.id(article['url'])
            fe.title(article['title'])
            fe.link(href=article['url'])
            fe.description(article['description'] or article['title'])
            
            # Dates
            # Use date_published, but fallback to other dates to ensure pubDate is always present.
            pub_date = article.get('date_published') or article.get('date_modified') or article.get('fetched_at')
            if pub_date:
                fe.published(pub_date.astimezone(self.brasilia_tz))
            
            if article['date_modified']:
                fe.updated(article['date_modified'].astimezone(self.brasilia_tz))
            else:
                # Fallback to published or fetched date for the 'updated' tag
                fallback_date = article.get('date_published') or article.get('fetched_at')
                fe.updated(fallback_date.astimezone(self.brasilia_tz))
            
            # Author
            if article['author']:
                fe.author(name=article['author'])
            
            # GUID (for RSS)
            fe.guid(article['url'], permalink=True)
            
            # Image enclosure
            if article['image']:
                try:
                    mime_type = extract_mime_type(article['image'])
                    fe.enclosure(article['image'], length='0', type=mime_type)
                except Exception as e:
                    logger.warning(f"Could not add image enclosure for {article['url']}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding article to feed: {article['url']}: {e}")
            return False
    
    def generate_rss(self, articles, source='lance', section='futebol'):
        """Generate RSS 2.0 feed"""
        try:
            # Get source configuration
            source_config = SOURCES_CONFIG.get(source, SOURCES_CONFIG['lance'])
            section_config = source_config['sections'].get(section, list(source_config['sections'].values())[0])
            
            fg = self._create_base_feed(source=source, section=section, feed_format='rss')
            
            # RSS-specific settings
            fg.link(href=f'https://lance-feeds.repl.co/feeds/{source}/{section}/rss', rel='self')
            fg.ttl(15)  # 15 minutes TTL
            
            # Add articles (reverse order so newest appear first in feed)
            added_count = 0
            for article in reversed(articles):
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            # Set lastBuildDate to the date of the newest article, if available
            if articles:
                newest_article = articles[0] # Query is sorted DESC
                pub_date = newest_article.get('date_published') or newest_article.get('date_modified') or newest_article.get('fetched_at')
                if pub_date:
                    fg.lastBuildDate(pub_date.astimezone(self.brasilia_tz))

            logger.info(f"Generated RSS feed with {added_count} articles")
            return fg.rss_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating RSS feed: {e}")
            raise
    
    def generate_atom(self, articles, source='lance', section='futebol'):
        """Generate Atom 1.0 feed"""
        try:
            # Get source configuration
            source_config = SOURCES_CONFIG.get(source, SOURCES_CONFIG['lance'])
            section_config = source_config['sections'].get(section, list(source_config['sections'].values())[0])
            
            fg = self._create_base_feed(source=source, section=section, feed_format='atom')
            
            # Atom-specific settings
            fg.link(href=f'https://lance-feeds.repl.co/feeds/{source}/{section}/atom', rel='self')
            fg.updated(datetime.now(timezone.utc).astimezone(self.brasilia_tz))
            
            # Add articles (reverse order so newest appear first in feed)
            added_count = 0
            for article in reversed(articles):
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            # Set the main feed 'updated' tag to the date of the newest article
            if articles:
                newest_article = articles[0] # Query is sorted DESC
                pub_date = newest_article.get('date_published') or newest_article.get('date_modified') or newest_article.get('fetched_at')
                if pub_date:
                    fg.updated(pub_date.astimezone(self.brasilia_tz))

            logger.info(f"Generated Atom feed with {added_count} articles")
            return fg.atom_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating Atom feed: {e}")
            raise
