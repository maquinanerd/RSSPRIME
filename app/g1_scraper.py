"""
G1 (g1.globo.com) scraper
"""

import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class G1Scraper(BaseScraper):
    """Scraper for G1 (g1.globo.com)"""

    def get_site_domain(self):
        return "g1.globo.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from G1 pages"""
        links = []
        soup = BeautifulSoup(html, 'lxml')
        seen = set()

        # G1 uses a common structure with 'feed-post-link'
        for element in soup.select('a.feed-post-link'):
            href = element.get('href')
            if href and self._is_valid_article_url(href, section):
                full_url = urljoin(base_url, href)
                if full_url not in seen:
                    links.append(full_url)
                    seen.add(full_url)
        
        logger.info(f"Found {len(links)} article links on G1 page")
        return links

    def _is_valid_article_url(self, url, section=None):
        """Check if URL is a valid G1 article"""
        if not url:
            return False

        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
        except Exception:
            return False

        if 'g1.globo.com' not in url and not url.startswith('/'):
            return False

        exclude_patterns = ['/video/', '/ao-vivo/', '/index.ghtml', 'javascript:', 'mailto:', '#']
        if any(pattern in url for pattern in exclude_patterns):
            return False
        
        if not path.endswith('.ghtml'):
            return False

        if section:
            if section == 'agronegocios':
                if '/economia/agronegocios/' not in path: return False
            elif section == 'economia':
                if '/economia/agronegocios/' in path: return False
                if '/economia/' not in path: return False
            elif f'/{section}/' not in path:
                return False
        
        return True

    def find_next_page_url(self, html, current_url):
        """Find next page URL for pagination on G1"""
        soup = BeautifulSoup(html, 'lxml')
        
        next_link = soup.select_one('.load-more-ajax a')
        if next_link and next_link.get('href'):
            href = next_link.get('href')
            return urljoin(current_url, href)

        return None