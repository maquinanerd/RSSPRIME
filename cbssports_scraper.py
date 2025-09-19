"""
Scraper for CBS Sports (cbssports.com)
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class CBSSportsScraper(BaseScraper):
    """Scraper for CBS Sports"""

    def get_site_domain(self):
        """Return the main domain for this scraper"""
        return "cbssports.com"

    def extract_article_links(self, html, base_url, section=None):
        """Extract article links from CBS Sports listing page HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = set()

        # Links are often in <a> tags with class 'article-list-pack-item-link'
        # or within elements with a 'data-item-id'
        selectors = [
            'a.article-list-pack-item-link[href]',
            'div[data-item-id] a[href]'
        ]
        
        for selector in selectors:
            for link_tag in soup.select(selector):
                href = link_tag['href']
                if href and href.startswith('/'):
                    # Filter out non-article links like /video/
                    if '/video/' not in href and '/live/' not in href:
                        full_url = urljoin(base_url, href)
                        links.add(full_url)

        logger.info(f"Extracted {len(links)} unique article links from {base_url}")
        return list(links)

    def find_next_page_url(self, html, current_url):
        """CBS Sports uses a 'Load More' button (JS-driven)."""
        logger.info("CBSSports.com scraper does not support pagination (JS-driven).")
        return None