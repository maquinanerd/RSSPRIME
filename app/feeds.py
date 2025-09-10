import logging
from datetime import datetime
from urllib.parse import urlparse
from feedgen.feed import FeedGenerator as FG
from .utils import extract_mime_type

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
    
    def _create_base_feed(self):
        """Create base feed with common metadata"""
        fg = FG()
        
        # Basic feed information
        fg.id(self.base_info['id'])
        fg.title(self.base_info['title'])
        fg.link(href=self.base_info['link']['href'], rel=self.base_info['link']['rel'])
        fg.description(self.base_info['description'])
        fg.language(self.base_info['language'])
        fg.generator(self.base_info['generator'])
        
        # Additional metadata
        fg.lastBuildDate(datetime.utcnow())
        fg.managingEditor('noreply@lance-feeds.repl.co (Lance Feed Bot)')
        fg.webMaster('noreply@lance-feeds.repl.co (Lance Feed Bot)')
        
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
            if article['date_published']:
                fe.published(article['date_published'])
            
            if article['date_modified']:
                fe.updated(article['date_modified'])
            elif article['date_published']:
                fe.updated(article['date_published'])
            else:
                fe.updated(article['fetched_at'])
            
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
    
    def generate_rss(self, articles):
        """Generate RSS 2.0 feed"""
        try:
            fg = self._create_base_feed()
            
            # RSS-specific settings
            fg.link(href='https://lance-feeds.repl.co/feeds/lance/rss.xml', rel='self')
            fg.ttl(15)  # 15 minutes TTL
            
            # Add articles
            added_count = 0
            for article in articles:
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            logger.info(f"Generated RSS feed with {added_count} articles")
            return fg.rss_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating RSS feed: {e}")
            raise
    
    def generate_atom(self, articles):
        """Generate Atom 1.0 feed"""
        try:
            fg = self._create_base_feed()
            
            # Atom-specific settings
            fg.link(href='https://lance-feeds.repl.co/feeds/lance/atom.xml', rel='self')
            fg.updated(datetime.utcnow())
            
            # Add articles
            added_count = 0
            for article in articles:
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            logger.info(f"Generated Atom feed with {added_count} articles")
            return fg.atom_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating Atom feed: {e}")
            raise
