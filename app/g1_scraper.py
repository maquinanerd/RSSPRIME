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

        # Broaden the search to all links and rely on the validation function.
        # The 'feed-post-link' class might not be present on all article links
        # or in the version of the page fetched by the scraper.
        for element in soup.find_all('a', href=True):
            href = element.get('href')
            if href and self._is_valid_article_url(href, section):
                full_url = urljoin(base_url, href)
                if full_url not in seen:
                    links.append(full_url)
                    seen.add(full_url)

        if not links:
            logger.warning(f"No valid article links found on G1 page for section '{section}'. The page structure might have changed or the scraper is being blocked.")
        else:
            logger.info(f"Found {len(links)} article links on G1 page for section '{section}'")

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
            # Check if the path correctly corresponds to the section.
            # The path should start with the section name.
            # Example: /economia/noticia/... for section 'economia'
            
            path_segments = path.strip('/').split('/')
            if not path_segments:
                return False

            # Handle special case for 'agronegocios' which is a sub-section of 'economia'
            if section == 'agronegocios' and (len(path_segments) < 2 or path_segments[0] != 'economia' or path_segments[1] != 'agronegocios'):
                return False
            elif section == 'economia' and (path_segments[0] != 'economia' or (len(path_segments) > 1 and path_segments[1] == 'agronegocios')):
                return False # Must be 'economia' but not 'agronegocios'
            elif section not in ['economia', 'agronegocios'] and path_segments[0] != section:
                return False # For other sections like 'politica'
        
        return True

    def find_next_page_url(self, html, current_url):
        """G1 uses a JSON endpoint for pagination, which is not supported. Disable it."""
        logger.debug("G1 pagination is not supported (uses JSON). Scraping first page only.")
        return None