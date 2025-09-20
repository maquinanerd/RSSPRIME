"""
Scraper for Marca.com
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MarcaScraper(BaseScraper):
    """Scraper for Marca.com"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "marca.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from Marca listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are in <h2><a> inside <article class="ui-story">
        for article in soup.find_all('article', class_='ui-story'):
            link_tag = article.find('h2').find('a', href=True) if article.find('h2') else None
            if link_tag and 'marca.com' in link_tag['href']:
                links.add(link_tag['href'])

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """Marca.com uses a JS-driven 'ver más' button for pagination."""
        logger.info("Marca.com scraper does not support pagination (JS-driven).")
        return None