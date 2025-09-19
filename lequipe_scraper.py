"""
Scraper for L'Équipe (lequipe.fr)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class LEquipeScraper(BaseScraper):
    """Scraper for L'Equipe"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "lequipe.fr"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from L'Equipe listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are in <a> tags inside elements with class 'liste_item'
        for item in soup.select('div.liste_item a[href]'):
            href = item['href']
            full_url = urljoin(base_url, href)
            if '/Football/' in full_url and 'lequipe.fr' in full_url:
                links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """L'Equipe uses a JS-driven 'Voir plus' button for pagination."""
        logger.info("L'Equipe scraper does not support pagination (JS-driven 'Voir plus').")
        return None