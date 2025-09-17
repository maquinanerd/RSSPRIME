"""
Folha de S.Paulo-specific scraper implementation
"""

import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, SoupStrainer
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FolhaScraper(BaseScraper):
    """Scraper specifically designed for Folha de S.Paulo news sites"""
    
    def get_site_domain(self):
        """Return the main domain for Folha"""
        return "www1.folha.uol.com.br"
    
    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Folha listing pages, optimized for performance."""
        # Use SoupStrainer to parse only 'a' tags with an 'href' attribute
        only_a_tags = SoupStrainer("a", href=True)
        soup = BeautifulSoup(html, 'lxml', parse_only=only_a_tags)
        
        links = set()

        for element in soup:
            href = element.get('href', '')
            if self._is_valid_folha_article(href, section):
                full_url = urljoin(base_url, href)
                links.add(full_url)

        logger.info(f"Found {len(links)} article links on Folha page")
        return list(links)

    def _is_valid_folha_article(self, url: str, section: str = None) -> bool:
        """Check if a URL is a valid Folha article for the given section."""
        if not url or not isinstance(url, str):
            return False

        try:
            parsed = urlparse(url)

            # 1. Must be on the correct domain
            if 'folha.uol.com.br' not in parsed.netloc and not url.startswith('/'):
                return False

            # 2. Must be an article, which ends in .shtml for Folha
            if not parsed.path.endswith('.shtml'):
                return False

            # 3. Exclude known non-article paths
            exclude_patterns = ['/galerias/', '/videos/', '/especial/', '/sobre/']
            if any(pattern in parsed.path for pattern in exclude_patterns):
                return False

            # 4. Section-specific validation
            if section:
                # The URL path must start with the section name
                # e.g., /mundo/2025/09/... for section 'mundo'
                path_segments = parsed.path.strip('/').split('/')
                if not path_segments or path_segments[0] != section:
                    return False

            return True

        except Exception as e:
            logger.debug(f"URL validation failed for '{url}': {e}")
            return False

    def find_next_page_url(self, html, current_url):
        """Find the URL for the next page of Folha articles"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Folha uses a 'Próxima' link inside a specific div
        next_selectors = [
            '.c-pagination__arrow--next',
            'a.c-pagination__arrow[rel="next"]'
        ]
        
        for selector in next_selectors:
            next_link = soup.select_one(selector)
            if next_link and next_link.get('href'):
                return urljoin(current_url, next_link['href'])
        
        return None
    