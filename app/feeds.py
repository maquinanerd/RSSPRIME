import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from feedgen.feed import FeedGenerator as FG
from .utils import extract_mime_type, deduplicate_articles, best_dt
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
    
    def _create_base_feed(self, source='lance', section='futebol', feed_format='rss', title=None, description=None):
        """Create base feed with source-specific or custom metadata"""
        fg = FG()
        
        source_config = SOURCES_CONFIG.get(source, SOURCES_CONFIG['lance'])
        section_config = source_config['sections'].get(section, list(source_config['sections'].values())[0])
        
        unique_id = f"https://lance-feeds.repl.co/feeds/{source}/{section}/{feed_format}"
        fg.id(unique_id)
        
        if title:
            fg.title(title)
        else:
            fg.title(f"{source_config['name']} - {section_config['name']} - Feed não oficial")

        if description:
            fg.description(description)
        else:
            fg.description(section_config['description'])

        fg.link(href=source_config['base_url'], rel='alternate')
        fg.language(source_config.get('language', 'pt-BR'))
        fg.generator('Multi-Source Feed Generator v1.0')
        fg.ttl(30)  # Add TTL
        
        fg.lastBuildDate(datetime.now(timezone.utc).astimezone(self.brasilia_tz))
        fg.managingEditor('noreply@lance-feeds.repl.co (Multi-Source Feed Bot)')
        fg.webMaster('noreply@lance-feeds.repl.co (Multi-Source Feed Bot)')
        
        return fg
    
    def _add_article_to_feed(self, fg, article):
        """Add a single article to the feed"""
        try:
            fe = fg.add_entry()

            # Handle URL from either 'link' (new format) or 'url' (old format)
            link = article.get('link') or article.get('url')
            if not link:
                logger.error("Skipping article with no link or url.")
                return False

            fe.id(link)
            fe.title(article['title'])
            fe.link(href=link)
            fe.description(article.get('summary') or article.get('description') or article['title'])

            # Use best_dt to ensure we have a valid, timezone-aware date
            pub_date = best_dt(article)

            if pub_date:
                fe.published(pub_date.astimezone(self.brasilia_tz))
                fe.updated(pub_date.astimezone(self.brasilia_tz))

            if article.get('author'):
                fe.author(name=article['author'])

            # Use the article link as the GUID
            fe.guid(link, permalink=True)

            # Enclosure with length=0 is invalid. Removing it.
            # if article.get('image'):
            #     try:
            #         mime_type = extract_mime_type(article['image'])
            #         fe.enclosure(article['image'], length='0', type=mime_type)
            #     except Exception as e:
            #         logger.warning(f"Could not add image enclosure for {link}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error adding article to feed: {article.get('link') or article.get('url')}: {e}", exc_info=True)
            return False
    
    def generate_rss(self, articles, source='lance', section='futebol', title=None, description=None):
        """Generate RSS 2.0 feed"""
        try:
            fg = self._create_base_feed(source=source, section=section, feed_format='rss', title=title, description=description)
            
            fg.link(href=f'https://lance-feeds.repl.co/feeds/{source}/{section}/rss', rel='self', type='application/rss+xml')
            
            # 1. Deduplicate articles
            dedup_articles = deduplicate_articles(articles)

            # 2. Sort articles reverse-chronologically
            sorted_articles = sorted(
                dedup_articles,
                key=lambda it: best_dt(it) or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )

            # 3. Sanity check the sort order
            for i in range(len(sorted_articles) - 1):
                di = best_dt(sorted_articles[i])
                dj = best_dt(sorted_articles[i+1])
                if di and dj and di < dj:
                    logger.error(f"Feed items out of order: {di} (index {i}) < {dj} (index {i+1})")
                    break

            added_count = 0
            for article in sorted_articles:
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            if sorted_articles:
                newest_article = sorted_articles[0]
                pub_date = best_dt(newest_article)
                if pub_date:
                    fg.lastBuildDate(pub_date.astimezone(self.brasilia_tz))

            logger.info(f"Generated RSS feed with {added_count} articles")
            return fg.rss_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating RSS feed: {e}")
            raise
    
    def generate_atom(self, articles, source='lance', section='futebol', title=None, description=None):
        """Generate Atom 1.0 feed"""
        try:
            fg = self._create_base_feed(source=source, section=section, feed_format='atom', title=title, description=description)
            
            fg.link(href=f'https://lance-feeds.repl.co/feeds/{source}/{section}/atom', rel='self', type='application/atom+xml')
            
            # 1. Deduplicate articles
            dedup_articles = deduplicate_articles(articles)

            # 2. Sort articles reverse-chronologically
            sorted_articles = sorted(
                dedup_articles,
                key=lambda it: best_dt(it) or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )

            # 3. Sanity check the sort order
            for i in range(len(sorted_articles) - 1):
                di = best_dt(sorted_articles[i])
                dj = best_dt(sorted_articles[i+1])
                if di and dj and di < dj:
                    logger.error(f"Feed items out of order: {di} (index {i}) < {dj} (index {i+1})")
                    break
            
            added_count = 0
            for article in sorted_articles:
                if self._add_article_to_feed(fg, article):
                    added_count += 1
            
            if sorted_articles:
                newest_article = sorted_articles[0]
                pub_date = best_dt(newest_article)
                if pub_date:
                    fg.updated(pub_date.astimezone(self.brasilia_tz))
                else:
                    fg.updated(datetime.now(timezone.utc).astimezone(self.brasilia_tz))
            else:
                fg.updated(datetime.now(timezone.utc).astimezone(self.brasilia_tz))

            logger.info(f"Generated Atom feed with {added_count} articles")
            return fg.atom_str(pretty=True).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating Atom feed: {e}")
            raise
