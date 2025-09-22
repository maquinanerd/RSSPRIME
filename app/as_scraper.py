"""
Scraper for AS.com network sites (as.com, chile.as.com, etc.)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ASScraper(BaseScraper):
    """Scraper for AS.com network sites"""

    def get_site_domain(self):
        """This will be dynamically based on the source's base_url."""
        return "as.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from AS listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Main article links are in <h2><a> tags
        for link_tag in soup.select('h2.s__tl a'):
            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                full_url = urljoin(base_url, href)
                
                # Filter out non-article links like /videos/ or /album/
                if '/videos/' not in full_url and '/album/' not in full_url:
                    links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """AS.com uses infinite scroll, which is hard to follow without a JS engine."""
        logger.info("AS.com scraper does not support pagination (infinite scroll).")
        return None