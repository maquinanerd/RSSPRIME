"""
Lance scraper compatible with the multi-source system
"""

import logging
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_scraper import BaseScraper
from .utils import get_user_agent

logger = logging.getLogger(__name__)


class LanceScraper(BaseScraper):
    """Scraper specifically designed for LANCE! news site"""
    
    def get_site_domain(self):
        """Return the main domain for LANCE!"""
        return "lance.com.br"
    
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from LANCE! listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # More specific selectors for article links on Lance
        selectors = [
            'div.item-noticia a',  # Main list items on some pages
            'a.d-block.chapeu-title-container',  # Featured items
            'h2.title a',  # Other headline links
            'div.list-posts-item a' # Common on /mais-noticias
        ]

        for selector in selectors:
            for link_tag in soup.select(selector):
                href = link_tag.get('href')
                if not href:
                    continue

                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)

                # Only include LANCE! articles that look like articles
                if 'lance.com.br' in full_url and ('.html' in full_url or '.htm' in full_url):
                    # Exclude non-article links
                    if '/galerias/' not in full_url and '/videos/' not in full_url:
                        links.add(full_url)

        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        logger.info(f"Found {len(unique_links)} article links on LANCE! page")
        return unique_links
    
    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of articles"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for pagination links (common patterns)
        next_selectors = [
            'a[rel="next"]',
            'a.next',
            'a.pagination-next',
            'a[aria-label*="next"]',
            'a[aria-label*="Next"]',
            'a[aria-label*="próxima"]',
            'a[aria-label*="Próxima"]'
        ]
        
        for selector in next_selectors:
            next_link = soup.select_one(selector)
            if next_link and next_link.get('href'):
                next_href = next_link.get('href')
                if next_href.startswith('/'):
                    return urljoin(current_url, next_href)
                elif next_href.startswith(('http://', 'https://')):
                    return next_href
        
        return None
    
    def parse_article_metadata(self, html, url):
        """Parse article metadata from LANCE! article page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Try JSON-LD first (most reliable)
        json_ld_data = self.parse_json_ld(html)
        if json_ld_data:
            return json_ld_data
        
        # Fallback to meta tags
        return self._parse_meta_tags(soup, url)
    
    def _parse_meta_tags(self, soup, url):
        """Parse article metadata from meta tags"""
        def get_meta_content(property_name):
            tag = soup.find('meta', {'property': property_name}) or soup.find('meta', {'name': property_name})
            return tag.get('content', '').strip() if tag else ''
        
        # Extract basic metadata
        title = (get_meta_content('og:title') or 
                get_meta_content('twitter:title') or 
                soup.find('title').get_text().strip() if soup.find('title') else '')
        
        description = (get_meta_content('og:description') or 
                      get_meta_content('twitter:description') or 
                      get_meta_content('description') or '')
        
        image = (get_meta_content('og:image') or 
                get_meta_content('twitter:image') or '')
        
        # Clean up image URL
        if image:
            image = self._clean_image_url(image)
        
        # Extract author
        author = (get_meta_content('article:author') or 
                 get_meta_content('author') or '')
        
        # Extract publish date
        pub_date_str = (get_meta_content('article:published_time') or 
                       get_meta_content('article:published') or
                       get_meta_content('datePublished') or '')
        
        pub_date = None
        if pub_date_str:
            try:
                from dateutil import parser
                pub_date = parser.parse(pub_date_str)
            except Exception as e:
                logger.warning(f"Could not parse date '{pub_date_str}': {e}")
        
        return {
            'title': title,
            'description': description,
            'image': image,
            'author': author,
            'pub_date': pub_date,
            'url': url
        }
    
    def _clean_image_url(self, image_url):
        """Clean and validate image URL"""
        if not image_url:
            return None
            
        # Remove query parameters that might cause issues
        if '?' in image_url:
            image_url = image_url.split('?')[0]
        
        # Ensure absolute URL
        if image_url.startswith('/'):
            image_url = urljoin('https://www.lance.com.br', image_url)
        
        # Validate URL format
        try:
            parsed = urlparse(image_url)
            if parsed.scheme in ['http', 'https'] and parsed.netloc:
                return image_url
        except:
            pass
        
        return None