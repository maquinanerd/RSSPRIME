"""
Scraper for A Bola (abola.pt)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ABolaScraper(BaseScraper):
    """Scraper for A Bola"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "abola.pt"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from A Bola listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are typically in <a> tags within <div class="media-body">
        for item in soup.select('div.media-body a[href]'):
            href = item['href']
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
                # Article URLs usually contain /noticia/
                if '/noticia/' in full_url:
                    links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """A Bola seems to use JS-driven pagination ('Carregar mais')."""
        logger.info("Abola.pt scraper does not support pagination (JS-driven).")
        return None